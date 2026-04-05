# Agent 2 Guide

## Title

Block Training And Overlap Optimization

## Mission

Agent 2 owns how already-defined blocks are trained, resumed, blended, merged,
and optimized to reduce boundary artifacts. This agent operates after partition
definitions already exist.

## Owns

- Block-wise training behavior after partitioning is fixed
- Overlap-aware optimization and weighting during learning
- Freeze scheduling and staged optimization
- Coarse-to-fine or similar training schedules
- Checkpoint flow, resume behavior, and per-block training control
- Merge-time blending, duplicate pruning, and optimization heuristics
- Config fields and scripts that control training or merge behavior

## Does Not Own

- Redefining block geometry, overlap widths, or camera assignment rules
- Report writing and experiment interpretation as the main deliverable
- Repository-wide workflow guidance or branch strategy

## Typical Files

- `train_large.py`
- `train_large_overlap.py`
- `merge.py`
- `merge_overlap.py`
- `render_large.py`, `render_large_lod.py` (rendering after merge)
- Optimization parameters in `arguments/__init__.py`
- Training and merge helpers under `utils/`
- Scripts or configs that launch training or merge experiments

## Typical Inputs

- Existing partition metadata
- A baseline or experimental training config
- A seam-reduction hypothesis tied to optimization behavior
- Existing checkpoints or run artifacts

## Typical Outputs

- Updated training or merge code
- New opt-in config flags for training behavior
- Smoke-test logs or subset-run artifacts
- A short note describing what behavior changed and how it was validated

## Good Tasks For Agent 2

- "Add overlap-aware loss weighting during block training."
- "Freeze shared boundary Gaussians after the coarse stage."
- "Improve merge blending near block seams."
- "Make coarse-to-fine training resumable."
- "Prune duplicate Gaussians after overlap-aware merge."

## Tasks To Hand Off

Hand off to Agent 1 when:

- The required fix changes block boundaries, overlap geometry, or assignment
  rules.

Hand off to Agent 3 when:

- The main task is to compare run outcomes, summarize metrics, or propose the
  next experiment.

Hand off to Agent 4 when:

- The task affects shared workflow, ownership, or repo-wide organization.

## Working Procedure

1. Confirm partition definitions already provide the needed structure.
2. Inspect training, merge, checkpoint, and config entrypoints.
3. Preserve baseline behavior by gating new logic behind config or wrapper
   entrypoints.
4. Use the smallest meaningful run to validate behavior before any large job.
5. Record exact commands, output paths, checkpoints, and stop conditions.

## Validation Expectations

Use the lightest validation that still proves the training or merge logic works.

- Run a smoke test or subset experiment first.
- Verify checkpoints, logs, and resume points are produced correctly.
- Confirm merge output is generated when merge logic changes.
- Record any metric deltas or failure traces relevant to the new behavior.

Definition of done for Agent 2 work:

- The new behavior is opt-in and baseline-compatible.
- The training or merge path runs through at least a smoke validation, or the
  blocker is documented precisely.
- The run artifact includes config path, command, output directory, and primary
  evidence.

## Common Risks

- Quietly depending on partition metadata that Agent 1 has not standardized
- Running expensive jobs before smoke validation
- Changing merge behavior without documenting downstream evaluation impact
- Breaking baseline training entrypoints while adding experimental logic

## Handoff Checklist

- Current goal
- Files touched
- Config path used
- Exact train or merge command
- Output directory and checkpoint status
- What was validated
- Main failure mode or metric delta
- Recommended next owner

## Example Handoff

Current goal: add overlap-aware freeze scheduling after the coarse stage.

Files touched:

- `train_large_overlap.py`
- `arguments/__init__.py`
- `config/<experiment>.yaml`

What changed:

- Added a configurable iteration threshold for freezing overlap-region updates.

What was validated:

- Completed a subset smoke run.
- Confirmed checkpoints and logs contain the new schedule.

What remains uncertain:

- Merge quality and full-scene metrics have not been checked yet.

Recommended next owner:

- Agent 3 for result interpretation after evaluation artifacts are available.
