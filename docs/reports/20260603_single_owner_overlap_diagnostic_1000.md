# 2026-06-03 Single-Owner Overlap Diagnostic 1000

## Current Goal

Validate the recommended single-owner path before moving to longer W2
room/passage runs.

This checks whether the current bounds filtering is working and whether merged
unit outputs still contain heavy cross-unit Gaussian center overlap.

## Tool

Added:

- `tools/analyze_unit_gaussian_overlap.py`

The tool reads trained per-cell PLY files, unit partition metadata, and the
merged PLY. It reports:

- per-unit point counts
- raw unit-bounds containment ratio
- expanded bounds leakage count
- Gaussian scale statistics
- cross-unit nearest-center overlap ratios at configurable world-space
  thresholds

## Commands

Manual passage split:

```bash
.venv/bin/python tools/analyze_unit_gaussian_overlap.py \
  --config config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000.yaml \
  --output output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000 \
  --iteration 1000 \
  --thresholds 0.05 0.1 0.2 \
  --sample-per-unit 0 \
  --write-json output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000/diagnostics/unit_gaussian_overlap_iter1000_full.json
```

Previous subtxt split:

```bash
.venv/bin/python tools/analyze_unit_gaussian_overlap.py \
  --config config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000.yaml \
  --output output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000 \
  --iteration 1000 \
  --thresholds 0.05 0.1 0.2 \
  --sample-per-unit 0 \
  --write-json output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000/diagnostics/unit_gaussian_overlap_iter1000_full.json
```

## Bounds Result

Manual passage split, 1000 iterations:

| Unit | Points | Inside Raw Bounds | Outside Expanded Bounds | P95 Max Scale |
|------|--------|-------------------|-------------------------|---------------|
| 401 | 73,128 | 0.976 | 0 | 0.0368 |
| 404 | 73,609 | 0.978 | 0 | 0.0380 |
| 409 | 145,222 | 0.975 | 0 | 0.0415 |
| 411 | 147,756 | 0.978 | 0 | 0.0411 |
| 412 | 135,962 | 0.977 | 0 | 0.0446 |
| 413 | 104,061 | 0.976 | 0 | 0.0477 |
| 414 | 216,178 | 0.971 | 0 | 0.0257 |
| passage1 | 64,902 | 0.982 | 0 | 0.1028 |
| passage2 | 120,985 | 0.990 | 0 | 0.0818 |
| passage3 | 117,269 | 0.987 | 0 | 0.0960 |

Interpretation: train/save/merge bounds filtering is working for this run. No
cell PLY contains Gaussians outside the expanded unit bounds. Passage Gaussians
are still larger than classroom Gaussians by scale statistics, so passage units
remain the higher-risk merge contributors.

## Cross-Unit Close Center Result

Aggregate mean close-center ratios across checked unit pairs:

| Split | Threshold | Max Pair Mean | All Pair Mean | Passage-Any Mean | Passage-Passage Mean |
|-------|-----------|---------------|---------------|------------------|----------------------|
| previous subtxt | 0.05 | 0.485 | 0.056 | 0.079 | 0.237 |
| manual passage | 0.05 | 0.194 | 0.048 | 0.068 | 0.136 |
| previous subtxt | 0.10 | 0.637 | 0.103 | 0.140 | 0.376 |
| manual passage | 0.10 | 0.366 | 0.095 | 0.132 | 0.250 |
| previous subtxt | 0.20 | 0.750 | 0.182 | 0.229 | 0.525 |
| manual passage | 0.20 | 0.640 | 0.177 | 0.230 | 0.418 |

Largest manual split pairs at threshold `0.2`:

| Pair | Mean Close Ratio | Left | Right |
|------|------------------|------|-------|
| 404 <-> passage1 | 0.640 | 0.769 | 0.512 |
| 414 <-> passage1 | 0.625 | 0.655 | 0.596 |
| 401 <-> passage1 | 0.500 | 0.758 | 0.242 |
| passage2 <-> passage3 | 0.437 | 0.584 | 0.289 |
| passage1 <-> passage3 | 0.416 | 0.455 | 0.378 |
| passage1 <-> passage2 | 0.402 | 0.317 | 0.487 |

## Comparison

The manual passage split improves the worst passage-passage overlap compared
with the previous subtxt split:

- `passage1 <-> passage2` at threshold `0.05`: `0.485 -> 0.143`
- `passage1 <-> passage2` at threshold `0.10`: `0.637 -> 0.251`
- `passage1 <-> passage2` at threshold `0.20`: `0.750 -> 0.402`

Some room-passage pairs become more prominent in the manual split, especially
`404/414/401 <-> passage1`. This is not automatically wrong because these units
are spatially adjacent, but it is exactly where render inspection and possible
post-merge cleanup should focus.

## Decision

The recommended single-owner path is internally consistent:

- single-owner partitioning is active
- bounds filtering is active
- expanded bounds leakage is zero for the 1000-iteration manual passage result
- manual passage split reduces the worst passage-passage overlap

However, the merged result still has substantial cross-unit center overlap in
passage-adjacent regions. The next low-risk step is visual render inspection
plus a separate post-merge cleanup experiment. Do not re-enable overlap-aware
training yet.

## Artifacts

- Manual diagnostic JSON:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000/diagnostics/unit_gaussian_overlap_iter1000_full.json`
- Previous subtxt diagnostic JSON:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000/diagnostics/unit_gaussian_overlap_iter1000_full.json`

## Handoff

- Current goal: verify the recommended single-owner path.
- Files touched: `tools/analyze_unit_gaussian_overlap.py`,
  `docs/progress.md`, this report.
- What changed: added a reusable read-only Gaussian overlap diagnostic tool and
  recorded the 1000-iteration comparison.
- What was validated: Python syntax check and two full-point diagnostics.
- What remains uncertain or risky: visual quality has not been inspected in
  rendered views; cleanup threshold and winner policy are not defined yet.
- Recommended next owner: Agent 2 for post-merge cleanup if pursued, Agent 3 for
  render-based interpretation.
- Recommended next action: render or inspect selected views around
  `404/414/401 <-> passage1` and passage-passage transition areas before
  launching 30k.
- Config path:
  `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000.yaml`
- Exact command: see `Commands`.
- Output directory:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000`
- Artifact or log paths: see `Artifacts`.
