# AGENTS.md

## Project Scope

- Project: CityGaussian V1 boundary artifact mitigation research
- Objective: reduce seams, color mismatch, and density gaps across block boundaries without relying on global alignment
- Baseline: preserve the original CityGaussian V1 pipeline unless an experiment explicitly opts into new behavior
- Strategy A: overlapping block partition with explicit boundary-sharing regions
- Strategy B: hierarchical coarse-to-fine block training
- Strategy A+B: combined overlap-aware partitioning with coarse-to-fine training

## Domain Glossary

- Block: one spatial cell produced by the CityGaussian partitioning pipeline and trained independently before merge
- Core / Transition / Overlap region: partition subregions used to separate stable interior content from boundary-sharing content
- Partition metadata: block ranges, camera assignment results, and any auxiliary data required to reproduce a partition layout
- Coarse stage: an early low-budget training stage used to initialize later optimization
- Fine stage: the main training stage that continues from baseline or coarse outputs
- Boundary-view metrics: evaluation metrics computed on views where block boundaries are actually visible
- Run artifact: the recorded config path, command, output directory, checkpoints, logs, and main metrics for one run
- Baseline vs variant: the comparison contract between unmodified CityGaussian behavior and any experimental change

## Repository Map

- Baseline partition, training, and merge entrypoints: `data_partition.py`, `train_large.py`, `merge.py`
- Overlap-aware variants: `data_partition_overlap.py`, `train_large_overlap.py`, `merge_overlap.py`, `utils/overlap_utils.py`
- Rendering entrypoints: `render_large.py`, `render_large_lod.py`, `viewer.py`
- Evaluation entrypoint: `metrics_large.py`
- Data conversion utilities: `convert.py`, `convert_cam.py`
- Boundary analysis and visualization tools (`tools/`):
  - Partition visualization: `tools/visualize_partitions.py`
  - Boundary-view selection and metrics: `tools/select_boundary_views.py`, `tools/boundary_crop.py`, `tools/boundary_lpips.py`, `tools/projected_boundary_lpips.py`, `tools/projected_boundary_utils.py`, `tools/filtered_metrics.py`
  - Result visualization: `tools/error_map.py`, `tools/plot_results.py`
  - Data preparation: `tools/prepare_matrixcity_small_aerial_v1.py`, `tools/copy_images.py`, `tools/transform_*.py`
- Argument definitions: `arguments/__init__.py` (single module containing all parameter groups)
- Experiment configs and launch scripts: `config/`, `scripts/`
- Planning and status documents: `Todo/README.md`, `docs/progress.md`, `docs/reports/`, `docs/cleanup_candidates.md`, `LOCAL_SETUP_NOTES.md`
- Per-agent working guides: `.codex/agents/`
- Untracked runtime artifacts: `data/`, `output/`
- Working source-of-truth for current work:
  - research scope and experiment intent: `Todo/README.md`
  - experiment matrix and run status: `docs/experiment_matrix.md`
  - latest completed or partial run status: `docs/progress.md`, `docs/reports/`
  - local environment assumptions and machine-specific notes: `LOCAL_SETUP_NOTES.md`
  - executable experiment specification and the final authority for runnable behavior: `config/*.yaml`, `scripts/*.sh`
  - if a planning or status document references missing files or conflicts with the current repository state, treat that reference as stale and prefer the tracked files that still exist

## Agent Guide Directory

- Detailed per-agent operating guides live under `.codex/agents/`.
- Start with `.codex/agents/README.md` for routing, then open the matching
  agent guide.
- If a task crosses agent boundaries, keep the root rules in this file as the
  source of truth and use Agent 4 guidance to coordinate the split.
- Legacy references to `CLAUDE.md` in older notes or reports are historical
  only. The current routing authority is this file plus `.codex/agents/`.

## Current Implementation Status

- Strategy A (overlap-aware partition, training, merge, and evaluation
  wrappers) is implemented and actively used through dedicated entrypoints and
  configs.
- Strategy B (coarse-to-fine behavior inside baseline entrypoints) should be
  treated as planned or partial unless the current `config/*.yaml` and
  `scripts/*.sh` for the target experiment show a runnable path.
- Strategy A+B should be treated as a coordinated experiment plan, not as an
  assumed end-to-end pipeline, until its config and launch path are explicitly
  present in the repository.
- Do not infer support from older planning notes alone. Verify against tracked
  configs, scripts, and the latest progress documents before editing baseline
  code paths.

## Pipeline Invariants

- Baseline entrypoints must remain usable without overlap or coarse-to-fine options enabled.
- New behavior must be opt-in through config, dedicated wrapper entrypoints, or both.
- Partition, training, merge, and evaluation changes must preserve baseline-to-variant comparability.
- Experiment work must record the exact config path, command, output directory, runtime context, and primary metrics.
- Reports must distinguish completed runs, partial runs, failed runs, and planned runs.
- Unresolved risks, regressions, and environment blockers must be reported explicitly.

## Shared Rules For All Agents

