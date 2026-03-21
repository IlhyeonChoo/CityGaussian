# AGENTS.md — AI 실험 에이전트 지침 (코드 수정·실험 실행·기록 역할)

> 이 문서는 **연구 계획에 따라 코드를 수정하고, 실험을 실행하고, 결과를 기록**하는 AI 에이전트에 대한 지침입니다.
> 사용자와 대화하며 분석·관리하는 역할은 CLAUDE.md를 참조하세요.

---

## 프로젝트 개요

- **프로젝트**: CityGaussian V1 블록 경계 아티팩트 완화 전략 연구
- **핵심 목표**: 블록 분할/학습 전략 개선으로 경계 아티팩트 완화 (글로벌 정합 없이)
- **기반 코드**: CityGaussian V1 (ECCV 2024)

---

## 역할 1: 실험 계획 확정

작업 시작 전 반드시 아래 문서들을 읽고 현재 상태를 파악한다.

### 필수 확인 문서

| 문서 | 경로 | 확인 내용 |
|------|------|-----------|
| 연구 계획서 | `Todo/README.md` | 전체 전략, 실험 그룹(G0~G4), 일정 |
| 로컬 설정 | `LOCAL_SETUP_NOTES.md` | 환경, 이미 검증된 항목, 주의사항 |
| AI 협업자 지침 | `CLAUDE.md` | 레포 구조, 파이프라인 흐름, 수정 대상 |
| 진행 기록 | `docs/progress.md` | 지금까지 완료된 작업 (있는 경우) |
| 정리 대상 | `docs/cleanup_candidates.md` | 이미 기록된 불필요 파일 (있는 경우) |

### 실험 계획 확정 절차

1. 위 문서를 모두 읽는다
2. 현재 config/ 디렉토리의 실험 설정 파일을 확인한다
3. output/ 디렉토리에서 이미 완료된 실험이 있는지 확인한다
4. 다음에 수행할 실험을 확정하고, **실험 계획을 사용자에게 보고**한다
5. 사용자 승인 후 코드 수정 및 실험을 진행한다

> **중요**: 실험 계획은 반드시 사용자 승인을 받은 뒤 진행한다. 임의로 실험을 시작하지 않는다.

---

## 역할 2: 코드 수정 및 작성

### 파이프라인 이해

CityGaussian V1의 학습 파이프라인:

```
1. Coarse 학습     : python train_large.py --config config/{scene}_coarse.yaml
2. 블록 파티셔닝   : python data_partition.py --config config/{scene}_cXX.yaml
3. 블록별 학습     : python train_large.py --config config/{scene}_cXX.yaml --block_id {N}
4. 블록 병합       : python merge.py --config config/{scene}_cXX.yaml
5. 렌더링          : python render_large.py --config config/{scene}_cXX.yaml --custom_test {path}
6. 메트릭 계산     : python metrics_large.py -m output/{scene}_cXX -t val
```

### 수정 대상 파일과 위치

#### 전략 A (중첩 블록 분할) 관련

| 파일 | 수정 포인트 |
|------|-------------|
| `arguments/__init__.py` | `ModelParams`에 `overlap_ratio` (float, default=0.0), `overlap_freeze` (bool), `blend_mode` (str) 추가 |
| `data_partition.py` | `block_partitioning()`에서 AABB 계산 시 overlap 영역 확장 로직 |
| `utils/large_utils.py` | `block_filtering()`에 core/transition/overlap 구역 구분 함수 추가 |
| `train_large.py` | overlap 영역 Gaussian에 대한 LR 감쇠 또는 freeze 처리 |
| `merge.py` | soft blending (거리 기반 opacity 감쇠) + 중복 Gaussian pruning |

#### 전략 B (Coarse-to-Fine 학습) 관련

| 파일 | 수정 포인트 |
|------|-------------|
| `arguments/__init__.py` | `OptimizationParams`에 `coarse_iterations` (int, default=0), `use_c2f` (bool) 추가 |
| `train_large.py` | block 학습 시 coarse→fine 2단계 분기: coarse checkpoint 저장 → fine에서 로드하여 이어 학습 |

#### 평가 도구 (새로 작성)

