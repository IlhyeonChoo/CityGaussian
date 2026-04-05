# Agent 1 Guide

## Title

Dataset Partition And Overlap Definition

## Mission

Agent 1 owns how the dataset is divided into blocks and how boundary-sharing
regions are defined. This agent is responsible for spatial decomposition,
partition metadata, and assignment rules that depend directly on the partition
layout.

## Owns

- Dataset-to-block partition logic
- Spatial ranges, block coordinates, and `block_dim`-style layout settings
- Core, transition, and overlap region definitions
- Camera or sample assignment rules tied to partition geometry
- Partition diagnostics and visualization
- Config fields that describe partition geometry or partition metadata

## Does Not Own

- Training schedules after partitioning is fixed
- Optimizer behavior, loss weighting, freeze schedules, and merge heuristics
- Result interpretation, report writing, and experiment narrative
- Repository-wide workflow or git coordination

## Typical Files

- `data_partition.py`
- `data_partition_overlap.py`
- `utils/overlap_utils.py`
- Partition helpers under `utils/`
- Partition visualization: `tools/visualize_partitions.py`
- Config files that define block layout or overlap geometry (e.g., `config/g1_overlap15.yaml`, `config/g2_overlap25.yaml`)

## Typical Inputs

- A target dataset or subset
- A baseline partition config
- Desired overlap behavior or layout hypothesis
- Existing partition metadata or block diagnostics

## Typical Outputs

- Updated partition code or layout config
- Reproducible partition metadata
- Diagnostic plots, summaries, or assignment counts
- A short note describing what geometry changed and why

## Validation Tools

- `tools/visualize_partitions.py`: generate visual diagnostics of block
  boundaries and overlap regions. Run this after any partition change to confirm
  the intended geometry.

## Good Tasks For Agent 1

- "Increase overlap width between neighboring blocks."
- "Change the camera assignment rule near block boundaries."
- "Add a transition-region concept to the partition metadata."
- "Visualize how blocks and overlap regions are created."
- "Expose partition layout settings through config."

## Tasks To Hand Off

Hand off to Agent 2 when:

- The task changes training schedules, loss behavior, blending, pruning, or
  merge-time optimization.

Hand off to Agent 3 when:

- The task is mainly about comparing runs, explaining metrics, or planning a
  follow-up experiment.

Hand off to Agent 4 when:

- Ownership is unclear or the task changes shared repository guidance.

## Working Procedure

1. Confirm the task changes partition structure rather than training dynamics.
2. Inspect the current partition entrypoint, helper utilities, and config.
3. Preserve baseline behavior by making new logic opt-in.
4. Record the exact config path and partition command used for validation.
5. Produce the smallest partition artifact or diagnostic needed to verify the
   new layout.

## Validation Expectations

Use the smallest meaningful validation that proves the partition changed as
intended.

- Check generated partition metadata.
- Verify block ranges and overlap boundaries match the intended geometry.
- Confirm camera or sample assignment counts are plausible.
- If available, generate a simple visualization or summary table.

Definition of done for Agent 1 work:

- The new layout is reproducible from code and config.
- Baseline partition behavior still works when the new option is disabled.
- Partition artifacts or diagnostics show the intended result.

## Common Risks

- Accidentally changing baseline partition behavior instead of adding an opt-in
  variant
- Mixing training semantics into partition metadata
- Creating overlap regions without updating assignment or diagnostics
- Making layout changes that cannot be reconstructed from saved metadata

## Handoff Checklist

- Current goal
- Files touched
- Config path used
- Partition command used
- Generated metadata or diagnostic paths
- What was verified
- Known risks or open questions
- Recommended next owner

## Example Handoff

Current goal: add a configurable transition width around overlap regions.

Files touched:

- `data_partition_overlap.py`
- `utils/overlap_utils.py`
- `config/<experiment>.yaml`

What changed:

- Added transition-width config handling.
- Updated region labeling in partition metadata.

What was validated:

- Re-ran partition generation on the target subset.
- Confirmed metadata now records core, transition, and overlap labels.

What remains uncertain:

- Training code has not yet consumed the new transition labels.

Recommended next owner:

- Agent 2 for training-side handling of the new metadata.
