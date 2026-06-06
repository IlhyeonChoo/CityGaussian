# 이전 서버 vs 현재 서버 상태 비교

> Legacy note: this document is a 2026-03-23 migration snapshot captured before
> the current-server setup notes were refreshed. Use `LOCAL_SETUP_NOTES.md` for
> the active setup baseline.

- 작성일: 2026-03-23
- 목적: 임시 16GB 서버에서 진행하던 subset 실험 상태와, 현재 다시 복귀한 32GB 서버 워크스페이스 상태를 한 번에 비교할 수 있게 정리한다.
- 범위:
  - Git/코드 상태
  - 환경 차이
  - 남아 있는 실험 산출물
  - 누락된 subset 결과와 복구 필요 항목

## 용어 정리

- 이전 서버:
  - 2026-03-21 ~ 2026-03-22에 subset smoke / 5k / 10k pilot을 진행한 임시 16GB GPU 머신
  - 문서상으로는 `RTX 4060 Ti 16GB` 환경으로 기록되어 있다
- 현재 서버:
  - 사용자가 원래 실험을 돌리던 서버이자, 2026-03-23 기준 다시 복귀한 현재 워크스페이스
  - 실측 결과 `NVIDIA RTX PRO 4500 Blackwell (32623 MiB)` 환경이다

## 한눈에 비교

| 항목 | 이전 서버 (문서 기준) | 현재 서버 (실측 기준) | 판단 |
|------|------------------------|------------------------|------|
| 역할 | subset smoke / pilot 임시 실행 | full baseline 보관 + 이후 본실험 재개 대상 | 현재 서버를 기준 환경으로 삼는 것이 맞다 |
| GPU | NVIDIA GeForce RTX 4060 Ti, 16GB | NVIDIA RTX PRO 4500 Blackwell, 32623 MiB | 현재 서버가 VRAM 여유가 커서 10k 이상 재개에 적합 |
| Python | 3.11 | 3.11 (`.venv`) | 동일 |
| PyTorch | 2.7.1+cu128 | 2.7.1+cu128 | 동일 |
| CUDA | 12.8 | 12.8 | 동일 |
| 핵심 CUDA extension | 사용 중 | `diff_gaussian_rasterization`, `simple_knn` import 정상 | 현재 서버도 바로 실행 가능 |
| 공식 진행 상태 | subset 5k canonical 완료, 10k는 OOM으로 중단 | baseline full 결과 보유, subset 결과는 미복구 | subset 복구가 다음 우선 작업 |
| Git 브랜치 | `experiment/obc-citygs` 기준으로 작업한 흔적 | `experiment/obc-citygs`, `origin` 대비 ahead 2 | 코드 베이스는 대체로 돌아와 있음 |

## Git / 코드 상태 비교

### 현재 서버에서 확인된 Git 상태

- 브랜치: `experiment/obc-citygs`
- 원격 추적 상태: `origin/experiment/obc-citygs` 대비 `ahead 2`
- 로컬 전용 커밋:
  - `1417cd6 add gitignore txt`
  - `d45ba02 Merge branch 'experiment/obc-citygs' ...`
- 현재 `git status`에서 dirty로 보이는 항목:
  - `LargeLightGaussian`
  - `submodules/diff-gaussian-rasterization`
  - `submodules/simple-knn`

### dirty 서브모듈 해석

현재 dirty 상태는 임의 수정이라기보다, 이전 서버 문서에 적힌 환경 패치와 일치한다.

| 경로 | 현재 상태 | 해석 |
|------|-----------|------|
| `LargeLightGaussian` | `metrics.py`, `scene/dataset_readers.py`, `utils/camera_utils.py` 수정 | 파일 핸들 누적 방지 패치와 일치 |
| `submodules/diff-gaussian-rasterization` | `cuda_rasterizer/rasterizer_impl.h` 수정 | CUDA 12.8 호환 패치와 일치 |
| `submodules/simple-knn` | `simple_knn.cu` 수정, `build/`, `simple_knn.egg-info/` 존재 | CUDA 12.8 호환 패치 + 빌드 산출물 |

근거 문서:

- `third_party_patches/README.md`
- `LOCAL_SETUP_NOTES.md`
- `docs/legacy/20260322_worktree_change_inventory.md`

### 실험 코드 구현 범위

| 항목 | 상태 | 비고 |
|------|------|------|
| 전략 A overlap 파이프라인 | 구현됨 | `arguments/__init__.py`, `data_partition_overlap.py`, `train_large_overlap.py`, `merge_overlap.py`, `utils/overlap_utils.py` |
| projected boundary-view 평가 도구 | 구현됨 | `tools/select_boundary_views.py`, `tools/filtered_metrics.py`, `tools/projected_boundary_lpips.py`, `tools/projected_boundary_utils.py` |
| subset smoke / 5k / 10k config | 존재 | `config/mc_small_aerial_subset_*`, `config/g1_overlap15_subset_*` |
| 전략 B coarse-to-fine | 미구현 | `coarse_iterations`, `use_c2f`가 코드/설정에 없음 |

## 이전 서버에서 했던 일과 현재 서버 반영 상태

### 이전 서버에서 문서로 확인되는 진행 상태

| 구분 | 이전 서버 상태 | 현재 서버 반영 여부 |
|------|----------------|---------------------|
| subset overlap smoke | 완료 | 문서/코드만 있음, output 없음 |
| subset G0 5k | 완료 | 문서/코드만 있음, output 없음 |
| subset G1 5k | 완료 | 문서/코드만 있음, output 없음 |
| subset 5k canonical 보고서 | 작성 완료 | 현재 서버에 문서 존재 |
| subset G0 10k | `cell0` 완료 후 `cell1` OOM 중단 | 문서만 존재, output/log 없음 |
| subset G1 10k | 시작 전 또는 미완료 | 현재 서버에도 결과 없음 |
| OOM 분석 로그 | 문서에는 기록됨 | 현재 서버에는 `logs/` 디렉토리 없음 |

