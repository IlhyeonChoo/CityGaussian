# W2 Balanced Manual-Unit 500-View Comparison

Run completed: 2026-06-05 00:12 UTC

## Goal

Compare the three 30k follow-up pipelines on a larger deterministic render set:

- grid 30k -> grid 30k
- grid 30k -> manual 30k
- manual 30k -> grid 30k

This is a 500-view render/metric comparison on COLMAP training views. It is
not a held-out generalization metric.

## Evaluation Set

Subset path:

`data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/balanced_manual_units_500`

Generated with:

```bash
.venv/bin/python tools/create_balanced_colmap_render_subset.py \
  --source-path data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered \
  --range-file data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
  --output-path data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/balanced_manual_units_500 \
  --units 401 404 409 411 412 413 414 passage1 passage2 passage3 \
  --priority-units passage1 passage2 passage3 401 404 409 411 412 413 414 \
  --per-unit 50
```

Selection rule:

- 10 units, 50 views per unit, 500 total views.
- Views are sampled uniformly across each unit candidate list.
- Passage units have priority when frame ranges overlap room ranges, so room
  subsets avoid the explicitly passage-owned frames.
- `images` and `points3D.ply` are symlinked from the filtered source scene,
  matching the existing `manual_passage_review_15000` custom-test layout.

Candidate counts after passage-priority assignment:

| Unit | Candidates | Selected | Selected frame range |
|---|---:|---:|---|
| 401 | 395 | 50 | 001610-002032 |
| 404 | 379 | 50 | 000971-001353 |
| 409 | 906 | 50 | 007521-008453 |
| 411 | 789 | 50 | 005801-006594 |
| 412 | 568 | 50 | 005132-005699 |
| 413 | 465 | 50 | 004411-005043 |
| 414 | 644 | 50 | 003641-004284 |
| passage1 | 476 | 50 | 000940-004410 |
| passage2 | 512 | 50 | 000000-005124 |
| passage3 | 767 | 50 | 005125-008991 |

## Commands

Render and metrics command:

```bash
bash scripts/evaluate_w2_balanced_manual_units_500.sh
```

The script renders all three models with `render_large.py --custom_test` and
then evaluates them with `tools/streaming_metrics_large.py`. The streaming
metric script computes the same SSIM, PSNR, and LPIPS functions used by
`metrics_large.py`, but avoids loading all 500 render/GT pairs at once.

Log:

`logs/evaluate_w2_balanced_manual_units_500_20260604.log`

Machine-readable summary:

`output/balanced_manual_units_500_comparison_summary.json`

Visual comparison sheet:

`output/balanced_manual_units_500_comparison_contact_sheet.jpg`

## Models

| Label | Config | Output |
|---|---|---|
| grid30k_to_grid30k | `config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_citygs_xz10_30000.yaml` | `output/w2_filtered_manual_passage_no415_best_grid30k_to_citygs_xz10_30000` |
| grid30k_to_manual30k | `config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000.yaml` | `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000` |
| manual30k_to_grid30k | `config/smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000.yaml` | `output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000` |

All metrics below use `balanced_manual_units_500/ours_30000`.

## Overall Metrics

| Model | SSIM ↑ | PSNR ↑ | LPIPS ↓ |
|---|---:|---:|---:|
| grid30k_to_grid30k | 0.858942 | 24.697345 | 0.316196 |
| grid30k_to_manual30k | 0.732234 | 15.218029 | 0.447477 |
| manual30k_to_grid30k | 0.877323 | 25.883212 | 0.287295 |

`manual30k_to_grid30k` is best overall. Against `grid30k_to_grid30k`, it gains
+0.018382 SSIM, +1.185867 PSNR, and -0.028902 LPIPS.

## Room Vs Passage

| Model | Group | SSIM ↑ | PSNR ↑ | LPIPS ↓ |
|---|---|---:|---:|---:|
| grid30k_to_grid30k | rooms | 0.863678 | 25.430899 | 0.291150 |
| grid30k_to_grid30k | passages | 0.847892 | 22.985718 | 0.374637 |
| grid30k_to_manual30k | rooms | 0.713631 | 14.841938 | 0.444752 |
| grid30k_to_manual30k | passages | 0.775642 | 16.095575 | 0.453837 |
| manual30k_to_grid30k | rooms | 0.885124 | 26.864949 | 0.257902 |
| manual30k_to_grid30k | passages | 0.859122 | 23.592492 | 0.355878 |

`manual30k_to_grid30k` improves both room and passage groups over
`grid30k_to_grid30k`, with a larger absolute gain in rooms.

## Per-Unit Metrics