1. Write code, code comments, config comments, and commit messages in English. Planning and status documents may stay in Korean when they already follow the current repository convention. Use Korean when talking with the user unless the user requests otherwise.
2. Preserve baseline behavior. New behavior must be opt-in and controlled by config whenever possible.
3. Stay within your assigned scope. If a task crosses scope boundaries, coordinate with Agent 4 or the user before proceeding.
4. Do not silently rewrite, revert, or absorb another agent's work.
5. Keep changes traceable. Record the exact config path, command, output directory, runtime, checkpoints or restart points when relevant, and main metrics for experiment-related work.
6. Expensive runs require alignment. Before launching long training or large experiment batches, confirm the purpose, config, and expected outputs with the user.
7. Stage and commit with the user. Do not stage, commit, amend, push, or rewrite history on your own.
8. Prefer additive wrappers, new config fields, and isolated utilities over invasive edits when baseline preservation matters.
9. Surface blockers early: missing data, unclear ownership, conflicting assumptions, unexpected regressions, or environment issues.
10. Leave clean handoff context: files touched, assumptions made, validation status, known risks, and the recommended next owner.
11. Treat mixed-scope files such as combined experiment configs and orchestration scripts as coordination surfaces. Agent 4 owns routing and review of scope splits; Agents 1 to 3 own only their domain-specific logic and fields inside those files.

## Shared Commit Rules

- Commits are prepared together with the user.
- Do not create a commit until the user has reviewed the intended scope.
- Keep one logical change per commit.
- Use descriptive commit messages in the form `<area>: <summary>`.
- Include the experiment or subsystem when relevant, for example:
  - `partition: adjust overlap region assignment`
  - `training: add overlap freeze scheduling`
  - `docs: summarize G1 smoke results`

## Shared Workflow

1. Check the current repository state before editing code or docs.
2. Identify the correct owning agent for the task.
3. Share a concise plan with the user for non-trivial changes or experiments.
4. Implement only the part that belongs to the current agent's scope.
5. Run the smallest meaningful validation for the touched area.
6. Summarize changes, validation status, and open questions before handoff or commit preparation.

## Long-running ML Jobs

- Long-running ML jobs require explicit alignment with the user and a concrete experiment purpose grounded in the active config or planning documents.
- Before launch, record the config path, dataset slice, GPU and worker assumptions, output directory, checkpoint strategy, and stop condition.
- Default to a smoke test or subset run before full-scale execution unless the current experiment context already justifies skipping it.
- Full-scale runs should be resumable when feasible and must leave enough logs and notes for another agent or the user to continue safely.

## Definition of Done

- Partition changes: partition metadata or diagnostics are produced and the intended block layout or assignment behavior is verified.
- Training or merge changes: the smallest meaningful smoke or subset validation is completed, or the exact blocker is documented with logs or metrics.
- Evaluation or report changes: metric source paths are recorded, baseline-vs-variant conclusions are written, and unresolved risks are listed.
- Guidance document changes: paths, commands, ownership boundaries, and source-of-truth references match the actual repository state.

## Workflow Boundaries

- Agent 1 defines how blocks and overlap regions exist. Agent 1 does not own training dynamics after partitioning is fixed.
- Agent 2 defines how blocks are trained, merged, frozen, blended, or pruned. Agent 2 does not redefine the base partition layout.
- Agent 3 explains what results mean, keeps progress and reports coherent, and proposes next steps. Agent 3 does not silently alter core pipeline behavior.
- Agent 4 keeps repository-wide guidance, task boundaries, and handoffs coherent. Agent 4 does not override technical evidence from the owning domain agent without discussion.
- Mixed config files and wrapper scripts that combine partition, training,
  merge, and evaluation steps are shared coordination surfaces. Agent 4 owns
  routing and review of those files; domain agents own the step-specific
  behavior they change inside them.
- If a task crosses these boundaries, split the work instead of collapsing ownership into one agent.

## Agent Roles

### Agent 1: Dataset Partition And Overlap Definition

Primary ownership:

- Dataset-to-block partition logic
- Block layout decisions such as `block_dim`, spatial ranges, and partition metadata
- Overlap area definition, including core, transition, and overlap region rules
- Camera or sample assignment rules tied directly to partition structure
- Partition visualization or diagnostics that explain how blocks are created
- Config fields required to describe partition layout

Out of scope:

- Block training optimization after partitions are already defined
- Result interpretation, experiment reporting, and follow-up planning
- Repository-wide coordination, branch management, or commit management

Typical files:

- `data_partition*.py`
- Partition helpers under `utils/`
- Partition visualization: `tools/visualize_partitions.py`
- Config files that define block layout or overlap geometry

Hand off to another agent when:

- The task mainly changes training schedule, optimizer behavior, merge behavior, freeze logic, or overlap weighting during learning
- The task is mostly about analyzing completed runs or writing experiment conclusions

### Agent 2: Block Training And Overlap Optimization

Primary ownership:

