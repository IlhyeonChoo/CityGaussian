# G0/G1 subset4 5k canonical pilot 결과

- 일시: 2026-03-22 KST
- 공식 비교 기준:
  - G0 non-overlap 5k: `config/mc_small_aerial_subset_c4_5k.yaml`
  - G1 overlap15 5k: `config/g1_overlap15_subset_5k.yaml`
- coarse pretrain:
  - `config/mc_small_aerial_subset_coarse_5k.yaml`
  - `output/mc_small_aerial_subset_coarse_5k/point_cloud/iteration_5000`
- 데이터셋: MatrixCity `small_city/aerial` subset
  - train: `block_1, block_4, block_7, block_10` = 3504장
  - test: `block_1_test` = 152장
- GPU: NVIDIA GeForce RTX 4060 Ti, VRAM 16GB
- 환경:
  - local `.venv`
  - Python 3.11
  - PyTorch 2.7.1+cu128
  - CUDA 12.8
  - block 학습 fallback: `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, `--max_cache_num 32`
- 비고:
  - 이 문서는 현재 `subset 4-block`의 공식 pilot 비교 기준이다.
  - 기존 `100 iter smoke` 비교 문서인 `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md`와 `docs/reports/G1_20260321_overlap15_subset_smoke.md`는 reference로 그대로 보존한다.
  - 공식 경계 비교는 `output/boundary_analysis/subset4_block_all_test_strict.json`의 strict boundary-view subset 기준이다.

## 실행 명령어

```bash
source .venv/bin/activate
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

.venv/bin/python train_large.py \
  --config config/mc_small_aerial_subset_coarse_5k.yaml \
  --max_cache_num 32

.venv/bin/python data_partition.py --config config/mc_small_aerial_subset_c4_5k.yaml
for block_id in 0 1 2 3; do
  .venv/bin/python train_large.py \
    --config config/mc_small_aerial_subset_c4_5k.yaml \
    --block_id "$block_id" \
    --max_cache_num 32
done
.venv/bin/python merge.py --config config/mc_small_aerial_subset_c4_5k.yaml --iteration 5000
.venv/bin/python render_large.py \
  --config config/mc_small_aerial_subset_c4_5k.yaml \
  --iteration 5000 \
  --custom_test data/matrix_city/aerial/test/block_all_test
.venv/bin/python metrics_large.py -m output/mc_small_aerial_subset_c4_5k -t block_all_test
.venv/bin/python tools/filtered_metrics.py \
  --output_dir output/mc_small_aerial_subset_c4_5k \
  --test_set block_all_test \
  --iteration 5000 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json
PYTHONPATH=tools:${PYTHONPATH:-} .venv/bin/python tools/projected_boundary_lpips.py \
  --output_dir output/mc_small_aerial_subset_c4_5k \
  --test_set block_all_test \
  --iteration 5000 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json \
  --save_crops

.venv/bin/python data_partition_overlap.py --config config/g1_overlap15_subset_5k.yaml
for block_id in 0 1 2 3; do
  .venv/bin/python train_large_overlap.py \
    --config config/g1_overlap15_subset_5k.yaml \
    --block_id "$block_id" \
    --max_cache_num 32
done
.venv/bin/python merge_overlap.py --config config/g1_overlap15_subset_5k.yaml --iteration 5000
.venv/bin/python render_large.py \
  --config config/g1_overlap15_subset_5k.yaml \
  --iteration 5000 \
  --custom_test data/matrix_city/aerial/test/block_all_test
.venv/bin/python metrics_large.py -m output/g1_overlap15_subset_5k -t block_all_test
.venv/bin/python tools/filtered_metrics.py \
  --output_dir output/g1_overlap15_subset_5k \
  --test_set block_all_test \
  --iteration 5000 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json
PYTHONPATH=tools:${PYTHONPATH:-} .venv/bin/python tools/projected_boundary_lpips.py \
  --output_dir output/g1_overlap15_subset_5k \
  --test_set block_all_test \
  --iteration 5000 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json \
  --save_crops
