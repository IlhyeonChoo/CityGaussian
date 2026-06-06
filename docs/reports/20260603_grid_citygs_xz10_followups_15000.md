# 2026-06-03 W2 Grid CityGaussian XZ10 Followups 15000

## Current Goal

Run two follow-up experiments requested after the manual passage split remained
poor at 15000 iterations:

1. Repartition the current merged manual-unit result with the original
   CityGaussian grid-style split, train each grid block to 15000, then merge.
2. Partition the coarse result with the original CityGaussian grid-style split,
   train each grid block to 15000, then merge.

Both experiments use the same filtered W2 scene, no 405/410/416 and no 415.

## Code And Config Changes

The grid followups use an opt-in pretrained Gaussian bounds filter so a grid
cell can load only the portion of a large pretrain PLY that falls inside that
cell's contracted grid bounds.

- `arguments/__init__.py`
  - Added `grid_pretrain_filter_mode`
  - Added `grid_pretrain_filter_padding`
- `utils/general_utils.py`
  - Added default values for non-CLI model param construction.
- `scene/__init__.py`
  - Added grid block bounds helpers.
  - Added `grid_pretrain_filter_mode: bounds` support for grid block training.
- `scripts/run_grid_citygs_experiment.sh`
  - Added a generic grid CityGaussian wrapper for partition, block training,
    strict merge, render, and metrics.

The new behavior is opt-in. Existing configs keep the default
`grid_pretrain_filter_mode: none`.

Validation:

```bash
bash -n scripts/run_grid_citygs_experiment.sh
.venv/bin/python -m py_compile scene/__init__.py arguments/__init__.py utils/general_utils.py
```

## Shared Setup

- Source scene:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Grid:
  `block_dim: [5, 1, 2]`
- AABB:
  `[-10.5, -4.0, -9.0, 5.8, 4.0, 7.0]`
- Iterations:
  `15000`
- Review subset:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000`
- Test set name:
  `manual_passage_review_15000`

## Experiment 1: Coarse Result To Grid

This is the clean CityGaussian-order baseline:

coarse 30000 result -> original CityGaussian grid partition -> grid block
15000 training -> merge -> render -> metrics.

Config:

- `config/smoke_test/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000.yaml`

Pretrain:

- `output/w2_filtered_manual_passage_no415_coarse_30000/point_cloud/iteration_30000`

Exact command:

```bash
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=6400 \
./scripts/run_grid_citygs_experiment.sh \
  smoke_test/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000 \
  > logs/20260603_w2_coarse_citygs_xz10_15000.log 2>&1 &
```

Output:

- Output directory:
  `output/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000`
- Merged PLY:
  `output/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000/point_cloud/iteration_15000/point_cloud.ply`
- Log:
  `logs/20260603_w2_coarse_citygs_xz10_15000.log`

Camera distribution:

| Cell | Cameras |
|------|---------|
| cell0 | 249 |
| cell1 | 1834 |
| cell2 | 2053 |
| cell3 | 230 |
| cell4 | 103 |
| cell5 | 103 |
| cell6 | 204 |
| cell7 | 2178 |
| cell8 | 2608 |
| cell9 | 241 |

Merged points:

| Cell | Points | Cell PLY Bytes |
|------|--------|----------------|
| cell0 | 0 | 1,526 |
| cell1 | 405,540 | 100,575,451 |
| cell2 | 195,045 | 48,372,691 |
| cell3 | 98,425 | 24,410,930 |
| cell4 | 8 | 3,510 |
| cell5 | 0 | 1,526 |
| cell6 | 44,719 | 11,091,842 |
| cell7 | 406,560 | 100,828,411 |
| cell8 | 206,923 | 51,318,435 |
| cell9 | 19 | 6,239 |
| **Total** | **1,357,239** | |

Metrics on `manual_passage_review_15000`:

| Metric | Value |
|--------|-------|
| SSIM | 0.8241367 |
| PSNR | 20.3612232 |
| LPIPS | 0.4033709 |
| Gaussians | 1,357,239 |
| Average FPS | 116.5108 |
| Max Memory | 1510.3149 M |

## Experiment 2: Manual Unit Merged Result To Grid

This experiment uses the current coarse-first manual-unit merged 15000 result
as the pretrain, then repartitions it with the same xz10 CityGaussian grid.

Config:

- `config/smoke_test/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000.yaml`

Pretrain:

- `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/point_cloud/iteration_15000`

Important settings:

- `grid_pretrain_filter_mode: bounds`
- `grid_pretrain_filter_padding: 0.02`
- `unit_merge_strict_iteration: True`

The xz10 camera partition from Experiment 1 was reused because the source
scene, explicit AABB, and block dimensions are identical:

- Source partition:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/data_partitions/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000.npy`
- Target partition:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/data_partitions/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000.npy`

The grid bounds filter found no pretrained Gaussians for cells
`0`, `4`, `5`, and `9`. Those cells were represented by 0-vertex PLYs copied
from the completed coarse-grid run, and block training skipped existing cell
outputs. This is an experimental workaround and should remain explicit when
interpreting the result.

Failed initial run:

```bash
SKIP_PARTITION=1 \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=6500 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
./scripts/run_grid_citygs_experiment.sh \
  smoke_test/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000 \
  > logs/20260603_w2_repartition_merged15k_citygs_xz10_15000.log 2>&1 &
```

Failure:

- `Grid bounds filter removed all pretrained gaussians for block_id 0.`

Successful rerun:

```bash
SKIP_PARTITION=1 \
SKIP_EXISTING_CELLS=1 \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=6600 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
./scripts/run_grid_citygs_experiment.sh \
  smoke_test/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000 \
  > logs/20260603_w2_repartition_merged15k_citygs_xz10_15000_rerun.log 2>&1 &