| 파일 | 용도 |
|------|------|
| `tools/boundary_crop.py` | 블록 경계에 해당하는 이미지 영역을 crop하는 유틸리티 |
| `tools/boundary_lpips.py` | crop된 경계 영역에 대해 LPIPS를 계산 — **이 연구의 primary metric** |
| `tools/error_map.py` | GT 대비 렌더링의 pixel-wise error map 생성 |
| `tools/visualize_partitions.py` | 3D 공간에서 블록 파티셔닝 결과를 시각화 |
| `tools/plot_results.py` | 실험 그룹 간 메트릭 비교 그래프 |

### 코드 수정 원칙

1. **기존 동작 보존**: 새 파라미터는 기본값으로 기존 CityGS V1과 동일하게 동작해야 한다
   - `overlap_ratio=0.0` → 기존과 동일
   - `coarse_iterations=0` 또는 `use_c2f=False` → 기존과 동일
2. **config로 제어**: 전략 차이는 코드 내 하드코딩이 아니라 YAML config 파라미터로 전환
3. **최소 수정**: 기존 함수의 시그니처를 바꾸기보다 새 파라미터를 추가하는 방식 선호
4. **테스트 가능하게**: smoke test config로 10~100 iteration 내에 전체 파이프라인이 돌아가는지 확인 가능해야 함

### 실험 Config 작성 규칙

실험 config는 기존 config를 기반으로 하되, 실험 파라미터를 추가한다.

```yaml
# 예시: config/overlap_15_g1.yaml
# 기존 mc_small_aerial_c36.yaml 기반 + overlap 파라미터 추가
model_params:
  source_path: "data/matrix_city/aerial"
  pretrain_path: "output/mc_small_aerial_coarse"
  block_dim: [6, 6, 1]
  overlap_ratio: 0.15        # 전략 A 파라미터
  overlap_freeze: true
  blend_mode: "soft"
  # ... (기존 파라미터 유지)

optim_params:
  iterations: 30000
  # ... (기존 파라미터 유지)
```

### 실험 Script 작성 규칙

scripts/ 디렉토리의 셸 스크립트는 아래 패턴을 따른다:

```bash
#!/bin/bash
# 실험 그룹: G1 - 전략 A (Overlap 15%)
# 사용법: bash scripts/run_overlap.sh --config config/overlap_15_g1.yaml

CONFIG=${1:-"config/overlap_15_g1.yaml"}

# 1. Coarse (이미 완료되었으면 건너뛰기)
# 2. Partition (overlap 적용)
# 3. Block-wise Training
# 4. Merge (soft blending)
# 5. Render
# 6. Metrics
```

---

## 역할 3: 실험 진행 및 결과 보고

### 실험 실행 시 기록할 항목

실험을 실행할 때 아래 정보를 수집하여 보고서에 포함한다:

1. **실험 환경**: GPU 모델, VRAM, CUDA 버전
2. **실행 명령어**: 정확한 커맨드 라인
3. **학습 시간**: wall-clock time (시작~종료)
4. **정량 지표**: PSNR, SSIM, LPIPS, Boundary LPIPS
5. **모델 크기**: 최종 .ply 파일 크기, Gaussian 수
6. **오류/경고**: 학습 중 발생한 이슈

### 결과 보고서 작성

실험 완료 후 `docs/reports/` 디렉토리에 보고서를 작성한다.

**파일명 규칙**: `{실험ID}_{날짜}_{간단설명}.md`
- 예: `G1_20260321_overlap15_smoke.md`

**보고서 구조**:

```markdown
# [실험 ID] 결과 보고서

- 일시: YYYY-MM-DD HH:MM ~ HH:MM
- Config: config/{파일명}.yaml
- 데이터셋: (이름, train/test 이미지 수)
- GPU: (모델, VRAM)

## 실행 명령어

(실제 실행한 명령어를 그대로 기록)

## 정량 결과

| 지표 | 값 | G0 대비 |
|------|-----|---------|
| PSNR | | |
| SSIM | | |
| LPIPS | | |
| Boundary LPIPS | | |
| 학습 시간 | | |
| 모델 크기 | | |
| Gaussian 수 | | |

## 학습 로그 요약

- Loss 수렴 여부
- 특이사항

## 렌더링 결과

- 경계 영역 시각 비교: (이미지 경로)
- Error map: (이미지 경로)

## 이슈

- (발생한 오류, 경고, 해결 방법)
```