| Unit | Model | SSIM ↑ | PSNR ↑ | LPIPS ↓ |
|---|---|---:|---:|---:|
| 401 | grid30k_to_grid30k | 0.873038 | 25.416559 | 0.294154 |
| 401 | grid30k_to_manual30k | 0.795189 | 18.412565 | 0.362665 |
| 401 | manual30k_to_grid30k | 0.894084 | 26.654589 | 0.261137 |
| 404 | grid30k_to_grid30k | 0.880085 | 25.535414 | 0.303053 |
| 404 | grid30k_to_manual30k | 0.731130 | 13.845959 | 0.467029 |
| 404 | manual30k_to_grid30k | 0.897378 | 26.883992 | 0.273788 |
| 409 | grid30k_to_grid30k | 0.892994 | 27.087659 | 0.251866 |
| 409 | grid30k_to_manual30k | 0.790382 | 17.425903 | 0.357008 |
| 409 | manual30k_to_grid30k | 0.911284 | 28.515470 | 0.221608 |
| 411 | grid30k_to_grid30k | 0.881307 | 25.270615 | 0.270899 |
| 411 | grid30k_to_manual30k | 0.716026 | 14.264207 | 0.448397 |
| 411 | manual30k_to_grid30k | 0.903978 | 26.996489 | 0.236858 |
| 412 | grid30k_to_grid30k | 0.870348 | 25.301426 | 0.271752 |
| 412 | grid30k_to_manual30k | 0.659889 | 13.207860 | 0.480837 |
| 412 | manual30k_to_grid30k | 0.895457 | 26.963684 | 0.231523 |
| 413 | grid30k_to_grid30k | 0.862122 | 25.553042 | 0.292848 |
| 413 | grid30k_to_manual30k | 0.666319 | 12.903512 | 0.480414 |
| 413 | manual30k_to_grid30k | 0.884039 | 26.929783 | 0.261602 |
| 414 | grid30k_to_grid30k | 0.785852 | 23.851581 | 0.353482 |
| 414 | grid30k_to_manual30k | 0.636479 | 13.833557 | 0.516916 |
| 414 | manual30k_to_grid30k | 0.809650 | 25.110637 | 0.318798 |
| passage1 | grid30k_to_grid30k | 0.840645 | 21.637674 | 0.391392 |
| passage1 | grid30k_to_manual30k | 0.795020 | 16.364119 | 0.435524 |
| passage1 | manual30k_to_grid30k | 0.847276 | 22.338318 | 0.381751 |
| passage2 | grid30k_to_grid30k | 0.837636 | 23.449775 | 0.358503 |
| passage2 | grid30k_to_manual30k | 0.709618 | 13.753690 | 0.507931 |
| passage2 | manual30k_to_grid30k | 0.857904 | 24.150939 | 0.324674 |
| passage3 | grid30k_to_grid30k | 0.865394 | 23.869706 | 0.374016 |
| passage3 | grid30k_to_manual30k | 0.822288 | 18.168916 | 0.418054 |
| passage3 | manual30k_to_grid30k | 0.872184 | 24.288217 | 0.361208 |

## Interpretation

- `manual30k_to_grid30k` is the current best among these three models on this
  500-view set. It beats `grid30k_to_grid30k` on every listed unit for SSIM,
  PSNR, and LPIPS.
- `grid30k_to_manual30k` is clearly degraded. The contact sheet shows heavy
  haze, warped clutter, and unstable local structure in many room and passage
  views, consistent with its low PSNR and high LPIPS.
- Passages remain harder than rooms for both grid-output models. The best model
  still has passage LPIPS 0.355878 versus room LPIPS 0.257902.
- Unit `414` remains weak even for the best model: SSIM 0.809650 and LPIPS
  0.318798. This is the first unit to inspect if further localized cleanup is
  needed.

## Handoff

- Current goal: compare the three 30k follow-up models on a balanced 500-view
  subset.
- Files touched:
  - `tools/create_balanced_colmap_render_subset.py`
  - `scripts/evaluate_w2_balanced_manual_units_500.sh`
  - `docs/reports/20260604_w2_balanced_manual_units_500_compare.md`
- What changed:
  - Added a deterministic COLMAP custom-test subset generator.
  - Added a reproducible three-model render/metric script.
  - Rendered and evaluated all three models on `balanced_manual_units_500`.
- What was validated:
  - 500 selected views: 50 per unit across 10 units.
  - 500 render and 500 GT images exist for all three models.
  - Streaming SSIM/PSNR/LPIPS completed for all three models.
- What remains uncertain or risky:
  - Metrics are on training views, not held-out views.
  - The subset uses passage-priority assignment, which is appropriate for this
    comparison but should be stated when comparing against older subsets.
- Recommended next owner: Agent 3 for interpretation and follow-up planning,
  Agent 2 if training/merge behavior needs to change next.
- Recommended next action:
  - Use `manual30k_to_grid30k` as the best current candidate.
  - Inspect `414` and passage views visually before deciding whether another
    localized cleanup or partition refinement is worth running.