관련 문서:

- `docs/progress.md`
- `docs/reports/G1_20260321_overlap15_subset_smoke.md`
- `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md`
- `docs/reports/G0_G1_20260322_subset4_5k_canonical.md`
- `docs/legacy/20260322_worktree_change_inventory.md`

## 산출물 / 데이터 비교

### 현재 서버에 실제로 남아 있는 산출물

| 항목 | 경로 | 상태 |
|------|------|------|
| full coarse baseline | `output/mc_small_aerial_coarse` | 존재 |
| full block baseline | `output/mc_small_aerial_c36` | 존재 |
| full block cell 수 | `output/mc_small_aerial_c36/cells` | 36개 존재 |
| full baseline merged PLY | `output/mc_small_aerial_c36/point_cloud/iteration_30000/point_cloud.ply` | 존재 |
| full baseline metric | `output/mc_small_aerial_c36/results.json` | 존재 |
| MatrixCity full train data | `data/matrix_city/aerial/train/block_all` | 존재 |
| MatrixCity full test data | `data/matrix_city/aerial/test/block_all_test` | 존재 |

### 현재 서버에 없는 항목

| 항목 | 문서상 존재 여부 | 현재 서버 상태 | 의미 |
|------|------------------|----------------|------|
| `output/mc_small_aerial_subset_coarse_5k` | 있음 | 없음 | subset coarse 결과 미복구 |
| `output/mc_small_aerial_subset_c4_5k` | 있음 | 없음 | subset G0 5k 결과 미복구 |
| `output/g1_overlap15_subset_5k` | 있음 | 없음 | subset G1 5k 결과 미복구 |
| `output/mc_small_aerial_subset_c4_10k` | 있음 | 없음 | subset G0 10k 중간 결과 미복구 |
| `output/g1_overlap15_subset_10k` | 있음 | 없음 | subset G1 10k 결과 없음 |
| `output/boundary_analysis` | 있음 | 없음 | selector manifest / boundary-view 재평가 산출물 없음 |
| `logs/` | 있음 | 없음 | OOM retry 로그 현재 서버에 없음 |
| `data/matrix_city/aerial_subset/...` | 문서상 subset 준비 흔적 존재 | 없음 | subset 전용 데이터 구조도 현재 서버에는 없음 |

### 현재 서버에 남아 있는 baseline 기준선

| 항목 | 값 |
|------|----|
| full baseline SSIM | `0.8717080354690552` |
| full baseline PSNR | `28.48253059387207` |
| full baseline LPIPS | `0.2514069676399231` |
| coarse output 크기 | 약 `7.7G` |
| full block output 크기 | 약 `32G` |

## 문서와 실제 상태의 불일치

### 현재 기준으로 outdated 된 문서

| 문서 | 현재 불일치 내용 |
|------|------------------|
| `LOCAL_SETUP_NOTES.md` | 아직 `RTX 4060 Ti 16GB` 기준이며, "32GB 서버로 옮길 예정" 상태로 적혀 있음 |
| `docs/progress.md` | subset 5k/10k 진행 상황은 적혀 있지만, 그 결과 파일들이 현재 서버에 실제로 없다는 점은 반영되지 않음 |
| `Todo/README.md` 및 보고서들 | 실행 예시와 결과 경로는 남아 있지만, 현재 서버 워크스페이스에는 subset output이 없음 |

### 해석

- 코드와 문서는 대체로 현재 서버에 돌아와 있다.
- 그러나 subset 실험 산출물과 OOM 로그는 현재 서버에 복원되지 않았다.
- 따라서 지금 워크스페이스는 "실험 코드는 유지된 상태"이지만, "subset pilot 결과물은 비어 있는 상태"로 보는 것이 정확하다.

## 현재 서버에서 바로 이어갈 수 있는 항목

| 항목 | 가능 여부 | 비고 |
|------|-----------|------|
| full baseline 재참조 | 가능 | output이 그대로 남아 있음 |
| overlap 실험 코드 점검/수정 | 가능 | 코드 파일 존재 |
| subset 실험 재구성 | 가능 | config와 평가 도구는 존재하나 결과물은 다시 준비해야 함 |
| 10k 이상 재도전 | 가능성이 높음 | 32GB VRAM 환경이라 16GB OOM 제약이 완화됨 |
| 전략 B 구현 착수 | 가능 | 아직 미구현 상태 |

## 결론

현재 서버는 "baseline 결과와 실험 코드가 살아 있는 기준 워크스페이스"로 정리할 수 있다. 반면, 이전 16GB 서버에서 진행한 subset smoke / 5k / 10k pilot의 실제 output, boundary analysis 산출물, 로그는 현재 서버에 복구되어 있지 않다.

즉, 현재 상태를 한 문장으로 요약하면 다음과 같다.

> 코드는 돌아왔고 full baseline은 남아 있지만, subset pilot 산출물은 사라져 있어 문서와 실제 output 상태가 분리되어 있다.

## 다음 단계 제안

1. 현재 문서를 기준으로 subset 복구 대상 목록을 확정한다.
2. 복구 우선순위는 `subset coarse 5k -> G0 5k -> G1 5k -> boundary_analysis -> 10k 재개 여부` 순으로 잡는다.
3. `LOCAL_SETUP_NOTES.md`와 `docs/progress.md`는 subset 복구 전략이 정해진 뒤 현재 서버 기준으로 다시 업데이트한다.
