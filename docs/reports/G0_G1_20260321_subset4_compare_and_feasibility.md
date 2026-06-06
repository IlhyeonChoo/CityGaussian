# G0/G1 subset4 smoke 비교 및 4-block 실행 가능성

- 일시: 2026-03-21 KST
- 비교 대상:
  - G0 subset baseline smoke: `config/mc_small_aerial_subset_c4_smoke.yaml`
  - G1 overlap15 subset smoke: `config/smoke_test/g1_overlap15_subset_smoke.yaml`
- coarse pretrain:
  - `config/mc_small_aerial_subset_coarse_smoke.yaml`
  - `output/mc_small_aerial_subset_coarse_smoke/point_cloud/iteration_10`
- 데이터셋: MatrixCity `small_city/aerial` subset
  - train: `block_1, block_4, block_7, block_10` = 3504장
  - test: `block_1_test` = 152장
- GPU: NVIDIA GeForce RTX 4060 Ti, VRAM 16GB
- 환경:
  - local `.venv`
  - Python 3.11
  - PyTorch 2.7.1+cu128
  - CUDA 12.8
  - `TORCH_CUDA_ARCH_LIST=8.9`
- 비고:
  - 두 실험 모두 `2x2x1` partition과 같은 subset, 같은 coarse pretrain을 사용했다.
  - 렌더는 둘 다 `--custom_test data/matrix_city/aerial/test/block_all_test`로 실행했다.
  - 공식 비교는 `output/boundary_analysis/subset4_block_all_test_strict.json`의 projected boundary-view subset 기준으로 다시 계산했다.
  - 기존 strip crop Boundary LPIPS는 reference 값으로만 남긴다.

## 실행 명령어