### 결과 파일 위치

```
output/{실험명}/
├── results.json              # 전체 메트릭
├── per_view.json             # 뷰별 메트릭
├── costs.json                # 렌더링 성능
├── point_cloud/
│   └── iteration_{N}/
│       └── point_cloud.ply   # 병합된 모델
├── cells/                    # 블록별 결과
│   └── cell{N}/
└── {test_set}/
    └── ours_{N}/
        ├── renders/          # 렌더링 이미지
        └── gt/               # GT 이미지
```

---

## 역할 4: 불필요 파일 정리 기록

### 핵심 원칙

> **절대로 파일을 직접 삭제하거나 편집하지 않는다.**
> 불필요하다고 판단되는 파일은 `docs/cleanup_candidates.md`에 기록만 한다.
> 사람 또는 다른 에이전트(CLAUDE.md 역할)가 확인 후 처리한다.

### 기록 대상

- 실험이 끝난 뒤 더 이상 필요 없는 중간 결과물
- 역할이 중복되는 config 파일
- 사용되지 않는 스크립트나 도구
- 오래된 문서 (내용이 현재 상태와 맞지 않는 경우)
- 임시로 만들었다가 불필요해진 파일

### 기록 형식

`docs/cleanup_candidates.md`에 아래 형식으로 추가한다:

```markdown
## 정리 후보 목록

### YYYY-MM-DD 기록

| 파일/디렉토리 | 이유 | 판단 근거 | 처리 제안 |
|---------------|------|-----------|-----------|
| `output/old_smoke_test/` | smoke test 완료, 본실험 결과로 대체됨 | G0 본실험 결과 존재 | 삭제 가능 |
| `config/mc_small_aerial_coarse_smoke.yaml` | smoke 전용, 본실험에서 미사용 | run_smoke_test.sh에서만 참조 | 보존 (smoke 재실행 가능성) |
```

### 판단 기준

- **삭제 가능**: 다른 곳에서 참조하지 않고, 재생성이 쉬운 경우
- **보존 권장**: 재실행에 필요하거나, 히스토리 기록 가치가 있는 경우
- **확인 필요**: 삭제 여부를 사용자에게 물어봐야 하는 경우

---

## 작업 흐름 요약

```
[시작]
  │
  ├─ 1. 문서 확인 (Todo/README.md, LOCAL_SETUP_NOTES.md, CLAUDE.md, docs/)
  │
  ├─ 2. 현재 상태 파악 (config/, output/, 완료된 실험 확인)
  │
  ├─ 3. 실험 계획 확정 → 사용자에게 보고 → 승인 대기
  │
  ├─ 4. 코드 수정/작성 (기존 코드 확장, config 생성)
  │
  ├─ 5. Smoke test로 파이프라인 검증
  │
  ├─ 6. 본 실험 실행
  │
  ├─ 7. 결과 보고서 작성 (docs/reports/)
  │
  ├─ 8. 불필요 파일 기록 (docs/cleanup_candidates.md)
  │
  └─ 9. 다음 실험으로 반복
```

---

## 환경 정보

- Python 3.11, PyTorch 2.7.1+cu128, CUDA 12.8, TORCH_CUDA_ARCH_LIST=12.0
- 가상환경: `.venv/`
- 데이터: `data/matrix_city/aerial/` (train 7672장, test 152장)
- 기본 이미지 다운스케일: 1600px (원본은 `--resolution 1`)
- `max_cache_num`: 64부터 시작 권장
- submodules: CUDA 12.8 호환 패치 적용 상태

---

## 주의사항

- `V1-original` 브랜치는 원본 보존 — 실험은 별도 브랜치에서 진행
- `output/`, `data/`는 Git 미추적
- 기존 CityGS V1의 동작을 깨뜨리지 않도록 주의
- 대용량 파일(.ply, .pth, 이미지)은 절대 Git에 추가하지 않음
- 실험 중 OOM 발생 시 `max_cache_num` 줄이기 또는 `--resolution` 조정
