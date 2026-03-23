# CityGaussian V1 블록 경계 아티팩트 완화 전략 연구

> **중첩 블록 분할 및 계층적 Coarse-to-Fine 학습**  
> CNU26-3DGS Research Group | 충남대학교 컴퓨터공학과 | 2026.03 ~

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![CUDA 12.8](https://img.shields.io/badge/CUDA-12.8-green.svg)](https://developer.nvidia.com/cuda-toolkit)
[![PyTorch 2.7.1](https://img.shields.io/badge/PyTorch-2.7.1-red.svg)](https://pytorch.org/)

---

## 개요

[CityGaussian V1](https://github.com/DekuLiuTesla/CityGaussian)(ECCV 2024)은 대규모 도시 장면을 블록 단위로 분할하여 독립적으로 3D Gaussian Splatting을 학습한 뒤 병합하는 파이프라인을 제안하였습니다. 그러나 각 블록이 독립적으로 학습되기 때문에, **블록 경계(block boundary)에서 시각적 불연속 아티팩트**(seam, color mismatch, density gap)가 발생합니다.

본 프로젝트는 **글로벌 정합(global alignment) 없이** 블록 분할 및 학습 전략 자체를 개선하여 경계 아티팩트를 완화하는 두 가지 접근법을 구현하고 실험적으로 검증합니다.

### 제안 전략

| 전략 | 명칭 | 핵심 아이디어 |
|------|------|---------------|
| **A** | 중첩 블록 분할 (Overlapping Block Partition) | 블록을 Core / Transition / Overlap 3구역으로 세분화하고, 인접 블록 간 경계 구역이 겹치도록 설계 |
| **B** | 계층적 Coarse-to-Fine 학습 (Hierarchical C2F Training) | 짧은 iteration의 Coarse Stage로 대략적 구조를 생성한 뒤, 이를 초기값으로 Fine Stage 학습 수행 |
| **A+B** | 결합 전략 | 중첩 블록 구조 위에 Coarse-to-Fine 학습을 적용하여 시너지 효과 검증 |

---

## 프로젝트 구조

기존 CityGaussian V1 루트 구조를 유지하면서, 실험용 파일을 루트 레벨 wrapper로 추가한다.

```
CityGaussianV1/
├── # === CityGS V1 원본 (수정 최소화) ===
├── train_large.py                  # 학습 메인 (block-wise 학습)
├── data_partition.py               # 블록 파티셔닝
├── merge.py                        # 블록 병합
├── render_large.py                 # 렌더링
├── metrics_large.py                # 메트릭 계산
├── arguments/__init__.py           # 파라미터 정의 (overlap 파라미터 추가)
├── scene/                          # Scene, GaussianModel, Camera
├── gaussian_renderer/              # render(), render_large()
├── utils/                          # large_utils, loss_utils 등
│
├── # === 전략 A: Overlap 실험용 (신규) ===
├── data_partition_overlap.py       # 전략 A: overlap-aware 파티셔닝
├── train_large_overlap.py          # 전략 A: overlap freeze 학습
├── merge_overlap.py                # 전략 A: soft blending + dedup merge
├── utils/overlap_utils.py          # 전략 A: 핵심 유틸리티
│
├── config/                         # 실험 설정 (YAML)
│   ├── mc_small_aerial_c36.yaml    # G0 baseline 블록 학습 설정
│   ├── mc_small_aerial_coarse.yaml # Coarse 학습 설정
│   ├── g1_overlap15.yaml           # G1: 전략 A (Overlap 15%)
│   ├── g2_overlap25.yaml           # G2: 전략 A (Overlap 25%)
│   └── smoke_test/                 # Smoke Test 설정
│       └── g1_overlap15_smoke.yaml
│
├── scripts/                        # 실행 스크립트
│   ├── run_overlap_experiment.sh   # G1/G2 전략 A E2E 실행
│   └── (기존 스크립트 유지)
│
├── tools/                          # 보조 도구
│   ├── select_boundary_views.py    # 실제 경계가 보이는 test view 선택
│   ├── filtered_metrics.py         # 선택된 view subset 메트릭 재계산
│   ├── projected_boundary_lpips.py # projected boundary crop LPIPS + crop 저장
│   ├── boundary_lpips.py           # strip 기반 Boundary LPIPS (reference)
│   ├── boundary_crop.py            # 경계 영역 crop (신규)
│   ├── error_map.py                # GT 대비 Error Map 생성 (신규)
│   ├── visualize_partitions.py     # 파티셔닝 시각화 (신규)
│   ├── plot_results.py             # 실험 결과 그래프 (신규)
│   └── (기존 도구 유지)
│
├── Todo/                           # 연구 계획 및 구현 계획
├── docs/                           # 실험 보고서, 진행 기록
│
├── data/                           # 데이터셋 (Git 미추적)
│   └── matrix_city/aerial/         # MatrixCity Small Aerial
│
├── output/                         # 학습 결과물 (Git 미추적)
│   ├── mc_small_aerial_coarse/     # G0 Coarse 결과
│   ├── mc_small_aerial_c36/        # G0 Block 결과
│   ├── g1_overlap15/               # G1 결과
│   └── g2_overlap25/               # G2 결과
│
├── CLAUDE.md                       # AI 분석/관리자 지침
├── AGENTS.md                       # AI 구현 에이전트 지침
└── LOCAL_SETUP_NOTES.md            # 로컬 환경 설정 기록
```

---

## 환경 설정

### 원본 논문 환경 (CityGaussian V1 공식)

- Python 3.8+, CUDA 11.8+, PyTorch 2.0+
- GPU: NVIDIA RTX 3090 / A6000 이상 (24GB+ VRAM 권장)

### 현재 실험 환경

| 항목 | 버전 |
|------|------|
| Python | 3.11 |
| PyTorch | 2.7.1+cu128 |
| CUDA | 12.8 |
| TORCH_CUDA_ARCH_LIST | 12.0 |
| 가상환경 | `.venv/` (venv 기반) |
| GPU | *(LOCAL_SETUP_NOTES.md 참조)* |

> **참고**: 원본 논문은 CUDA 11.8 / PyTorch 2.0 기준이나, 본 실험에서는 CUDA 12.8 환경에 맞춰
> submodules(`diff-gaussian-rasterization`, `simple-knn`)에 호환성 패치를 적용하여 사용한다.
> 패치 세부 사항은 `third_party_patches/README.md` 및 `LOCAL_SETUP_NOTES.md` 참조.

### 설치

```bash
# 1. 레포 클론
git clone --recursive https://github.com/IlhyeonChoo/CityGaussian.git
cd CityGaussian

# 2. 가상환경 생성
python3.11 -m venv .venv
source .venv/bin/activate

# 3. PyTorch 설치 (CUDA 12.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 4. 의존성 설치
pip install -r requirements.txt

# 5. 서브모듈 패치 적용 및 빌드
./scripts/apply_third_party_patches.sh
pip install submodules/diff-gaussian-rasterization
pip install submodules/simple-knn
```

### 데이터 준비

```bash
# MatrixCity Small Aerial 변환 (raw → V1 형식)
# 공식 링크: https://city-super.github.io/matrixcity/
# COLMAP 결과: https://huggingface.co/datasets/dylanebert/CityGaussian
python tools/prepare_matrixcity_small_aerial_v1.py
# 결과: data/matrix_city/aerial/train/block_all (train 7672장, test 152장)
```

---

## 실험 실행

### Smoke Test (빠른 검증)

본격 실험 전 파이프라인 동작 확인 및 기본 경향성 확인을 위한 Smoke Test입니다.

**1단계: 파이프라인 동작 확인** (2x2 블록, 100 iter)

각 단계가 에러 없이 완료되는지 확인한다.

```bash
SMOKE_CFG=config/smoke_test/g1_overlap15_smoke.yaml

# Partition → 블록별 학습 → Merge → Render → Metric 전체 파이프라인
python data_partition_overlap.py --config $SMOKE_CFG
for block_id in 0 1 2 3; do
  python train_large_overlap.py --config $SMOKE_CFG --block_id $block_id
done
python merge_overlap.py --config $SMOKE_CFG
python render_large.py --config $SMOKE_CFG
python metrics_large.py -m output/g1_overlap15_smoke -t val
```

**1단계 성공 기준:**
- ✅ 전 단계 에러 없이 완료
- ✅ zone mask 출력: core/overlap 비율이 합리적
- ✅ merged PLY 생성됨, 렌더링 이미지 출력됨

**2단계: 품질 경향성 확인** (본 실험 config, 단일 블록 축약 학습)

> 본 실험 전 전체 36블록을 짧게 돌려 경향을 확인한다. 상세 기준은 `Todo/G1_G2_implementation_plan.md`의 검증 계획 참조.

**2단계 성공 기준:**
- ✅ **Pass**: Loss 정상 수렴, 경계 영역에서 baseline 대비 시각적 개선 관찰
- ⚠️ **Conditional Pass**: 동작하나 개선 효과 미미 → 하이퍼파라미터 튜닝 필요
- ❌ **Fail**: 학습 발산 또는 baseline보다 악화 → 설계 재검토

### 본 실험

```bash
# G0: Baseline (CityGaussian V1 원본 파이프라인)
python train_large.py --config config/mc_small_aerial_coarse.yaml          # Coarse
python data_partition.py --config config/mc_small_aerial_c36.yaml          # Partition
python train_large.py --config config/mc_small_aerial_c36.yaml --block_id N  # Block 학습
python merge.py --config config/mc_small_aerial_c36.yaml                   # Merge

# G1: 전략 A - Overlap 15%
bash scripts/run_overlap_experiment.sh config/g1_overlap15.yaml

# G2: 전략 A - Overlap 25%
bash scripts/run_overlap_experiment.sh config/g2_overlap25.yaml
```

### 평가

```bash
# 전체 장면 메트릭 (PSNR / SSIM / LPIPS)
python metrics_large.py -m output/g1_overlap15 -t val

# 공식 경계 평가 1: 실제 block 경계가 보이는 test view만 선택
python tools/select_boundary_views.py \
  --config config/g1_overlap15.yaml \
  --test_dir data/matrix_city/aerial/test/block_all_test \
  --output_json output/boundary_analysis/g1_overlap15_boundary_views.json

# 공식 경계 평가 2: 선택된 view subset에서 전체 이미지 메트릭 재계산
python tools/filtered_metrics.py \
  --output_dir output/g1_overlap15 \
  --test_set val \
  --iteration 30000 \
  --view_manifest output/boundary_analysis/g1_overlap15_boundary_views.json

# 공식 경계 평가 3: projected boundary crop LPIPS + 시각 확인용 crop 저장
python tools/projected_boundary_lpips.py \
  --output_dir output/g1_overlap15 \
  --test_set val \
  --iteration 30000 \
  --view_manifest output/boundary_analysis/g1_overlap15_boundary_views.json \
  --save_crops

# 빠른 reference용 strip crop Boundary LPIPS
python tools/boundary_lpips.py --output_dir output/g1_overlap15 --crop_size 128

# Error Map 시각화
python tools/error_map.py --pred output/g1_overlap15/val/ours_30000/renders --gt output/g1_overlap15/val/ours_30000/gt

# 결과 비교 그래프 생성
python tools/plot_results.py --results_dir output/ --groups mc_small_aerial_c36 g1_overlap15 g2_overlap25
```

공식 비교 규칙:

- 전체 test set 메트릭은 reference로 유지한다.
- 경계 품질 비교는 `select_boundary_views.py`가 뽑은 `실제 경계가 보이는 view subset` 기준으로 한다.
- Boundary LPIPS의 공식 수치는 `projected_boundary_lpips.py` 결과를 사용한다.
- `boundary_lpips.py`는 smoke/quick check용 heuristic reference로만 사용한다.

## 현재 Pilot 상태

- 현재 `subset 4-block`의 공식 pilot 비교 기준은 `5k`이다.
- canonical 보고서:
  - `docs/reports/G0_G1_20260322_subset4_5k_canonical.md`
- 기존 `100 iter smoke` 보고서는 reference로 유지한다.
  - `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md`
  - `docs/reports/G1_20260321_overlap15_subset_smoke.md`
- `10k`는 아직 공식 결론이 아니다.
  - coarse 10k 완료
  - G0 10k는 `cell0` 완료, `cell1`은 `step 3819`에서 중단, `OOM 의심`
  - G1 10k는 미시작
- RTX 4060 Ti 로컬(`VRAM 16GB`)에서는 block 학습 시 `max_cache_num 32`와 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`를 기본 재시도 기준으로 사용한다.

---

## 실험 그룹

| ID | 실험 그룹 | 설명 | 역할 |
|----|-----------|------|------|
| **G0** | CityGaussian V1 Baseline | 원본 파이프라인 재현 | 기준선 |
| **G1** | 전략 A (Overlap 15%) | 중첩 비율 15% + Freeze 방식 | 전략 A 효과 검증 |
| **G2** | 전략 A (Overlap 25%) | 중첩 비율 25% + Freeze 방식 | Overlap 비율 ablation |
| **G3** | 전략 B (Block-wise C2F) | 블록별 Coarse 10% + Fine | 전략 B 효과 검증 |
| **G4** | 전략 A+B 결합 | Overlap 15% + Block-wise C2F | 시너지 검증 |

---

## 평가 지표

| 지표 | 측정 대상 | 우선순위 |
|------|-----------|----------|
| **PSNR** | 전체 장면 렌더링 품질 (픽셀 수준) | 필수 |
| **SSIM** | 구조적 유사도 | 필수 |
| **LPIPS** | 지각적 품질 | 핵심 |
| **Boundary LPIPS** | 경계 영역 한정 지각적 품질 | 핵심 (Primary) |
| 학습 시간 | wall-clock time | 필수 |
| 모델 크기 | .ply 파일 크기 / Gaussian 수 | 필수 |
| FPS | 렌더링 속도 | 참고 |
| Peak VRAM | 최대 GPU 메모리 사용량 | 참고 |

---

## 데이터셋

| 데이터셋 | 용도 | 규모 | 로컬 경로 |
|----------|------|------|-----------|
| [MatrixCity Aerial Small](https://city-super.github.io/matrixcity/) | Smoke Test + 주요 실험 | train 7672장, test 152장 | `data/matrix_city/aerial/` |

---

## 연구 일정

| 주차 | 단계 | 내용 |
|------|------|------|
| 1주 | 환경 구축 | CityGS V1 재현, Baseline(G0) 확보, Boundary LPIPS 스크립트 작성 |
| 2주 | Smoke Test A | 전략 A 구현 + Smoke Test |
| 3주 | Smoke Test B | 전략 B 구현 + Smoke Test |
| 4~5주 | 본 실험 | MatrixCity 전체 대상 G0~G4 실험 (3회 반복) |
| 6주 | Ablation | Overlap 비율, Coarse iter 비율 등 ablation study |
| 7주 | 분석 및 정리 | 결과 분석, 시각화, 보고서 작성 |

---

## 참고 문헌

- **CityGaussian V1**: Liu et al., "CityGaussian: Real-time High-quality Large-Scale Scene Rendering with Gaussians," ECCV 2024. [[Paper]](https://arxiv.org/abs/2404.01133) [[Code]](https://github.com/DekuLiuTesla/CityGaussian)
- **3D Gaussian Splatting**: Kerbl et al., "3D Gaussian Splatting for Real-Time Radiance Field Rendering," SIGGRAPH 2023.
- **Mega-NeRF**: Turki et al., "Mega-NeRF: Scalable Construction of Large-Scale NeRFs for Virtual Fly-Throughs," CVPR 2022.

---

## 라이선스

본 프로젝트는 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 라이선스를 따릅니다.  
CityGaussian V1 원본 코드의 라이선스 조건을 준수합니다.

---

## 팀

**CNU26-3DGS Research Group**  
충남대학교 컴퓨터공학과  

문의: [GitHub Issues](https://github.com/CNU26-3DGS/citygs-boundary-smoothing/issues)
