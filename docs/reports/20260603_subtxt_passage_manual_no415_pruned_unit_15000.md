# 2026-06-03 Subtxt Manual Passage No415 Pruned Unit 15000

## Current Goal

Run the manual passage split for 15000 iterations so the merged result can be
checked visually instead of relying on 1000-iteration smoke behavior.

## Config

- Config:
  `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000.yaml`
- Range file:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt`
- Source scene:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Point source:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416`

## Exact Command

```bash
CONFIG=smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000 \
RANGE_FILE=data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=5 \
PYTHON_BIN=.venv/bin/python \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
```

Log:

- `logs/20260603_w2_manual_passage_15000.log`

## Output

- Output directory:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000`
- Merged PLY:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000/point_cloud/iteration_15000/point_cloud.ply`
- Merged PLY size: `1.2G`
- Merged Gaussian count: `4,991,356`

## Block Results

All 10 unit blocks trained to iteration 15000 and merged successfully.

| Cell | Unit | Merged Points |
|------|------|---------------|
| cell0 | 401 | 480,927 |
| cell1 | 404 | 448,084 |
| cell2 | 409 | 555,730 |
| cell3 | 411 | 587,607 |
| cell4 | 412 | 698,743 |
| cell5 | 413 | 552,381 |
| cell6 | 414 | 628,670 |
| cell7 | passage1 | 245,379 |
| cell8 | passage2 | 580,853 |
| cell9 | passage3 | 212,982 |

No `Traceback`, `OutOfMemory`, `ValueError`, or training failure was found in
the run log.

Train-time unit bounds pruning removed `2,288` Gaussians across `613` events.
This is tiny relative to the final merged count and confirms the bounds guard
was active without dominating the run.

Pruned counts by block:

| Block | Pruned |
|-------|--------|
| 0 | 283 |
| 1 | 113 |
| 2 | 193 |
| 3 | 261 |
| 4 | 359 |
| 5 | 386 |
| 6 | 228 |
| 7 | 43 |
| 8 | 217 |
| 9 | 205 |

## Bounds And Overlap Diagnostic

Command:

```bash
.venv/bin/python tools/analyze_unit_gaussian_overlap.py \
  --config config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000.yaml \
  --output output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000 \
  --iteration 15000 \
  --thresholds 0.05 0.1 0.2 \
  --sample-per-unit 200000 \
  --write-json output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000/diagnostics/unit_gaussian_overlap_iter15000_sample200k.json
```

Result:

- Expanded bounds leakage: `0` for every unit.
- Cell point total equals merged point count: `4,991,356`.
- Passage Gaussians remain larger than classroom Gaussians by scale statistics,
  especially `passage3`.

| Unit | Points | Inside Raw Bounds | Outside Expanded Bounds | P95 Max Scale |
|------|--------|-------------------|-------------------------|---------------|
| 401 | 480,927 | 0.974 | 0 | 0.0281 |
| 404 | 448,084 | 0.978 | 0 | 0.0253 |
| 409 | 555,730 | 0.968 | 0 | 0.0316 |
| 411 | 587,607 | 0.973 | 0 | 0.0338 |
| 412 | 698,743 | 0.970 | 0 | 0.0309 |
| 413 | 552,381 | 0.970 | 0 | 0.0319 |
| 414 | 628,670 | 0.930 | 0 | 0.0252 |
| passage1 | 245,379 | 0.955 | 0 | 0.0528 |
| passage2 | 580,853 | 0.992 | 0 | 0.0406 |
| passage3 | 212,982 | 0.981 | 0 | 0.0999 |

Top close-center pairs at threshold `0.2`:

| Pair | Mean Close Ratio |
|------|------------------|
| 401 <-> passage1 | 0.643 |
| 404 <-> passage1 | 0.513 |
| 414 <-> passage1 | 0.388 |
| passage2 <-> passage3 | 0.379 |
| 411 <-> 412 | 0.355 |
| passage1 <-> passage2 | 0.331 |
| 412 <-> 413 | 0.319 |
| 411 <-> passage3 | 0.313 |
| 412 <-> passage3 | 0.292 |
| 409 <-> passage3 | 0.280 |

## Visual Review Render

Created a 36-view custom test subset focused on passage and room-passage
transition frames:

- Subset:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000`
- Frame mapping:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000/selected_frames.json`

Render command:

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python render_large.py \
  --config config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000.yaml \
  --iteration 15000 \
  --custom_test data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000
```

Render artifacts:

- Renders:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000/manual_passage_review_15000/ours_15000/renders`
- GT:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000/manual_passage_review_15000/ours_15000/gt`
- Contact sheet:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000/manual_passage_review_15000/ours_15000/manual_passage_review_15000_contact_sheet.jpg`

Render cost:

- Average FPS: `61.64`
- Max render memory: `3643 MB`
- Number of Gaussians: `4,991,356`

Subset metrics:

- SSIM: `0.7784863`
- PSNR: `15.5607643`
- LPIPS: `0.4365648`

Worst PSNR frames:

| Render | Frame | PSNR | SSIM | LPIPS |
|--------|-------|------|------|-------|
| 00002.png | frame_000240 | 7.566 | 0.648 | 0.530 |
| 00004.png | frame_000480 | 9.667 | 0.661 | 0.512 |
| 00035.png | frame_008991 | 11.119 | 0.689 | 0.526 |
| 00000.png | frame_000000 | 11.679 | 0.657 | 0.496 |
| 00014.png | frame_004285 | 12.304 | 0.734 | 0.481 |

## Interpretation

The 15000-iteration run is operationally successful, but the merged visual
result is not satisfactory.

The result supports two points:

- The current single-owner bounds filtering path is functioning: no expanded
  bounds leakage remains in saved/merged PLYs.
- The remaining quality problem is not simply a failed bounds filter. The
  merged model still shows heavy blur/fog in selected passage and room-passage
  views, consistent with cross-unit Gaussian interference and passage quality
  weakness.

Visual review shows strong haze or blur in many selected frames. This is most
visible in passage2 early frames (`frame_000000`, `frame_000240`,
`frame_000480`), passage1/room-passage transition frames, and the passage3 end
frame (`frame_008991`).

## Decision

Do not promote this 15000 result directly to a 30000 run as-is.

Recommended next step is a post-merge cleanup or selective render test before
more training:

- Use the 15000 merged output as the testbed.
- Try a conservative post-merge duplicate/conflict cleanup around high-overlap
  pairs.
- Re-render the same `manual_passage_review_15000` subset for direct visual and
  metric comparison.

Overlap-aware training should remain deferred until this single-owner merged
failure mode is better isolated.

## Handoff

- Current goal: run 15000 iterations and inspect the result visually.
- Files touched:
  `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000.yaml`,
  `docs/progress.md`, this report.
- What changed: added a 15000 config, generated a 36-view review subset, ran
  training/merge/render/metrics, and recorded results.
- What was validated: all 10 blocks trained and merged; bounds diagnostic;
  selected render and metrics.
- What remains uncertain or risky: exact cause of haze needs post-merge cleanup
  experiments or per-block render comparison.
- Recommended next owner: Agent 2 for merge/post-merge cleanup, Agent 3 for
  visual interpretation.
- Recommended next action: run a post-merge cleanup experiment on the 15000 PLY
  and re-render the same 36-view subset.
- Config path:
  `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000.yaml`
- Exact command: see `Exact Command`.
- Output directory:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000`
- Artifact or log paths: see `Output`, `Bounds And Overlap Diagnostic`,
  `Visual Review Render`.
