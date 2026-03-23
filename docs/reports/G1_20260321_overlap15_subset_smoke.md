# G1 overlap15 subset smoke 결과 보고서

- 일시: 2026-03-21 20:30 ~ 20:58 KST
- Config:
  - `config/mc_small_aerial_subset_coarse_smoke.yaml`
  - `config/smoke_test/g1_overlap15_subset_smoke.yaml`
- 데이터셋: MatrixCity `small_city/aerial` subset
  - train: `block_1, block_4, block_7, block_10` = 3504장
  - test: `block_1_test` = 152장
- GPU: NVIDIA GeForce RTX 4060 Ti, VRAM 16GB
- 비고:
  - local `.venv` / Python 3.11 / PyTorch 2.7.1+cu128 기준
  - 렌더는 `render_large.py`의 기본 test split 분기 대신 `--custom_test data/matrix_city/aerial/test/block_all_test`로 실행
  - 공식 경계 비교는 `output/boundary_analysis/subset4_block_all_test_strict.json`에 저장한 projected boundary-view subset 기준으로 다시 계산했다.

## 실행 명령어

```bash
.venv/bin/python tools/prepare_matrixcity_small_aerial_v1.py \
  --raw-dir data/matrixcity_smoke_raw/small_city/aerial \
  --output-dir data/matrix_city/aerial \
  --point-cloud /mnt/hddg1/3DGS/CityGaussianV1/output/mc_small_aerial_coarse_smoke/input.ply \
  --train-blocks block_1,block_4,block_7,block_10 \
  --test-blocks block_1_test \
  --link-mode symlink

.venv/bin/python train_large.py --config config/mc_small_aerial_subset_coarse_smoke.yaml --max_cache_num 64
.venv/bin/python render_large.py --config config/mc_small_aerial_subset_coarse_smoke.yaml --iteration 10 --custom_test data/matrix_city/aerial/test/block_all_test
.venv/bin/python metrics_large.py -m output/mc_small_aerial_subset_coarse_smoke -t block_all_test

.venv/bin/python data_partition_overlap.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml

.venv/bin/python train_large_overlap.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml --block_id 0 --max_cache_num 64
.venv/bin/python train_large_overlap.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml --block_id 1 --max_cache_num 64
.venv/bin/python train_large_overlap.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml --block_id 2 --max_cache_num 64
.venv/bin/python train_large_overlap.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml --block_id 3 --max_cache_num 64

.venv/bin/python merge_overlap.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml --iteration 100
.venv/bin/python render_large.py --config config/smoke_test/g1_overlap15_subset_smoke.yaml --iteration 100 --custom_test data/matrix_city/aerial/test/block_all_test
.venv/bin/python metrics_large.py -m output/g1_overlap15_subset_smoke -t block_all_test
PYTHONPATH=tools:${PYTHONPATH:-} .venv/bin/python tools/boundary_lpips.py \
  --output_dir output/g1_overlap15_subset_smoke \
  --test_set block_all_test \
  --iteration 100 \
  --crop_size 128 \
  --grid_block_dim 2,2,1

.venv/bin/python tools/select_boundary_views.py \
  --config config/mc_small_aerial_subset_c4_smoke.yaml \
  --test_dir data/matrix_city/aerial/test/block_all_test \
  --output_json output/boundary_analysis/subset4_block_all_test_strict.json

.venv/bin/python tools/filtered_metrics.py \
  --output_dir output/g1_overlap15_subset_smoke \
  --test_set block_all_test \
  --iteration 100 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json

.venv/bin/python tools/projected_boundary_lpips.py \
  --output_dir output/g1_overlap15_subset_smoke \
  --test_set block_all_test \
  --iteration 100 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json \
  --save_crops
```

## 정량 결과

| 항목 | coarse subset smoke | G1 overlap15 subset smoke | coarse 대비 |
|------|---------------------|---------------------------|-------------|
| SSIM | 0.5435 | 0.6248 | +0.0813 |
| PSNR | 16.5556 | 20.2971 | +3.7415 |
| LPIPS | 0.6480 | 0.6222 | -0.0258 |
| Boundary LPIPS (heuristic strip) | N/A | 0.5906 | N/A |
| Gaussian 수 | 3,841,754 | 3,918,215 | +76,461 |
| 모델 크기 | 909 MB | 927 MB | +18 MB |
| Average FPS | 60.04 | 58.61 | -1.44 |
| Max Memory(M) | 2177.39 | 2223.79 | +46.40 |

## Projected Boundary-View 재평가

- selector manifest: `output/boundary_analysis/subset4_block_all_test_strict.json`
- 선택된 view 수: `48 / 152`
- boundary coverage:
  - `x_0.5000 = 0`
  - `y_0.5000 = 48`
- 해석:
  - 현재 subset의 `block_1_test`는 실제로 보이는 내부 경계 중 `y` 축 seam만 커버한다.
  - 아래 표가 이번 보고서의 공식 경계 비교 기준이다.

| 항목 | G1 overlap15 projected boundary-view subset |
|------|---------------------------------------------|
| SSIM | 0.5948 |
| PSNR | 20.0533 |
| LPIPS | 0.6511 |
| Projected Boundary LPIPS | 0.6245 |
| 선택된 view 수 | 48 |

## 학습 로그 요약

- coarse subset smoke는 10 iteration 기준으로 정상 종료됐다.
- overlap partition 결과:
  - block 0: 1332 cameras
  - block 1: 937 cameras
  - block 2: 1604 cameras
  - block 3: 1099 cameras
- overlap 학습은 4개 cell 모두 100 iteration까지 정상 완료됐다.
- merge 결과:
  - 병합 전 총 Gaussian 수: 4,546,676
  - duplicate pruning 후 최종 Gaussian 수: 3,918,215
  - `blend_mode: soft`, `prune_duplicates: true`

## 렌더링 결과

- coarse smoke render:
  - `output/mc_small_aerial_subset_coarse_smoke/block_all_test/ours_10`
- overlap smoke render:
  - `output/g1_overlap15_subset_smoke/block_all_test/ours_100`
- boundary LPIPS (heuristic strip reference):
  - `output/g1_overlap15_subset_smoke/block_all_test/ours_100/boundary_lpips.json`
  - `x_0.5000 = 0.5911`
  - `y_0.5000 = 0.5901`
- projected boundary-view artifacts:
  - selector manifest: `output/boundary_analysis/subset4_block_all_test_strict.json`
  - filtered metrics: `output/g1_overlap15_subset_smoke/block_all_test/ours_100/boundary_view_metrics.json`
  - projected boundary LPIPS: `output/g1_overlap15_subset_smoke/block_all_test/ours_100/projected_boundary_lpips.json`
  - crop previews: `output/g1_overlap15_subset_smoke/block_all_test/ours_100/projected_boundary_crops`

## 이슈

- Hugging Face `MatrixCity` raw subset은 `train/`, `test/` 하위 구조와 flat PNG layout을 사용해서, `tools/prepare_matrixcity_small_aerial_v1.py`를 해당 구조에 맞게 보완했다.
- `render_large.py`는 현재 분리된 test 디렉토리를 자동으로 사용하지 않아 `--custom_test data/matrix_city/aerial/test/block_all_test` 우회가 필요했다.
- 공식 경계 비교는 이제 projected boundary-view subset 기준으로 계산한다. 기존 `tools/boundary_lpips.py` 값은 quick heuristic reference로만 유지한다.
- 현재 subset test는 `y_0.5000` 경계만 커버하고 `x_0.5000` 경계는 커버하지 못한다.