```

## 공식 비교 기준

- selector manifest: `output/boundary_analysis/subset4_block_all_test_strict.json`
- 선택된 view 수: `48 / 152`
- boundary coverage:
  - `x_0.5000 = 0`
  - `y_0.5000 = 48`
- 현재 공식 비교는 실제로 보이는 `y` seam만 대상으로 한다.

## 정량 결과

### 전체 test view

| 지표 | G0 non-overlap 5k | G1 overlap15 5k | G1 - G0 |
|------|-------------------|-----------------|---------|
| SSIM | 0.7405 | 0.7209 | -0.0196 |
| PSNR | 25.3124 | 24.1718 | -1.1407 |
| LPIPS | 0.4607 | 0.4758 | +0.0151 |

### Strict boundary-view subset

| 지표 | G0 non-overlap 5k | G1 overlap15 5k | G1 - G0 |
|------|-------------------|-----------------|---------|
| SSIM | 0.7211 | 0.6692 | -0.0519 |
| PSNR | 24.7609 | 21.9210 | -2.8400 |
| LPIPS | 0.4822 | 0.5218 | +0.0396 |
| Projected Boundary LPIPS | 0.4534 | 0.5042 | +0.0508 |
| 선택된 view 수 | 48 | 48 | 0 |

## 비용 및 모델 크기

| 항목 | G0 non-overlap 5k | G1 overlap15 5k | G1 - G0 |
|------|-------------------|-----------------|---------|
| Average FPS | 20.96 | 19.92 | -1.04 |
| Max Memory(M) | 5495.22 | 5689.48 | +194.26 |
| Gaussian 수 | 9,758,275 | 9,779,872 | +21,597 |
| 병합 PLY 크기 | 2.420 GB | 2.425 GB | +5.4 MB |
| output 디렉토리 크기 | 5.5 GB | 7.9 GB | +2.4 GB |

## 블록별 학습 시간

`cfg_args` 생성 시각과 `iteration_5000/point_cloud.ply` 생성 시각 차이로 계산했다.

| 항목 | G0 | G1 |
|------|----|----|
| cell0 | 1447.20 s | 1495.29 s |
| cell1 | 1508.28 s | 1575.05 s |
| cell2 | 1385.01 s | 1411.97 s |
| cell3 | 1469.34 s | 1498.06 s |
| 4개 cell 합 | 5809.83 s | 5980.37 s |
| cell 평균 | 1452.46 s | 1495.09 s |

관찰:

- 5k 기준 현재 subset에서는 G0 non-overlap이 전체 test와 strict boundary-view 모두에서 G1 overlap15보다 우세했다.
- overlap15는 model size와 render memory를 약간 늘렸지만, block 학습 시간 증가는 `+170.54 s`로 약 `+2.9%` 수준이었다.
- 현재 결론은 `block_1_test`가 `y_0.5000` seam만 커버한다는 범위 안에서만 유효하다.

## 10k 상태 메모

`10k`는 이번 문서의 공식 결론에 포함하지 않는다.

- coarse 10k는 완료됨:
  - `output/mc_small_aerial_subset_coarse_10k/point_cloud/iteration_10000/point_cloud.ply`
- G0 10k는 부분 완료 상태:
  - `cell0` 완료
  - `cell1`은 TensorBoard event 기준 `step 3819`, `num_points 9,287,927`에서 중단
  - traceback는 남아 있지 않지만, 4060 Ti 16GB에서의 이전 `max_cache_num 64` OOM 패턴과 맞아 `OOM 의심`으로 기록한다
- G1 10k는 아직 시작하지 않았다.
- 따라서 현재 공식 pilot 결론은 `5k`까지만 사용한다. `10k`는 `max_cache_num 32` 기준으로 다시 진행할 예정이다.

## 결과 파일

- G0:
  - `output/mc_small_aerial_subset_c4_5k/results.json`
  - `output/mc_small_aerial_subset_c4_5k/block_all_test/ours_5000/boundary_view_metrics.json`
  - `output/mc_small_aerial_subset_c4_5k/block_all_test/ours_5000/projected_boundary_lpips.json`
- G1:
  - `output/g1_overlap15_subset_5k/results.json`
  - `output/g1_overlap15_subset_5k/block_all_test/ours_5000/boundary_view_metrics.json`
  - `output/g1_overlap15_subset_5k/block_all_test/ours_5000/projected_boundary_lpips.json`
