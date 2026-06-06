# 2026-06-03 W2 30k Followup Runbook

## Current Goal

Run the best 15000-iteration xz10 grid result forward to 30000 iterations, then
build a higher-quality reusable merged manual-unit model and use that model as
the pretrain for another xz10 grid 30000 run.

The intended sequence is:

1. best xz10 grid 15k merged result -> xz10 grid 30k
2. reused coarse 30k -> manual-unit 30k -> merged manual-unit 30k
3. merged manual-unit 30k -> xz10 grid 30k

## Reused Artifacts

- Filtered W2 scene:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Coarse 30k:
  `output/w2_filtered_manual_passage_no415_coarse_30000/point_cloud/iteration_30000`
- Current best 15k merged grid result:
  `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/point_cloud/iteration_15000`
- Current best xz10 partition copied from:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered/data_partitions/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000.npy`

## Configs

### Best Grid 15k To Grid 30k

- Config:
  `config/smoke_test/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000.yaml`
- Output:
  `output/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000`
- Pretrain:
  `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/point_cloud/iteration_15000`
- Partition:
  `w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000`
- Empty cells prepared before launch:
  `0`, `4`, `5`, `9`

Launch command:

```bash
SKIP_PARTITION=1 \
SKIP_EXISTING_CELLS=1 \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=6700 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
./scripts/run_grid_citygs_experiment.sh \
  smoke_test/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000 \
  > logs/20260603_w2_best_grid15k_to_citygs_xz10_30000.log 2>&1 &
```

Current status:

- Completed at `2026-06-04T02:14:36+0000`.
- Parent PID at launch: `2178568`
- Sequence watcher PID: `2184635`
- No related process remained after completion.
- Log:
  `logs/20260603_w2_best_grid15k_to_citygs_xz10_30000.log`
- Sequence log:
  `logs/20260603_w2_30k_followup_sequence.log`
- Initial cell:
  `cell1`
- Initial filtered pretrain count:
  `669,077 / 1,895,774`
- Completion analysis:
  `docs/reports/20260604_w2_30k_followup_analysis.md`

Sequence watcher command:

```bash
FIRST_PID=2178568 \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
WAIT_INTERVAL_SECONDS=60 \
./scripts/run_w2_30k_followup_sequence.sh \
  > logs/20260603_w2_30k_followup_sequence.log 2>&1 &
```

## Manual-Unit 30k

This run creates the higher-quality reusable merged manual-unit model.

- Config:
  `config/smoke_test/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000.yaml`
- Output:
  `output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000`
- Pretrain:
  `output/w2_filtered_manual_passage_no415_coarse_30000/point_cloud/iteration_30000`
- Partition:
  `w2_filtered_manual_passage_no415_manual_units_coarse30k_30000`
- Range file:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt`
- Important setting:
  `unit_train_prune_until_iter: 30000`

Launch command after the best-grid 30k run is inspected:

```bash
CONFIG=smoke_test/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000 \
RANGE_FILE=data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=6800 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh \
  > logs/20260603_w2_manual_units_coarse30k_30000.log 2>&1 &
```

Expected merged model:

- `output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000/point_cloud/iteration_30000/point_cloud.ply`

## Manual-Unit 30k To Grid 30k

This run uses the higher-quality merged manual-unit 30k model as a common
pretrain for xz10 grid training.

- Config:
  `config/smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000.yaml`
- Output:
  `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`
- Pretrain:
  `output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000/point_cloud/iteration_30000`
- Partition:
  `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`

Launch command after the manual-unit 30k merged PLY exists and empty grid cells
are checked:

```bash
SKIP_PARTITION=1 \
SKIP_EXISTING_CELLS=1 \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=6900 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
./scripts/run_grid_citygs_experiment.sh \
  smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000 \
  > logs/20260603_w2_manual_units30k_to_citygs_xz10_30000.log 2>&1 &
```

Before launching this stage, compute or inspect the grid bounds-filtered
pretrain counts. If cells again have zero pretrain Gaussians, prepare explicit
0-vertex PLYs for those cells at `iteration_30000`.

The sequence watcher performs this check with:

```bash
.venv/bin/python tools/prepare_grid_empty_cells.py \
  --config config/smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000.yaml \
  --iteration 30000 \
  --prepare-empty-ply \
  --empty-template output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/cells/cell0/point_cloud_blocks/scale_1.0/iteration_15000/point_cloud.ply \
  --write-json output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000/diagnostics/grid_pretrain_counts_iter30000.json
```

## Validation Commands

```bash
bash -n scripts/run_grid_citygs_experiment.sh
bash -n scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
.venv/bin/python -m py_compile scene/__init__.py arguments/__init__.py utils/general_utils.py
.venv/bin/python -m py_compile tools/prepare_grid_empty_cells.py
```

## Notes

- The best-grid 30k run intentionally uses the current best merged grid 15k PLY
  as pretrain. It is not just a fresh 30k rerun from the manual-unit 15k PLY.
- The manual-unit 30k output name includes `manual_units_coarse30k_30000` so it
  can be reused later as a common high-quality merged unit model.
- The xz10 camera partition is reused because the source scene, block
  dimensions, and explicit AABB are unchanged.
