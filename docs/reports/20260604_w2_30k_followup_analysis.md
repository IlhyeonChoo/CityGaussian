# 2026-06-04 W2 30k Followup Analysis

## Current Goal

Analyze the completed W2 30k follow-up sequence:

1. best xz10 grid 15k merged result -> xz10 grid 30k
2. reused coarse 30k -> manual-unit 30k
3. manual-unit 30k merged result -> xz10 grid 30k

The direct question is whether the best 15k xz10 path improved at 30k, and
whether the higher-quality manual-unit 30k merged model is useful as a common
pretrain for xz10 grid training.

## Completion Status

The sequence completed successfully.

- Sequence log:
  `logs/20260603_w2_30k_followup_sequence.log`
- Completion time:
  `2026-06-04T02:14:36+0000`
- No `Traceback`, `OutOfMemory`, `CUDA out of memory`, `Training failed`,
  or skipped-merge failure pattern was found in the three run logs.
- No related training, rendering, metrics, merge, or watcher process remained
  after completion.
- GPU compute process list was empty after completion.

## Outputs

| Stage | Config | Output |
|-------|--------|--------|
| Best grid15k -> grid30k | `config/smoke_test/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000.yaml` | `output/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000` |
| Coarse30k -> manual-unit30k | `config/smoke_test/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000.yaml` | `output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000` |
| Manual-unit30k -> grid30k | `config/smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000.yaml` | `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000` |

Merged PLYs:

| Run | Merged PLY | Size |
|-----|------------|------|
| Best grid15k -> grid30k | `output/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000/point_cloud/iteration_30000/point_cloud.ply` | `492M` |
| Manual-unit30k | `output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000/point_cloud/iteration_30000/point_cloud.ply` | `1.4G` |
| Manual-unit30k -> grid30k | `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000/point_cloud/iteration_30000/point_cloud.ply` | `487M` |

## Metrics

All metrics below use the same 36-view `manual_passage_review_15000` subset.
This subset is rendered as `Train cameras: 36, Test cameras: 0`, so these
numbers are a controlled visual-review signal rather than held-out
generalization metrics.

| Run | Gaussians | SSIM | PSNR | LPIPS | Avg FPS | Max Mem |
|-----|----------:|-----:|-----:|------:|--------:|--------:|
| Manual-unit 15k | 4,991,356 | 0.7784863 | 15.5607643 | 0.4365648 | 61.64 | 3643M |
| Manual-unit coarse-first 15k | 4,896,739 | 0.7827049 | 15.8133736 | 0.4396092 | 54.36 | 3996M |
| Best grid 15k | 1,895,774 | 0.8428190 | 21.7424717 | 0.3811370 | 93.96 | 1919M |
| Best grid15k -> grid30k | 2,076,198 | 0.8566074 | 23.3606491 | 0.3640910 | 89.61 | 2079M |
| Manual-unit30k | 5,980,856 | 0.7765912 | 15.3306208 | 0.4488924 | 49.39 | 4616M |
| Manual-unit30k -> grid30k | 2,057,987 | 0.8589663 | 23.4472618 | 0.3599922 | 94.47 | 1981M |

Compared with best grid 15k:

| Run | Delta Gaussians | Delta SSIM | Delta PSNR | Delta LPIPS |
|-----|----------------:|-----------:|-----------:|------------:|
| Best grid15k -> grid30k | +180,424 | +0.0137884 | +1.6181774 | -0.0170460 |
| Manual-unit30k -> grid30k | +162,213 | +0.0161473 | +1.7047901 | -0.0211448 |

Compared with best grid15k -> grid30k, the manual-unit30k -> grid30k run is
slightly better on this subset:

- `SSIM +0.0023589`
- `PSNR +0.0866127`
- `LPIPS -0.0040988`
- `-18,211` Gaussians
- higher average FPS and lower max memory

## Cell Counts

### Best grid15k -> grid30k

| Cell | Points |
|------|-------:|
| cell0 | 0 |
| cell1 | 618,056 |
| cell2 | 300,880 |
| cell3 | 143,060 |
| cell4 | 0 |
| cell5 | 0 |
| cell6 | 72,449 |
| cell7 | 628,876 |
| cell8 | 312,877 |
| cell9 | 0 |
| **Total** | **2,076,198** |

### Manual-unit30k

| Cell | Unit | Points |
|------|------|-------:|
| cell0 | 401 | 601,144 |
| cell1 | 404 | 540,056 |
| cell2 | 409 | 635,609 |
| cell3 | 411 | 755,682 |
| cell4 | 412 | 899,879 |
| cell5 | 413 | 646,613 |
| cell6 | 414 | 662,124 |
| cell7 | passage1 | 293,548 |
| cell8 | passage2 | 705,234 |
| cell9 | passage3 | 240,967 |
| **Total** | | **5,980,856** |

### Manual-unit30k -> grid30k

