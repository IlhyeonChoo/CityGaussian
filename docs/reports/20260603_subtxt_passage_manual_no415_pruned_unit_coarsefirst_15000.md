# 2026-06-03 Subtxt Manual Passage No415 Pruned Unit Coarse-First 15000

## Current Goal

Re-run the W2 manual passage split in the original CityGaussian order:
coarse training first, then partition, unit training, merge, render, and
metrics.

This report supersedes the earlier non-coarse 15000 run only for coarse-first
interpretation. The earlier run remains useful as a comparison baseline.

## Config

- Coarse config:
  `config/smoke_test/w2_filtered_manual_passage_no415_coarse_30000.yaml`
- Unit config:
  `config/smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000.yaml`
- Range file:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt`
- Source scene:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Unit partition:
  `scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units`
- Pretrain path used by unit training:
  `output/w2_filtered_manual_passage_no415_coarse_30000/point_cloud/iteration_30000`
- Unit split:
  `401`, `404`, `409`, `411`, `412`, `413`, `414`, `passage1`,
  `passage2`, `passage3`
- Important unit settings:
  `unit_init_point_filter=True`, `unit_init_point_source=core`,
  `unit_init_point_filter_mode=membership_and_bounds`,
  `unit_pretrain_filter_mode=bounds`, `unit_save_filter_mode=bounds`,
  `unit_train_prune_mode=bounds`, `unit_merge_filter_mode=bounds`,
  `unit_merge_strict_iteration=True`, `unit_aabb_margin=0.5`,
  `unit_aabb_margin_ratio=0.05`

## Exact Commands

Coarse:

```bash
CUDA_VISIBLE_DEVICES=0 WANDB_MODE=offline .venv/bin/python train_large.py \
  --config config/smoke_test/w2_filtered_manual_passage_no415_coarse_30000.yaml \
  --port 6300
```

Unit partition, block training, and merge:

```bash
CONFIG=smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000 \
RANGE_FILE=data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=5 \
PYTHON_BIN=.venv/bin/python \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
```

Overlap diagnostic:

```bash
.venv/bin/python tools/analyze_unit_gaussian_overlap.py \
  --config config/smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000.yaml \
  --output output/w2_filtered_manual_passage_no415_coarsefirst_units_15000 \
  --iteration 15000 \
  --thresholds 0.05 0.1 0.2 \
  --sample-per-unit 200000 \
  --write-json output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/diagnostics/unit_gaussian_overlap_iter15000_sample200k.json
```

Render:

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python render_large.py \
  --config config/smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000.yaml \
  --iteration 15000 \
  --custom_test data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000
```

Metrics:

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python metrics_large.py \
  --model_paths output/w2_filtered_manual_passage_no415_coarsefirst_units_15000 \
  --test_sets manual_passage_review_15000
```

## Logs

- Coarse log:
  `logs/20260603_w2_filtered_manual_passage_no415_coarse_30000.log`
- Unit/merge log:
  `logs/20260603_w2_filtered_manual_passage_no415_coarsefirst_units_15000.log`
- Render log:
  `logs/20260603_w2_filtered_manual_passage_no415_coarsefirst_units_15000_render.log`
- Metrics log:
  `logs/20260603_w2_filtered_manual_passage_no415_coarsefirst_units_15000_metrics.log`

## Coarse Result

The fresh coarse run completed successfully.

- Output PLY:
  `output/w2_filtered_manual_passage_no415_coarse_30000/point_cloud/iteration_30000/point_cloud.ply`
- PLY size: `59,063,475` bytes
- Iteration 30000 train metrics:
  `L1 0.0708830737`, `PSNR 19.9275604248`

Unit training did use this coarse output. The block logs contain filtered
pretrained Gaussian counts from the `238,153` coarse Gaussians.

## Output

- Output directory:
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000`
- Merged PLY:
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/point_cloud/iteration_15000/point_cloud.ply`
- Merged PLY size: `1,214,392,804` bytes
- Merged Gaussian count: `4,896,739`

All 10 unit blocks trained to iteration 15000 and merged successfully. No
`Traceback`, `OutOfMemory`, `ValueError`, or missing strict-iteration PLY was
observed in the completed run.

## Block Results

| Cell | Unit | Filtered Pretrain | Merged Points | Cell PLY Bytes |
|------|------|-------------------|---------------|----------------|
| cell0 | 401 | 16,590 | 459,148 | 113,870,235 |
| cell1 | 404 | 40,197 | 439,993 | 109,119,795 |
| cell2 | 409 | 42,806 | 521,431 | 129,316,419 |
| cell3 | 411 | 59,697 | 608,545 | 150,920,691 |
| cell4 | 412 | 83,914 | 727,910 | 180,523,211 |
| cell5 | 413 | 69,724 | 523,075 | 129,724,131 |
| cell6 | 414 | 64,219 | 539,029 | 133,680,723 |
| cell7 | passage1 | 178,287 | 254,203 | 63,043,875 |
| cell8 | passage2 | 72,958 | 602,549 | 149,433,683 |
| cell9 | passage3 | 189,065 | 220,856 | 54,773,819 |

## Bounds And Overlap Diagnostic

Diagnostic JSON:

- `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/diagnostics/unit_gaussian_overlap_iter15000_sample200k.json`

Per-unit summary:

| Unit | Points | Inside Raw Bounds | Outside Expanded Bounds | P95 Max Scale |
|------|--------|-------------------|-------------------------|---------------|
| 401 | 459,148 | 0.974 | 0 | 0.0306 |
| 404 | 439,993 | 0.960 | 0 | 0.0310 |
| 409 | 521,431 | 0.966 | 0 | 0.0367 |
| 411 | 608,545 | 0.965 | 0 | 0.0395 |
| 412 | 727,910 | 0.952 | 0 | 0.0430 |
| 413 | 523,075 | 0.932 | 0 | 0.0519 |
| 414 | 539,029 | 0.910 | 0 | 0.0341 |
| passage1 | 254,203 | 0.936 | 0 | 0.0924 |
| passage2 | 602,549 | 0.962 | 0 | 0.0513 |
| passage3 | 220,856 | 0.930 | 0 | 0.1252 |

Expanded bounds leakage is zero for every unit, so the save/merge bounds filter
is working. The remaining issue is not a simple out-of-bounds leak.

Top close-center pairs at threshold `0.2`:

| Pair | Mean Close Ratio | Left | Right | AABB Overlap |
|------|------------------|------|-------|--------------|
| 411 <-> 412 | 0.814 | 0.921 | 0.707 | 58.443 |
| 401 <-> passage1 | 0.772 | 0.999 | 0.546 | 32.020 |
| 412 <-> 413 | 0.746 | 0.819 | 0.673 | 37.042 |
| 412 <-> passage3 | 0.723 | 0.997 | 0.449 | 141.079 |
| 414 <-> passage1 | 0.709 | 0.999 | 0.419 | 52.477 |
| 411 <-> passage3 | 0.688 | 0.995 | 0.382 | 105.516 |
| passage2 <-> passage3 | 0.650 | 0.981 | 0.319 | 304.493 |
| 404 <-> passage1 | 0.648 | 0.999 | 0.298 | 35.102 |
| passage1 <-> passage2 | 0.628 | 0.271 | 0.985 | 334.608 |
| 413 <-> passage3 | 0.603 | 0.996 | 0.210 | 90.670 |

The high close ratios confirm that many units still occupy very similar
spatial regions after merge, especially passage-adjacent pairs.

## Visual Review Render

Subset:

- `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000`

Artifacts:

- Renders:
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/manual_passage_review_15000/ours_15000/renders`
- Ground truth:
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/manual_passage_review_15000/ours_15000/gt`
- Coarse-first vs non-coarse contact sheet:
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000/manual_passage_review_15000_coarsefirst_vs_noncoarse_contact_sheet.jpg`

