# W2 Grid30k To Manual-Unit30k Run

## Goal

Run the current best xz10 grid 30k candidate through the manual-unit
partition for another 30k iterations:

1. Pretrain from the best 30k grid candidate.
2. Repartition with the manual 10-unit room/passage layout.
3. Train each manual unit for 30k iterations.
4. Strict-merge iteration 30000, then render and evaluate the 36-view
   `manual_passage_review_15000` subset.

This is a follow-up to the 30k analysis in
`docs/reports/20260604_w2_30k_followup_analysis.md`.

## Config

- Config:
  `config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000.yaml`
- Output:
  `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000`
- Log:
  `logs/20260604_w2_best_grid30k_to_manual_units_30000.log`
- Partition name:
  `w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000`
- Partition mode:
  `colmap_unit`
- Unit layout:
  `401`, `404`, `409`, `411`, `412`, `413`, `414`,
  `passage1`, `passage2`, `passage3`
- Iterations:
  `30000`
- Pretrain:
  `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000/point_cloud/iteration_30000`

The selected pretrain is the previous best 36-view render candidate from the
30k follow-up sequence.

## Exact Command

```bash
CONFIG=smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000 \
RANGE_FILE=data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
PYTHON_BIN=.venv/bin/python \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=20 \
PORT=7000 \
TRAIN_EXTRA_ARGS='--max_cache_num 256' \
SKIP_EXISTING_CELLS=1 \
RUN_RENDER=1 \
RUN_METRICS=1 \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh \
  > logs/20260604_w2_best_grid30k_to_manual_units_30000.log 2>&1 &
```

Background wrapper PID at launch: `2760695`.

## Partition Diagnostics

Manual partition creation command:

```bash
.venv/bin/python tools/create_colmap_unit_partition.py \
  --source-path data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered \
  --partition-name w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000 \
  --range-file data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
  --range-unit-names 401 404 409 411 412 413 414 passage1 passage2 passage3 \
  --range-overlap-policy single_owner \
  --camera-outlier-filter robust \
  --camera-outlier-z-threshold 8.0 \
  --camera-outlier-min-distance 5.0 \
  --camera-outlier-distance-ratio 4.0 \
  --point-source-path data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416 \
  --point-filter-box -12.0 -4.0 -14.0 12.0 7.0 8.0 \
  --core-point-policy single_owner \
  --validate-point-cloud-length \
  --overwrite
```

Camera counts by unit:

| Unit | Cameras |
|------|---------|
| 401 | 395 |
| 404 | 379 |
| 409 | 906 |
| 411 | 789 |
| 412 | 568 |
| 413 | 465 |
| 414 | 644 |
| passage1 | 476 |
| passage2 | 512 |
| passage3 | 767 |

Unassigned cameras: `679`.

The unassigned camera count is expected for this no-415 manual split and is
kept as a run risk, not silently corrected.

## Pretrain Bound Counts

Diagnostic file:
`output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/diagnostics/unit_pretrain_counts_iter30000.json`

Expanded manual-unit bounds counts from the grid 30k pretrain:

| Unit | Pretrain Gaussians |
|------|--------------------|
| 401 | 136,959 |
| 404 | 193,456 |
| 409 | 461,769 |
| 411 | 607,768 |
| 412 | 809,333 |
| 413 | 567,059 |
| 414 | 297,055 |
| passage1 | 1,466,913 |
| passage2 | 622,842 |
| passage3 | 1,589,714 |

Empty units: none.

Risk: `passage1` and `passage3` receive very large pretrain subsets, so those
blocks may be slower and may still carry density conflicts from the grid merge.

## Initial Status

Status at `2026-06-04 03:29 UTC`:

- Wrapper PID `2760695` is running.
- Active CUDA process PID `2760846` uses about `6910 MiB`.
- `cell0` is training normally.
- Initial log shows `Filtered Cameras: 395`, `Filtered unit point cloud:
  51949 / 1274646 points`, and `Filtered pretrained gaussians:
  136959 / 2057987`.
- No traceback, OOM, or explicit training error was present in the log at the
  initial check.

The wrapper's `No GPU available. Retrying in 10 seconds.` line is expected
while one block owns the GPU and the launcher waits to schedule another block.

## Current Run State

Partial. Training is in progress.

Expected next artifacts after completion:

- Merged PLY:
  `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/point_cloud/iteration_30000/point_cloud.ply`
- Render output:
  `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/manual_passage_review_15000/ours_30000/renders`
- Metrics JSON:
  `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/manual_passage_review_15000/results.json`

## Handoff

- Current goal: finish grid30k -> manual-unit30k, then inspect render and
  metrics.
- Files touched:
  `config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000.yaml`,
  this report.
- What changed: added a runnable config, generated manual-unit partition
  metadata, started the 30k wrapper.
- What was validated: config parses at shell/script level, pretrain PLY exists,
  partition has all 10 units non-empty, pretrain bounds counts have no empty
  unit, and early training log has no fatal error.
- What remains uncertain: passage-heavy units may still introduce density
  conflicts after merge; final quality must be judged from merged render.
- Recommended next owner: Agent 2 for training/merge monitoring, Agent 3 for
  result interpretation after metrics/render completion.
- Recommended next action: monitor the log through all cells, then compare
  final metrics and contact sheets against
  `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`.


## Completion Update

Completed at `2026-06-04 07:31 UTC`.

Final artifacts:

- Merged PLY: `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/point_cloud/iteration_30000/point_cloud.ply`
- Metrics JSON: `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/results.json`
- Per-view JSON: `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/per_view.json`
- Selected comparison sheet: `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/manual_passage_review_15000_grid30k_to_manual30k_selected_compare.jpg`

Final metrics on `manual_passage_review_15000` 36 train views:

| Run | SSIM | PSNR | LPIPS | Gaussians |
|-----|------|------|-------|-----------|
| grid30k -> manual-unit30k | 0.7822402 | 15.9809046 | 0.4517397 | 7,248,911 |
| previous best: manual-unit30k -> xz10 grid30k | 0.8589663 | 23.4472618 | 0.3599922 | 2,057,987 |
| best grid15k -> xz10 grid30k | 0.8566074 | 23.3606491 | 0.3640910 | 2,076,198 |
| direct manual-unit30k | 0.7765912 | 15.3306208 | 0.4488924 | 5,980,856 |

Delta against the previous best: SSIM `-0.0767`, PSNR `-7.4664`, LPIPS `+0.0917`. PSNR improved on only `1 / 36` views, SSIM on `2 / 36`, and LPIPS on `3 / 36`.

Merged block counts: `680079`, `599246`, `772708`, `885434`, `1041030`, `803516`, `714116`, `489777`, `811155`, `451850`; total `7,248,911`. The merged PLY is `1.7G`, much larger than the previous best `487M` PLY.

Overlap diagnostic file: `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/diagnostics/unit_overlap_iter30000_sample50000.json`. All units had `outside_expanded=0`, so the regression is not bounds leakage. Top close-center pairs at threshold `0.2` were `411<->412` (`0.835`), `412<->413` (`0.743`), `401<->passage1` (`0.739`), `412<->passage3` (`0.719`), `414<->passage1` (`0.711`), and `passage1<->passage2` (`0.670`).

Conclusion: this branch is not a better candidate. It regresses almost to the direct manual-unit30k failure mode. Keep `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000` as the current best candidate, and do not continue this branch unless a conflict-aware merge or post-merge deduplication step is added.
