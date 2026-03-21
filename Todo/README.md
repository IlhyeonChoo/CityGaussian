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

```
citygs-boundary-smoothing/
├── configs/                        # 실험 설정 파일 (YAML)
│   ├── baseline_g0.yaml            # G0: CityGaussian V1 Baseline
│   ├── overlap_15_g1.yaml          # G1: 전략 A (Overlap 15%)
│   ├── overlap_25_g2.yaml          # G2: 전략 A (Overlap 25%)
│   ├── c2f_blockwise_g3.yaml       # G3: 전략 B (Block-wise C2F)
│   ├── combined_g4.yaml            # G4: 전략 A+B 결합
│   └── smoke_test/                 # Smoke Test 설정
│       ├── smoke_overlap.yaml
│       └── smoke_c2f.yaml
│
├── src/                            # 핵심 소스 코드
│   ├── partition/                  # 블록 파티셔닝 모듈
│   │   ├── __init__.py
│   │   ├── base_partition.py       # CityGS V1 기본 파티셔닝
│   │   └── overlap_partition.py    # 전략 A: 중첩 블록 파티셔닝
│   │
│   ├── training/                   # 학습 파이프라인
│   │   ├── __init__.py
│   │   ├── block_trainer.py        # 블록별 학습기 (기본)
│   │   ├── coarse_trainer.py       # 전략 B: Coarse Stage 학습
│   │   ├── fine_trainer.py         # 전략 B: Fine Stage 학습
│   │   └── overlap_handler.py      # 전략 A: Overlap 영역 LR/Freeze 처리
│   │
│   ├── merge/                      # 병합 모듈
│   │   ├── __init__.py
│   │   ├── base_merge.py           # 기본 블록 병합
│   │   ├── soft_blending.py        # 전략 A: 거리 기반 opacity 감쇠
│   │   └── duplicate_pruning.py    # 전략 A: 중복 Gaussian 제거
│   │
│   └── evaluation/                 # 평가 모듈
│       ├── __init__.py
│       ├── metrics.py              # PSNR, SSIM, LPIPS 계산
│       ├── boundary_lpips.py       # Boundary LPIPS 측정
│       └── boundary_crop.py        # 경계 영역 crop 유틸리티
│
├── scripts/                        # 실행 스크립트
│   ├── run_baseline.sh             # G0 Baseline 학습/평가
│   ├── run_overlap.sh              # G1/G2 전략 A 학습/평가
│   ├── run_c2f.sh                  # G3 전략 B 학습/평가
│   ├── run_combined.sh             # G4 결합 전략 학습/평가
│   ├── run_smoke_test.sh           # Smoke Test 실행
│   └── run_all_experiments.sh      # 전체 실험 일괄 실행 (3회 반복)
│
├── tools/                          # 보조 도구
│   ├── visualize_partitions.py     # 블록 파티셔닝 시각화
│   ├── visualize_boundary.py       # 경계 영역 렌더링 시각화
│   ├── error_map.py                # GT 대비 Error Map 생성
│   ├── render_trajectory.py        # 카메라 궤적 렌더링 영상 생성
│   └── plot_results.py             # 실험 결과 그래프 생성
│
├── docs/                           # 문서
│   └── research_proposal.pdf       # 연구 계획서
│
├── data/                           # 데이터셋 (Git 미추적)
│   ├── matrixcity_aerial_small/
│   ├── rubble/
│   └── custom/
│
├── output/                         # 학습 결과물 (Git 미추적)
│   ├── G0_baseline/
│   ├── G1_overlap_15/
│   ├── G2_overlap_25/
│   ├── G3_c2f_blockwise/
│   └── G4_combined/
│
├── logs/                           # 학습 로그 (Git 미추적)
│
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py
└── LICENSE
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
mkdir -p data/matrixcity_aerial_small

# MatrixCity Aerial Small 데이터셋 다운로드
# 공식 링크: https://city-super.github.io/matrixcity/
# COLMAP 결과: https://huggingface.co/datasets/dylanebert/CityGaussian
```

---

## 실험 실행

### Smoke Test (빠른 검증)

본격 실험 전 구현 검증 및 기본 경향성 확인을 위한 Smoke Test입니다.

```bash
# 전략 A Smoke Test (2x2 블록, overlap=15%, 5000 iter)
bash scripts/run_smoke_test.sh --strategy overlap

# 전략 B Smoke Test (Coarse 1000 iter + Fine 5000 iter)
bash scripts/run_smoke_test.sh --strategy c2f
```

**Smoke Test 성공 기준:**
- ✅ **Pass**: Loss 정상 수렴, 경계 영역에서 baseline 대비 시각적 개선 관찰
- ⚠️ **Conditional Pass**: 동작하나 개선 효과 미미 → 하이퍼파라미터 튜닝 필요
- ❌ **Fail**: 학습 발산 또는 baseline보다 악화 → 설계 재검토

### 본 실험

```bash
# G0: Baseline (CityGaussian V1 재현)
bash scripts/run_baseline.sh --config configs/baseline_g0.yaml

# G1: 전략 A - Overlap 15%
bash scripts/run_overlap.sh --config configs/overlap_15_g1.yaml

# G2: 전략 A - Overlap 25%
bash scripts/run_overlap.sh --config configs/overlap_25_g2.yaml

# G3: 전략 B - Block-wise Coarse-to-Fine
bash scripts/run_c2f.sh --config configs/c2f_blockwise_g3.yaml

# G4: 전략 A+B 결합
bash scripts/run_combined.sh --config configs/combined_g4.yaml

# 전체 실험 일괄 실행 (3회 반복, random seed 변경)
bash scripts/run_all_experiments.sh --repeats 3
```

### 평가

```bash
# 전체 장면 메트릭 (PSNR / SSIM / LPIPS)
python src/evaluation/metrics.py --output_dir output/G1_overlap_15 --gt_dir data/matrixcity_aerial_small/test

# Boundary LPIPS (경계 영역 crop, 64~128px)
python src/evaluation/boundary_lpips.py --output_dir output/G1_overlap_15 --crop_size 128

# Error Map 시각화
python tools/error_map.py --pred output/G1_overlap_15/renders --gt data/matrixcity_aerial_small/test

# 결과 비교 그래프 생성
python tools/plot_results.py --results_dir output/ --groups G0 G1 G2 G3 G4
```

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

| 데이터셋 | 용도 | 규모 |
|----------|------|------|
| [MatrixCity Aerial Small](https://city-super.github.io/matrixcity/) | Smoke Test + 주요 실험 | ~300 images |
| [Rubble (Mega-NeRF)](https://meganerf.cmusatyalab.org/) | 보조 실험 | ~1,600 images |
| 자체 캡처 | 일반화 테스트 | TBD |

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