```bash
.venv/bin/python data_partition.py --config config/mc_small_aerial_subset_c4_smoke.yaml

for block_id in 0 1 2 3; do
  .venv/bin/python train_large.py \
    --config config/mc_small_aerial_subset_c4_smoke.yaml \
    --block_id "$block_id" \
    --max_cache_num 64
done

.venv/bin/python merge.py --config config/mc_small_aerial_subset_c4_smoke.yaml --iteration 100
.venv/bin/python render_large.py \
  --config config/mc_small_aerial_subset_c4_smoke.yaml \
  --iteration 100 \
  --custom_test data/matrix_city/aerial/test/block_all_test
.venv/bin/python metrics_large.py -m output/mc_small_aerial_subset_c4_smoke -t block_all_test
PYTHONPATH=tools:${PYTHONPATH:-} .venv/bin/python tools/boundary_lpips.py \
  --output_dir output/mc_small_aerial_subset_c4_smoke \
  --test_set block_all_test \
  --iteration 100 \
  --crop_size 128 \
  --grid_block_dim 2,2,1

.venv/bin/python tools/select_boundary_views.py \
  --config config/mc_small_aerial_subset_c4_smoke.yaml \
  --test_dir data/matrix_city/aerial/test/block_all_test \
  --output_json output/boundary_analysis/subset4_block_all_test_strict.json

.venv/bin/python tools/filtered_metrics.py \
  --output_dir output/mc_small_aerial_subset_c4_smoke \
  --test_set block_all_test \
  --iteration 100 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json

.venv/bin/python tools/projected_boundary_lpips.py \
  --output_dir output/mc_small_aerial_subset_c4_smoke \
  --test_set block_all_test \
  --iteration 100 \
  --view_manifest output/boundary_analysis/subset4_block_all_test_strict.json \
  --save_crops

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

## 공식 비교: Projected Boundary-View subset

- selector manifest: `output/boundary_analysis/subset4_block_all_test_strict.json`
- 선택된 view 수: `48 / 152`
- boundary coverage:
  - `x_0.5000 = 0`
  - `y_0.5000 = 48`
- 현재 공식 비교는 실제로 보이는 `y` 축 seam만 대상으로 한다.

| 항목 | G0 non-overlap subset smoke | G1 overlap15 subset smoke | G1 - G0 |
|------|-----------------------------|---------------------------|---------|
| SSIM | 0.5918 | 0.5948 | +0.0030 |
| PSNR | 19.7919 | 20.0533 | +0.2614 |
| LPIPS | 0.6553 | 0.6511 | -0.0042 |
| Projected Boundary LPIPS | 0.6280 | 0.6245 | -0.0035 |
| 선택된 view 수 | 48 | 48 | 0 |

## Reference: 전체 test view 결과

| 항목 | G0 non-overlap subset smoke | G1 overlap15 subset smoke | G1 - G0 |
|------|-----------------------------|---------------------------|---------|
| SSIM | 0.6235 | 0.6248 | +0.0013 |
| PSNR | 20.0664 | 20.2971 | +0.2307 |
| LPIPS | 0.6214 | 0.6222 | +0.0008 |
| Boundary LPIPS (heuristic strip) | 0.5905 | 0.5906 | +0.0001 |
| Average FPS | 59.01 | 58.61 | -0.41 |
| Max Memory(M) | 2205.21 | 2223.79 | +18.58 |
| Gaussian 수 | 3,890,998 | 3,918,215 | +27,217 |
| 병합 PLY 크기 | 965.0 MB | 971.7 MB | +6.7 MB |
| output 디렉토리 크기 | 2.7 GB | 3.8 GB | +1.1 GB |

## 파티션/학습 비교

### 블록별 camera 수

| Block | G0 | G1 | 증가량 |
|------|----|----|--------|
| 0 | 1283 | 1332 | +49 |
| 1 | 906 | 937 | +31 |
| 2 | 1530 | 1604 | +74 |
| 3 | 1051 | 1099 | +48 |

### 이미지의 block 중복 할당 수

| multiplicity | G0 | G1 |
|-------------|----|----|
| 1개 block | 2381 | 2227 |
| 2개 block | 994 | 1129 |
| 3개 block | 115 | 105 |
| 4개 block | 14 | 43 |

### 100-iter smoke 학습 시간

`cfg_args` 생성 시각과 최종 `point_cloud.ply` 생성 시각 차이로 계산했다.

| 항목 | G0 | G1 |
|------|----|----|
| cell0 | 23.54 s | 25.31 s |
| cell1 | 24.28 s | 25.27 s |
| cell2 | 23.68 s | 25.40 s |
| cell3 | 23.49 s | 24.81 s |
| 4개 cell 합 | 94.98 s | 100.79 s |
| cell 평균 | 23.75 s | 25.20 s |

관찰:

- overlap15는 block별 camera 수와 중복 할당이 늘어서 100-iter 기준 학습 시간이 약 `+6.1%` 증가했다.
- projected boundary-view subset 기준으로는 G1 overlap15가 SSIM/PSNR/LPIPS/projected boundary LPIPS에서 모두 소폭 우세했다.
- 다만 이번 subset 공식 비교는 `y` 축 seam만 커버한다. `x` 축 seam에 대한 결론으로 일반화하면 안 된다.
- 렌더 비용과 모델 크기 차이도 작다. 4060 Ti 16GB 기준에서 두 방법 모두 렌더 단계는 여유가 있었다.

## 4-block 실행 가능성 추정

가정:

- 현재 subset 4개 raw block과 동일한 조건을 유지한다.
- `2x2x1` partition, `max_cache_num 64`, 같은 test/eval 절차를 사용한다.
- 100-iter smoke에서 측정한 `4개 cell 총 학습 시간`을 기준으로 학습 시간을 선형 근사한다.
- `partition`은 overlap smoke에서 실측한 `6분 43초`를 공통 one-time overhead로 사용했다.
  - baseline partition wall-clock은 별도 로그로 저장되지 않아, 같은 2x2 subset partition이라는 점을 근거로 유사 시간으로 추정했다.
- render/metrics/boundary는 현재 머신 실측값을 사용했다.

| 방법 | 5k 추정 | 10k 추정 | 30k 추정 |
|------|---------|----------|----------|
| G0 non-overlap | 약 1.55시간 | 약 2.87시간 | 약 8.14시간 |
| G1 overlap15 | 약 1.62시간 | 약 3.02시간 | 약 8.62시간 |

해석:

- 4060 Ti 16GB 기준에서 subset 4-block은 두 방법 모두 실행 가능하다고 판단한다.
- overlap15는 non-overlap 대비 대략 `0.07시간`, `0.15시간`, `0.48시간` 정도 더 오래 걸리는 수준으로 추정된다.
- 저장 공간도 충분하다. 현재 루트 파티션 여유 공간은 약 `576 GB`이고, smoke output은 G0 `2.7 GB`, G1 `3.8 GB`였다.
- 다만 30k는 장시간 단일 GPU 작업이라 late densification 구간에서 VRAM 변동이 생길 수 있다.
  - OOM이 보이면 첫 대응은 `--max_cache_num 32`로 낮추는 것이다.
  - 그 다음 대응은 `--resolution`을 낮추거나, 5k/10k pilot 후 본편으로 가는 것이다.

## 결론

- 전체 test view 기준 차이는 작았지만, 실제 경계가 보이는 projected boundary-view subset 기준으로는 G1 overlap15가 G0 non-overlap보다 일관되게 조금 더 좋았다.
- 품질 개선 폭은 작고, 현재 subset은 `y` 경계 한 축만 비교했다.
- 현재 하드웨어에서는 두 방법 모두 subset 4-block 기준 pilot과 30k 본편까지 현실적으로 돌릴 수 있다.
- 다음 우선순위는 `5k 또는 10k pilot`을 두 방법 모두 같은 subset에서 한 번 더 돌리고, `x` 경계까지 실제로 보이는 test block을 추가해 coverage를 넓히는 것이다.