Visual review of the contact sheet shows that the coarse-first run is still not
satisfactory. Some views have slightly more structure than the non-coarse run,
but many selected passage and room-passage views remain heavily blurred or
fogged. The passage regions are still the dominant failure case.

## Metrics Comparison

Same 36-view `manual_passage_review_15000` subset:

| Run | Merged Gaussians | SSIM | PSNR | LPIPS |
|-----|------------------|------|------|-------|
| Non-coarse 15k | 4,991,356 | 0.7784863 | 15.5607643 | 0.4365648 |
| Coarse-first 15k | 4,896,739 | 0.7827049 | 15.8133736 | 0.4396092 |
| Delta | -94,617 | +0.0042186 | +0.2526093 | +0.0030444 |

Coarse-first improves SSIM and PSNR slightly, but LPIPS is slightly worse. The
visual result remains poor enough that the metric improvement should not be
treated as a successful fix.

## Interpretation

The corrected CityGaussian-order run is operationally successful:

- coarse 30000 completed
- unit training loaded the coarse output
- partition, all 10 unit trainings, and merge completed
- expanded bounds leakage is zero
- render and metrics completed on the same 36-view review subset

However, coarse-first alone does not solve the W2 room/passage merged quality
problem. The diagnostics point to high cross-unit close-center overlap rather
than failed bounds clipping. The highest-risk pairs are room-passage and
passage-passage pairs such as `401 <-> passage1`, `412 <-> passage3`,
`passage1 <-> passage2`, and `passage2 <-> passage3`.

## Decision

Do not promote this coarse-first 15000 result to a 30000 unit run unchanged.

The next lower-risk experiment should be a merge/post-merge conflict cleanup or
tighter merge pruning around the high-overlap pairs, followed by rendering the
same `manual_passage_review_15000` subset. This isolates whether redundant
Gaussians at shared spaces are the primary source of the haze before spending
more compute on longer block training.

## Handoff

- Current goal: rerun the manual passage split in true coarse-first order.
- Files touched:
  `config/smoke_test/w2_filtered_manual_passage_no415_coarse_30000.yaml`,
  `config/smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000.yaml`,
  `docs/progress.md`, `docs/experiment_matrix.md`, this report.
- What changed: added self-contained coarse and coarse-first unit configs,
  completed coarse 30000, completed unit 15000, merged, diagnosed, rendered,
  and measured the 36-view review subset.
- What was validated: coarse output exists; unit logs show filtered pretrained
  Gaussians from the coarse output; all cells reached iteration 15000; merged
  PLY exists; bounds diagnostic, render, and metrics completed.
- What remains uncertain or risky: the exact merge cleanup winner policy is not
  selected, and per-block render comparison has not yet isolated which units
  dominate the haze.
- Recommended next owner: Agent 2 for merge/post-merge cleanup, Agent 3 for
  visual interpretation and comparison.
- Recommended next action: run a conservative post-merge conflict cleanup on
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000`, then
  re-render `manual_passage_review_15000`.
- Config path:
  `config/smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000.yaml`
- Exact command: see `Exact Commands`.
- Output directory:
  `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000`
- Artifact or log paths: see `Logs`, `Output`, `Bounds And Overlap Diagnostic`,
  and `Visual Review Render`.
