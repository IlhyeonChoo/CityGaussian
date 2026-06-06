# 2026-06-03 Overlap Deferred For W2 Room/Passage

## Decision

For the current W2 room/passage experiments, overlap-aware partitioning,
training, and merge are deferred.

The existing overlap implementation remains in the repository, but new W2
room/passage runs should not use it unless the experiment is explicitly
reopened as a separate overlap comparison.

## Scope

Deferred overlap path:

- `data_partition_overlap.py`
- `train_large_overlap.py`
- `merge_overlap.py`
- `config/g1_overlap15*.yaml`
- `config/g2_overlap25*.yaml`

Current active W2 path:

- `partition_mode: colmap_unit`
- single-owner camera assignment from room/passage range files
- point/core-point cleanup before training
- train-time unit bounds pruning
- merge-time unit bounds filtering

`unit_aabb_margin` is bounds padding around each unit. It is not overlap-aware
training because cameras are still assigned to a single final unit.

## Rationale

The current W2 failure modes appear dominated by passage camera assignment,
outlier or weakly supported poses, broad Gaussian growth outside the intended
unit, and duplicate or conflicting Gaussians after merge.

Adding overlap-aware training now would mix another variable into the same
failure surface. The immediate priority is to establish a stable single-owner
room/passage baseline, especially for the passage units, before revisiting
overlap.

## Current Baseline Direction

- Keep each classroom and passage segment as a single-owner unit.
- Prefer the filtered source scene over the unfiltered merged scene when camera
  or point cleanup is required.
- Keep passage splits explicit in a range file rather than inferred from the
  merged COLMAP image order.
- Continue using core point cleanup so core points are not shared across final
  units.
- Continue train-time and merge-time bounds filtering to reduce Gaussians that
  spread far outside the intended unit.

## Resume Criteria

Only resume overlap-aware experiments after the single-owner W2 baseline has a
usable visual result for classrooms and passages.

If resumed, overlap should be treated as a new comparison branch with separate
config names, output directories, reports, and render comparisons. It should
not replace the current `colmap_unit` baseline silently.

## Handoff

- Current goal: document that overlap is deferred for W2 room/passage work.
- Files touched: this report, `docs/progress.md`, `docs/experiment_matrix.md`.
- What changed: W2 active path and deferred overlap path are now separated in
  documentation.
- What was validated: documentation-only change; no training or rendering run.
- What remains uncertain or risky: post-merge duplicate handling and passage
  visual quality still need render inspection and follow-up experiments.
- Recommended next owner: Agent 4 for experiment coordination, then Agent 2 for
  training/merge changes if post-merge cleanup is pursued.
- Recommended next action: run or inspect renders for the latest
  `subtxt_passage_manual_no415_pruned_units` output before starting a 30k run.
- Config path: N/A for this decision note.
- Exact command: N/A.
- Output directory: N/A.
- Artifact or log paths: `docs/reports/20260603_overlap_deferred_for_w2_room_passage.md`.
