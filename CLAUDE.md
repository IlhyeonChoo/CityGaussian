# CLAUDE.md — AI 협업자 지침 (사용자와 함께 분석·관리하는 역할)

> 이 문서는 **사용자와 대화하며 실험 분석, 문서 관리, 레포 구조 관리**를 수행하는 AI에 대한 지침입니다.
> 코드를 직접 작성하거나 실험을 실행하는 역할은 AGENTS.md를 참조하세요.

---

## 프로젝트 개요

- **프로젝트**: CityGaussian V1 블록 경계 아티팩트 완화 전략 연구
- **핵심 목표**: 글로벌 정합 없이 블록 분할/학습 전략 개선으로 경계 아티팩트(seam, color mismatch, density gap)를 완화
- **기반 코드**: [CityGaussian V1](https://github.com/DekuLiuTesla/CityGaussian) (ECCV 2024)
- **소속**: CNU26-3DGS Research Group, 충남대학교 컴퓨터공학과

### 연구 전략

| 전략 | 명칭 | 핵심 아이디어 |
|------|------|---------------|
| **A** | 중첩 블록 분할 (Overlapping Block Partition) | Core / Transition / Overlap 3구역, 인접 블록 경계 중첩 |
| **B** | 계층적 Coarse-to-Fine 학습 (Hierarchical C2F Training) | 짧은 Coarse Stage → 초기값으로 Fine Stage |
| **A+B** | 결합 전략 | 중첩 블록 + C2F 학습 시너지 검증 |

### 실험 그룹

| ID | 실험 | 설명 |
|----|------|------|
| **G0** | Baseline | CityGaussian V1 원본 재현 |
| **G1** | 전략 A (Overlap 15%) | overlap_ratio=0.15 + Freeze |
| **G2** | 전략 A (Overlap 25%) | overlap_ratio=0.25 + Freeze |
| **G3** | 전략 B (Block-wise C2F) | Coarse 10% iter → Fine |
| **G4** | 전략 A+B 결합 | Overlap 15% + C2F |

---

## 역할 1: 실험 결과 분석

사용자가 실험 결과를 공유하면 **함께 원인과 결과를 분석**한다.

### 분석 시 확인할 항목

1. **정량 지표 비교**
   - 필수: PSNR, SSIM, LPIPS (전체 장면)
   - 핵심: **Boundary LPIPS** (경계 영역 한정 — 이 연구의 primary metric)
   - 부가: 학습 시간, 모델 크기(.ply / Gaussian 수), FPS, Peak VRAM

2. **결과 파일 위치**
   - 학습 결과: `output/{실험명}/`
   - 메트릭 JSON: `output/{실험명}/results.json`, `per_view.json`
   - 렌더링 이미지: `output/{실험명}/{test_set}/ours_{iteration}/renders/`
   - GT 이미지: `output/{실험명}/{test_set}/ours_{iteration}/gt/`

3. **분석 관점**
   - Baseline(G0) 대비 각 전략의 개선 폭
   - 전체 품질(PSNR/SSIM) 손실 없이 경계 품질(Boundary LPIPS)이 개선되었는가
   - overlap 비율(15% vs 25%)에 따른 trade-off (품질 향상 vs 모델 크기/학습 시간 증가)
   - Coarse stage iteration 비율이 결과에 미치는 영향
   - 시각적 아티팩트: seam, color mismatch, density gap이 완화되었는가

4. **시각적 확인**
   - error map으로 경계 영역의 오차 분포 확인
   - 경계 영역 crop 이미지로 직접 비교
   - 블록 파티셔닝 시각화로 overlap 영역이 의도대로 생성되었는지 확인

### 분석 보고 형식

실험 결과를 분석할 때는 아래 구조를 따른다:

```
## [실험 ID] 결과 분석

### 정량 결과
(표: G0 baseline 대비 delta 포함)

### 관찰
- 경계 영역에서의 변화
- 전체 품질에 대한 영향
- 예상과 다른 결과가 있다면 원인 가설

### 결론 및 다음 단계
- 이 결과가 의미하는 것
- 추가로 확인이 필요한 사항
```

---

## 역할 2: 문서 업데이트 및 계획 수립

### 관리 대상 문서

| 문서 | 위치 | 용도 |
|------|------|------|
| 연구 계획서 | `Todo/README.md` | 전체 연구 계획 및 일정 |
| 실험 보고서 | `docs/reports/` | 각 실험 그룹별 결과 보고서 |
| 진행 상황 | `docs/progress.md` | 주차별 진행 기록 |
| 로컬 설정 | `LOCAL_SETUP_NOTES.md` | 환경 설정 및 검증 기록 |
| 정리 대상 | `docs/cleanup_candidates.md` | Agent가 기록한 불필요 파일 목록 (확인용) |

### 문서 작업 원칙

- 실험 결과가 나올 때마다 `docs/reports/`에 보고서 작성
- 계획 변경이 있으면 `Todo/README.md`의 일정표 업데이트
- 새로운 발견이나 결정 사항은 즉시 관련 문서에 반영
- 문서는 **한국어**로 작성 (코드 주석과 변수명은 영어)

### 보고서 작성 형식

```markdown
# [실험 그룹 ID] 결과 보고서

- 일시: YYYY-MM-DD
- 실험 설정: (config 파일명, 주요 파라미터)
- 데이터셋: (사용한 데이터셋, 이미지 수)

## 정량 결과
(표)

## 정성 결과
(시각화 이미지 경로, 관찰)

## 분석
(원인 분석, baseline 대비 비교)

## 결론 및 향후 계획
```

---

## 역할 3: 레포 구조 관리

### 현재 레포 구조 (핵심)

```
CityGaussianV1/
├── train_large.py          # 학습 메인 (block-wise 학습 포함)
├── data_partition.py        # 블록 파티셔닝
├── merge.py                 # 블록 병합
├── render_large.py          # 렌더링
├── metrics_large.py         # 메트릭 계산
├── render_large_lod.py      # LOD 렌더링
│
├── arguments/__init__.py    # 파라미터 정의 (ModelParams, OptimizationParams 등)
├── scene/                   # Scene, GaussianModel, Camera, DatasetReader
├── gaussian_renderer/       # render(), render_large(), render_lod()
├── utils/                   # large_utils(블록), loss_utils, image_utils 등
│
├── config/                  # 실험 설정 YAML
├── scripts/                 # 실행 셸 스크립트
├── tools/                   # 데이터 변환/준비 도구
│
├── Todo/                    # 연구 계획서, gitignore 템플릿
├── docs/                    # 실험 보고서, 진행 기록
├── output/                  # 학습 결과물 (Git 미추적)
├── data/                    # 데이터셋 (Git 미추적)
│
├── LargeLightGaussian/      # 모델 압축 서브모듈
├── submodules/              # diff-gaussian-rasterization, simple-knn
├── lpipsPyTorch/            # LPIPS 라이브러리
├── SIBR_viewers/            # 실시간 뷰어
│
├── CLAUDE.md                # 이 문서
├── AGENTS.md                # Agent용 지침
├── LOCAL_SETUP_NOTES.md     # 로컬 환경 설정 기록
└── README.md                # 프로젝트 소개
```

### CityGaussian V1 파이프라인 흐름

```
1. Coarse 학습     : train_large.py --config {scene}_coarse.yaml
2. 블록 파티셔닝   : data_partition.py --config {scene}_cXX.yaml
3. 블록별 학습     : train_large.py --config {scene}_cXX.yaml --block_id {N}  (병렬 가능)
4. 블록 병합       : merge.py --config {scene}_cXX.yaml
5. 렌더링          : render_large.py --config {scene}_cXX.yaml --custom_test {path}
6. 메트릭 계산     : metrics_large.py -m output/{scene}_cXX -t val
```

### 구조 관리 원칙

- **기존 V1 코드는 최대한 보존**: 원본 파이프라인의 기존 기능이 깨지지 않도록 한다
- **확장 방식으로 수정**: 새 파라미터는 기본값으로 기존 동작을 유지하도록 설계
- **실험 config로 분리**: 전략별 차이는 코드 분기가 아니라 config 파라미터로 제어
- **브랜치 전략**: `V1-original` (원본 보존) → `experiment/boundary-smoothing` (실험 진행)

### 수정 대상 파일과 이유

| 파일 | 수정 이유 | 영향 범위 |
|------|-----------|-----------|
| `arguments/__init__.py` | overlap_ratio, coarse_iterations 등 새 파라미터 추가 | 전체 파이프라인 |
| `data_partition.py` | overlap 영역 계산 로직 추가 | 전략 A |
| `train_large.py` | overlap freeze/LR 감쇠, C2F 2단계 학습 | 전략 A, B |
| `merge.py` | soft blending, duplicate pruning | 전략 A |
| `utils/large_utils.py` | overlap-aware block_filtering, 구역 구분 | 전략 A |

### 새로 생성할 파일

| 파일 | 용도 |
|------|------|
| `config/baseline_g0.yaml` ~ `config/combined_g4.yaml` | 실험 그룹별 설정 |
| `config/smoke_test/*.yaml` | Smoke test 설정 |
| `scripts/run_baseline.sh` ~ `scripts/run_all_experiments.sh` | 실험 실행 스크립트 |
| `tools/boundary_lpips.py` | Boundary LPIPS 평가 |
| `tools/boundary_crop.py` | 경계 영역 crop |
| `tools/error_map.py` | Error map 생성 |
| `tools/visualize_partitions.py` | 파티셔닝 시각화 |
| `tools/plot_results.py` | 결과 그래프 |

---

## 환경 정보

- Python 3.11, PyTorch 2.7.1+cu128, CUDA 12.8
- TORCH_CUDA_ARCH_LIST=12.0
- 가상환경: `.venv/`
- 주요 데이터: `data/matrix_city/aerial/` (MatrixCity Small Aerial, train 7672장 + test 152장)
- 기존 검증 완료: drjohnson coarse/block 학습, MatrixCity smoke test (LOCAL_SETUP_NOTES.md 참조)

---

## 주의사항

- `output/`, `data/`는 Git 미추적 — 결과 비교 시 로컬 경로 기준으로 확인
- submodules(`diff-gaussian-rasterization`, `simple-knn`)는 CUDA 12.8 호환 패치 적용 상태
- 이미지 기본 다운스케일 1600px — 원본 해상도는 `--resolution 1` 필요
- `max_cache_num`은 64부터 시작 권장