```

Output:

- Output directory:
  `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000`
- Merged PLY:
  `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/point_cloud/iteration_15000/point_cloud.ply`
- Failed log:
  `logs/20260603_w2_repartition_merged15k_citygs_xz10_15000.log`
- Successful rerun log:
  `logs/20260603_w2_repartition_merged15k_citygs_xz10_15000_rerun.log`

Bounds-filtered pretrain counts:

| Cell | Filtered Pretrain |
|------|-------------------|
| cell0 | 0 |
| cell1 | 1,044,043 |
| cell2 | 1,209,364 |
| cell3 | 216,918 |
| cell4 | 0 |
| cell5 | 0 |
| cell6 | 235,169 |
| cell7 | 2,339,755 |
| cell8 | 1,641,772 |
| cell9 | 0 |

Merged points:

| Cell | Points | Cell PLY Bytes |
|------|--------|----------------|
| cell0 | 0 | 1,526 |
| cell1 | 545,768 | 135,351,995 |
| cell2 | 272,753 | 67,644,275 |
| cell3 | 115,957 | 28,758,867 |
| cell4 | 0 | 1,526 |
| cell5 | 0 | 1,526 |
| cell6 | 54,852 | 13,604,826 |
| cell7 | 570,730 | 141,542,571 |
| cell8 | 335,714 | 83,258,603 |
| cell9 | 0 | 1,526 |
| **Total** | **1,895,774** | |

Metrics on `manual_passage_review_15000`:

| Metric | Value |
|--------|-------|
| SSIM | 0.8428190 |
| PSNR | 21.7424717 |
| LPIPS | 0.3811370 |
| Gaussians | 1,895,774 |
| Average FPS | 93.9608 |
| Max Memory | 1918.5264 M |

## Comparison

Same 36-view `manual_passage_review_15000` subset:

| Run | Merged Gaussians | SSIM | PSNR | LPIPS |
|-----|------------------|------|------|-------|
| Manual unit 15k | 4,991,356 | 0.7784863 | 15.5607643 | 0.4365648 |
| Manual unit coarse-first 15k | 4,896,739 | 0.7827049 | 15.8133736 | 0.4396092 |
| Coarse -> grid xz10 15k | 1,357,239 | 0.8241367 | 20.3612232 | 0.4033709 |
| Merged-unit -> grid xz10 15k | 1,895,774 | 0.8428190 | 21.7424717 | 0.3811370 |

Compared with the manual unit coarse-first 15k result, the merged-unit-to-grid
result has:

- `SSIM +0.0601`
- `PSNR +5.9291`
- `LPIPS -0.0585`
- `-3,000,965` merged Gaussians

Compared with the clean coarse-to-grid result, the merged-unit-to-grid result
has:

- `SSIM +0.0187`
- `PSNR +1.3812`
- `LPIPS -0.0222`
- `+538,535` merged Gaussians

## Visual Review

Contact sheets:

- All 36 frames:
  `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/manual_passage_review_15000_grid_followups_contact_sheet.jpg`
- Selected larger frames:
  `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/manual_passage_review_15000_grid_followups_selected_contact_sheet.jpg`

The manual-unit rows remain heavily blurred or fogged in many classroom and
passage views. Both grid runs are visibly more stable. The
merged-unit-to-grid result is usually the strongest of the tested options and
preserves more room and corridor structure than the clean coarse-to-grid run.

Remaining artifacts are still visible in selected views, especially around
door/corridor boundaries and dark reflective regions. Notable frames include
`00004`, `00005`, `00008`, `00029`, and `00035`.

## Interpretation

The original CityGaussian-style grid split is currently a much stronger
direction than continuing the 10 manual unit blocks as-is.

The best 15000-iteration candidate from this run is:

- `w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000`

The result is not final because empty grid cells were handled by explicit
0-vertex PLYs and some visual artifacts remain. However, both metrics and
visual review support escalating this grid-repartition direction to a longer
run before spending more time on the manual passage unit layout.

## Risks And Next Checks

- Empty cells `0`, `4`, `5`, and `9` had cameras but no filtered pretrain
  Gaussians in the merged-unit-to-grid experiment. This may be acceptable if
  adjacent grid blocks cover those review views, but it should be tracked.
- The xz10 grid has sparse or dead cells. A different grid shape or AABB may
  improve stability.
- Metrics were measured on the 36-view manual passage review subset only.
  Additional room-specific and passage-specific review subsets should be used
  before declaring the run solved.
- If the selected contact sheet remains acceptable to manual review, run the
  merged-unit-to-grid config at 30000 iterations.

## Handoff

- Current goal: compare two CityGaussian-grid followups at 15000 iterations.
- Files touched:
  `arguments/__init__.py`, `utils/general_utils.py`, `scene/__init__.py`,
  `scripts/run_grid_citygs_experiment.sh`,
  `config/smoke_test/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000.yaml`,
  `config/smoke_test/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000.yaml`,
  this report.
- What changed: added opt-in grid pretrained bounds filtering and a reusable
  grid experiment wrapper, then ran the two 15000-iteration followups.
- What was validated: Python compile, wrapper shell syntax, both completed
  renders, both completed metrics, visual contact sheets.
- What remains uncertain or risky: empty grid cells in the
  merged-unit-to-grid experiment and remaining visual artifacts in some
  boundary frames.
- Recommended next owner: Agent 2 for training/merge execution, Agent 3 for
  expanded visual and metric analysis.
- Recommended next action: if manual review accepts the selected contact
  sheet, run `w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10`
  at 30000 iterations.
