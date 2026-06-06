# 2026-03-22 Worktree 변경 인벤토리

> Legacy note: this document captured migration-time 판단 기준 while moving off
> the temporary 16GB server. Use `LOCAL_SETUP_NOTES.md` and current-server
> scripts for active execution.

- 목적:
  - 로컬 `RTX 4060 Ti (VRAM 16GB)`에서 smoke, 5k, 10k pilot을 돌리면서 생긴 변경을 서버 이관 판단용으로 정리한다.
  - 아래 분류 기준은 `서버에서 그대로 유지`, `서버 환경에 따라 선택 적용`, `로컬 전용이라 없어도 됨`으로 나눈다.

## 1. 서버 환경 문제 대응

이 그룹은 실험 아이디어 자체보다 `CUDA 12.8`, 파일 핸들, 로컬 빌드/실행 안정성`에 대응한 변경이다.

| 경로 | 변경 내용 | 성격 | 서버 권장 조치 |
|------|-----------|------|----------------|
| `submodules/diff-gaussian-rasterization/cuda_rasterizer/rasterizer_impl.h` | CUDA 12.8에서 빌드되도록 include/정렬 관련 수정 | 환경/호환성 | 서버가 이미 빌드된다면 그대로 두고, 같은 CUDA 계열에서 빌드 문제가 나면 적용 |
| `submodules/simple-knn/simple_knn.cu` | CUDA 12.8에서 컴파일되도록 include/정렬 관련 수정 | 환경/호환성 | 서버가 이미 빌드된다면 그대로 두고, 같은 CUDA 계열에서 빌드 문제가 나면 적용 |
| `LargeLightGaussian/scene/dataset_readers.py` | 카메라 메타만 먼저 읽고 이미지 파일 핸들을 오래 붙잡지 않도록 수정 | 환경/안정성 | LargeLightGaussian 쪽도 같이 쓰고 `Too many open files`류 이슈가 있으면 적용 |
| `LargeLightGaussian/utils/camera_utils.py` | 필요할 때만 이미지를 열고 즉시 닫도록 수정 | 환경/안정성 | 위와 동일 |
| `LargeLightGaussian/metrics.py` | metric 계산 시 `Image.open()` 핸들을 즉시 닫도록 수정 | 환경/안정성 | 위와 동일 |

판단:

- 이 변경들은 `실험 설계 변경`이 아니라 `환경/운영 안정성` 쪽이다.
- 원래 서버가 `RTX PRO 4500` 또는 다른 GPU에서 이미 문제 없이 돌아가던 부분이라면, 무조건 옮길 필요는 없다.
- 다만 CUDA 12.8 또는 파일 핸들 누수 문제가 서버에서도 보이면 이 그룹은 그대로 가져가도 된다.

## 2. 실험용으로 유지해야 하는 변경

이 그룹은 이번 overlap/boundary-view 실험 자체를 위해 만든 파일이다. 서버에서 같은 실험을 이어갈 거라면 유지하는 편이 맞다.

| 경로 | 변경 내용 | 성격 | 서버 권장 조치 |
|------|-----------|------|----------------|
| `tools/select_boundary_views.py` | 실제 block 경계가 보이는 test view만 선택 | 실험 평가 | 유지 권장 |
| `tools/filtered_metrics.py` | 선택된 view subset에서 PSNR/SSIM/LPIPS 재계산 | 실험 평가 | 유지 권장 |
| `tools/projected_boundary_utils.py` | projected boundary crop 공통 유틸 | 실험 평가 | 유지 권장 |
| `tools/projected_boundary_lpips.py` | projected boundary crop LPIPS 계산 및 crop 저장 | 실험 평가 | 유지 권장 |
| `tools/prepare_matrixcity_small_aerial_v1.py` | `--train-blocks`, `--test-blocks` 추가, Hugging Face raw layout 대응, subset 준비 가능 | 데이터 준비/실험 편의 | 서버에 prepared data가 이미 있으면 필수는 아님. 같은 subset/raw 준비를 다시 할 거면 유지 |
| `config/mc_small_aerial_subset_coarse_smoke.yaml` | subset coarse smoke | 실험 config | 유지 권장 |
| `config/smoke_test/g1_overlap15_subset_smoke.yaml` | subset overlap smoke | 실험 config | 유지 권장 |
| `config/mc_small_aerial_subset_c4_smoke.yaml` | subset non-overlap smoke | 실험 config | 유지 권장 |
| `config/mc_small_aerial_subset_coarse_5k.yaml` | subset coarse 5k | 실험 config | 유지 권장 |
| `config/mc_small_aerial_subset_coarse_10k.yaml` | subset coarse 10k | 실험 config | 유지 권장 |
| `config/mc_small_aerial_subset_c4_5k.yaml` | subset G0 5k | 실험 config | 유지 권장 |
| `config/mc_small_aerial_subset_c4_10k.yaml` | subset G0 10k | 실험 config | 유지 권장 |
| `config/g1_overlap15_subset_5k.yaml` | subset G1 5k | 실험 config | 유지 권장 |
| `config/g1_overlap15_subset_10k.yaml` | subset G1 10k | 실험 config | 유지 권장 |

판단:

- 이 그룹은 서버에서 같은 subset smoke/pilot과 projected boundary-view 평가를 이어갈 때 그대로 필요하다.
- 서버에서 full-scale만 돌리고 subset smoke를 다시 안 할 거라면 config 일부는 없어도 되지만, 재현성과 비교 기록 때문에 보존하는 편이 낫다.

## 3. 로컬 운영 편의용 스크립트

이 그룹은 실험 코어 로직이 아니라 `로컬 16GB VRAM GPU`에서 재시작과 OOM 분석을 쉽게 하려고 만든 것이다.

| 경로 | 변경 내용 | 성격 | 서버 권장 조치 |
|------|-----------|------|----------------|
| `scripts/legacy/run_subset_progression_resume.sh` | subset 5k/10k progression 재시작, skip-safe 실행, filtered eval 자동화 | 운영 자동화 | legacy 16GB 복구 흐름 보존용. 현재 서버 기본 경로로는 사용하지 않음 |
| `scripts/run_with_gpu_monitor.sh` | stdout/stderr + `nvidia-smi` 메모리 추이를 함께 저장 | 로컬 운영/OOM 분석 | 서버에서 OOM 원인 확인이 필요하면 유용. 아니면 필수 아님 |

추가 메모:

- 현재 `scripts/legacy/run_subset_progression_resume.sh`로 보관된 스크립트에는 이후 `TRAIN_EXTRA_ARGS` 전달 기능을 넣어 checkpoint 저장 인자를 block 학습에 넘길 수 있게 했다.
- `scripts/run_with_gpu_monitor.sh`는 실험 결과 자체를 바꾸지 않는다. 로그를 더 남기는 운영 도구다.

## 4. 문서 및 결과 기록

이 그룹은 실행 코드가 아니라 기록이다.

| 경로 | 변경 내용 | 성격 | 서버 권장 조치 |
|------|-----------|------|----------------|
| `docs/reports/G1_20260321_overlap15_subset_smoke.md` | subset overlap smoke 기록 | 문서 | 보존 권장 |
| `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md` | subset smoke 비교/실행 가능성 기록 | 문서 | 보존 권장 |
| `docs/reports/G0_G1_20260322_subset4_5k_canonical.md` | 현재 canonical 5k pilot 기록 | 문서 | 보존 권장 |
| `docs/progress.md` | 진행 상황 기록 | 문서 | 보존 권장 |
| `Todo/README.md` | 현재 pilot 상태와 평가 절차 반영 | 문서 | 보존 권장 |
| `LOCAL_SETUP_NOTES.md` | 로컬 GPU/환경 기록 | 문서 | 로컬 참고용, 서버에는 선택 |

## 5. 현재 git status 기준 변경 묶음

### tracked dirty

- `LargeLightGaussian`
- `Todo/README.md`
- `docs/progress.md`
- `submodules/diff-gaussian-rasterization`
- `submodules/simple-knn`
- `tools/prepare_matrixcity_small_aerial_v1.py`

### untracked

- `config/g1_overlap15_subset_10k.yaml`
- `config/g1_overlap15_subset_5k.yaml`
- `config/mc_small_aerial_subset_c4_10k.yaml`
- `config/mc_small_aerial_subset_c4_5k.yaml`
- `config/mc_small_aerial_subset_c4_smoke.yaml`
- `config/mc_small_aerial_subset_coarse_10k.yaml`
- `config/mc_small_aerial_subset_coarse_5k.yaml`
- `config/mc_small_aerial_subset_coarse_smoke.yaml`
- `config/smoke_test/g1_overlap15_subset_smoke.yaml`
- `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md`
- `docs/reports/G0_G1_20260322_subset4_5k_canonical.md`
- `docs/reports/G1_20260321_overlap15_subset_smoke.md`
- `scripts/legacy/run_subset_progression_resume.sh`
- `scripts/run_with_gpu_monitor.sh`
- `tools/filtered_metrics.py`
- `tools/projected_boundary_lpips.py`
- `tools/projected_boundary_utils.py`
- `tools/select_boundary_views.py`

## 6. 서버 이관 판단 요약

- 서버에서 그대로 두거나 가져가야 하는 것:
  - `tools/select_boundary_views.py`
  - `tools/filtered_metrics.py`
  - `tools/projected_boundary_utils.py`
  - `tools/projected_boundary_lpips.py`
  - subset smoke/5k/10k config들
  - 이번 실험 보고서들
- 서버에서 환경에 따라 선택 적용할 것:
  - `submodules/diff-gaussian-rasterization/cuda_rasterizer/rasterizer_impl.h`
  - `submodules/simple-knn/simple_knn.cu`
  - `LargeLightGaussian/*`의 파일 핸들 안정화 패치
- 서버에서 없어도 되는 로컬 운영 도구:
  - `scripts/run_with_gpu_monitor.sh`
  - `scripts/legacy/run_subset_progression_resume.sh`
- 데이터 준비 상황에 따라 선택:
  - `tools/prepare_matrixcity_small_aerial_v1.py`

## 7. 10k 관련 운영 결론

- 로컬 `RTX 4060 Ti (VRAM 16GB)`에서는 `G0 10k cell1`이 최소 두 번 OOM으로 중단됐다.
  - `max_cache_num 32`: `step 3810`, render path OOM
  - `max_cache_num 16`: `step 3550`, densification path OOM
- 따라서 이 GPU에서의 10k 실패는 실험 아이디어 문제라기보다 `로컬 VRAM 제약`의 영향이 크다.
- full 10k 이상은 원래 서버 GPU에서 이어가는 쪽이 맞다.