| Cell | Points |
|------|-------:|
| cell0 | 0 |
| cell1 | 615,643 |
| cell2 | 299,032 |
| cell3 | 124,803 |
| cell4 | 0 |
| cell5 | 0 |
| cell6 | 64,331 |
| cell7 | 619,150 |
| cell8 | 335,028 |
| cell9 | 0 |
| **Total** | **2,057,987** |

## Empty Grid Cells

Both grid30k runs still rely on explicit empty cells for strict merge:

- empty grid cells: `0`, `4`, `5`, `9`

For the manual-unit30k -> grid30k pretrain, the recorded grid bounds-filtered
counts were:

```text
[0, 1277645, 1461710, 257271, 0, 0, 279227, 2847246, 2022848, 0]
```

Diagnostic JSON:

- `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000/diagnostics/grid_pretrain_counts_iter30000.json`

This is operationally consistent with the 15k grid followup, but it remains a
layout risk. The xz10 AABB/grid has dead or unused cells under the current
contracted bounds split.

## Visual Review

Contact sheets:

- Selected larger frames:
  `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000/manual_passage_review_15000_30k_followups_selected_contact_sheet.jpg`
- Full 36-view sheet:
  `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000/manual_passage_review_15000_30k_followups_contact_sheet.jpg`

Visual findings:

- Manual-unit30k is not usable as a direct render model. It is frequently foggy,
  smeared, and structurally unstable in both classroom and corridor views.
- Both grid30k runs are much more stable than all manual-unit direct renders.
- Manual-unit30k -> grid30k is the current best aggregate result.
- Best grid15k -> grid30k is still competitive and wins several individual
  frames.
- Remaining problem frames still include corridor/door boundary and reflective
  dark regions. Notable examples: `00004`, `00005`, `00014`, `00031`, `00035`.

Simple per-frame PNG PSNR check:

- Winner counts across 36 frames:
  - `manual-unit30k -> grid30k`: 20
  - `best grid15k -> grid30k`: 12
  - `best grid15k`: 3
  - `manual-unit30k`: 1
- Frames where best grid15k -> grid30k clearly beats manual-unit30k -> grid30k:
  `00031`, `00014`, `00032`, `00015`, `00022`, `00035`.
- Frames where manual-unit30k -> grid30k clearly improves over best grid15k ->
  grid30k include `00023`, `00004`, `00028`, `00002`, `00030`.

## Interpretation

The 30k xz10 grid direction is validated on the 36-view review subset.

The best current render candidate is:

- `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`

The best current reusable manual-unit merged pretrain is:

- `output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000/point_cloud/iteration_30000/point_cloud.ply`

However, the manual-unit30k merged model should not be used directly for
rendering. It is useful as a dense pretrain that becomes good after the xz10
grid filter/retraining step.

The core failure remains the manual-unit partition's direct merged render. More
iterations made the direct manual-unit result worse on the review subset:

- manual-unit coarse-first 15k: `SSIM 0.7827`, `PSNR 15.8134`,
  `LPIPS 0.4396`
- manual-unit30k: `SSIM 0.7766`, `PSNR 15.3306`, `LPIPS 0.4489`

This supports the earlier hypothesis that direct manual-unit merging causes
cross-block Gaussian interference. The grid repartition step reduces the
effective Gaussian count by roughly two thirds and recovers quality.

Another warning remains unchanged from the earlier manual-unit experiments:
the manual-unit partition reports `679 cameras did not match any unit` out of
`6580` cameras. This coverage gap should be treated as a manual-unit
assignment risk, and may contribute to the poor direct manual-unit render.

## Recommended Next Step

Do not spend more runs on direct manual-unit rendering as the final output.

Recommended next analysis path:

1. Use `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`
   as the current best model.
2. Render broader review subsets for rooms and corridor separately, not only
   the 36-view `manual_passage_review_15000` subset.
3. If broader visual review agrees, treat xz10 grid post-training as the main
   path.
4. Investigate a better grid/AABB layout to remove empty cells `0`, `4`, `5`,
   and `9`, or explicitly document this as the intended six-active-cell layout.

## Handoff

- Current goal: analyze completed W2 30k followup sequence.
- Files touched:
  this report, `docs/progress.md`, `docs/experiment_matrix.md`.
- What changed:
  recorded 30k metrics, cell counts, visual review artifacts, and conclusion.
- What was validated:
  logs had no failure patterns, all three runs produced merged PLYs,
  render/metrics completed, GPU/process state was clean after completion.
- What remains uncertain or risky:
  only the 36-view train-camera manual passage review subset was evaluated,
  the xz10 grid still has empty cells `0`, `4`, `5`, `9`, and the manual-unit
  partition still has `679/6580` cameras unmatched.
- Recommended next owner:
  Agent 3 for expanded visual/metric analysis; Agent 1 if changing grid/AABB
  layout; Agent 2 if launching the next training run.
- Recommended next action:
  render broader room-specific and passage-specific review subsets for
  `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`.