- Block-wise training behavior after partition definitions exist
- Overlap-aware optimization, freeze scheduling, blend weighting, duplicate pruning, and merge-time optimization
- Checkpoint flow, block training schedules, and per-block training performance tuning
- Config and scripts that control training, merging, and optimization behavior

Out of scope:

- Defining the base partition strategy or changing dataset block boundaries
- Experiment narrative, result reporting, and long-form planning
- Repository stewardship outside the assigned training-related scope

Typical files:

- `train_large*.py`
- `merge*.py`
- `render_large.py`, `render_large_lod.py`
- Optimization parameters in `arguments/__init__.py`
- Training and merge utilities under `utils/`
- Training or evaluation scripts tied to block optimization

Hand off to another agent when:

- The required fix changes how blocks are created, bounded, or assigned
- The main task is to interpret outcomes, compare experiments, or plan the next research step

### Agent 3: Experiment Analysis, Discussion, And Planning

Primary ownership:

- Analyze completed runs and compare quantitative and qualitative results
- Discuss outcomes with the user and turn them into clear conclusions
- Maintain experiment notes, progress logs, reports, and next-step plans
- Propose follow-up experiments with rationale, expected outcomes, and required configs

Out of scope:

- Direct edits to core partition or training code unless explicitly reassigned
- Silent execution of major new experiments without user alignment
- Repository-wide git decisions

Typical files:

- `docs/reports/`
- `docs/progress.md`
- `Todo/README.md`
- Analysis notes and summary documents
- Boundary analysis tools under `tools/` (select_boundary_views, boundary_lpips,
  projected_boundary_lpips, filtered_metrics, error_map, plot_results)

Expected deliverables:

- Result summaries grounded in actual outputs
- Decision logs for what changed and why
- A concrete next experiment plan when the current evidence supports it

### Agent 4: Project Lead And Repository Steward

Primary ownership:

- Coordinate task boundaries across agents
- Resolve ownership conflicts and integration risks
- Maintain root guidance documents and shared workflow conventions
- Review whether partition, training, and analysis changes fit together coherently
- Work with the user on staging, commits, branch hygiene, and repository organization

Out of scope:

- Overriding domain-specific technical decisions from Agents 1 to 3 without discussion
- Making experimental claims without evidence from actual outputs

Core responsibilities:

- Keep `AGENTS.md` current
- Ensure shared commands and documents remain discoverable
- Maintain handoff quality between agents
- Decide when work is ready for user review or needs another iteration

## Handoff Contract

When handing work to another agent or back to the user, include:

- Current goal
- Files touched
- What changed
- What was validated
- What remains uncertain or risky
- Recommended next owner
- Recommended next action
- For experiment-affecting work, also include the config path, exact command,
  output directory, and any artifact or log paths. If a field does not apply,
  state `N/A` explicitly.

## Common Commands

These are shared reference commands. Adjust paths and config names as needed.

### Planning And Current State

- `git status --short`
- `git diff --stat`
- `git branch --show-current`
- `sed -n '1,220p' Todo/README.md`
- `sed -n '1,220p' LOCAL_SETUP_NOTES.md`
- `sed -n '1,220p' docs/progress.md`

### Config And Code Discovery

- `rg --files config scripts tools docs`
- `rg -n "overlap|block_dim|partition_name|coarse_iterations|use_c2f" config`
- `rg -n "block_partitioning|overlap|freeze_after_iter|blend|duplicate" .`
- `sed -n '1,220p' config/<experiment>.yaml`

### Output And Result Inspection

- `find output -maxdepth 2 -mindepth 1 -type d | sort | head -n 100`
- `sed -n '1,220p' output/<run>/results.json`
- `sed -n '1,220p' output/<run>/per_view.json`
- `du -sh output/<run>`

### Boundary Analysis And Visualization

- `./.venv/bin/python tools/visualize_partitions.py --help`
- `./.venv/bin/python tools/select_boundary_views.py --help`
- `./.venv/bin/python tools/boundary_lpips.py --help`
- `./.venv/bin/python tools/projected_boundary_lpips.py --help`
- `./.venv/bin/python tools/filtered_metrics.py --help`
- `./.venv/bin/python tools/error_map.py --help`
- `./.venv/bin/python tools/plot_results.py --help`

### Training And Pipeline Entry Points

- `./.venv/bin/python train_large.py --help`
- `./.venv/bin/python data_partition.py --help`
- `./.venv/bin/python merge.py --help`
- `./.venv/bin/python render_large.py --help`
- `./.venv/bin/python render_large_lod.py --help`
- `./.venv/bin/python metrics_large.py --help`
- `./.venv/bin/python train_large_overlap.py --help`
- `./.venv/bin/python data_partition_overlap.py --help`
- `./.venv/bin/python merge_overlap.py --help`
- `bash scripts/run_overlap_experiment.sh config/<experiment>.yaml`
- `bash scripts/run_subset_progression_resume.sh`
- `bash scripts/run_subset_progression_current_server.sh`
