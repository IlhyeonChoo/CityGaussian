# AGENTS_Mod.md

This file is a condensed alternative to the current root `AGENTS.md`.

Its job is to keep only durable, repo-wide guidance at the project root.
Detailed agent-specific responsibilities, examples, checklists, and command
lists should live under `.codex/agents/`.

Unless overridden here, follow the global defaults for language, safety, git,
and validation behavior.

## Project Scope

- Project: CityGaussian V1 boundary artifact mitigation research
- Objective: reduce seams, color mismatch, and density gaps across block
  boundaries without relying on global alignment
- Baseline: preserve the original CityGaussian V1 pipeline unless an experiment
  explicitly opts into new behavior
- Strategy A: overlap-aware partitioning with boundary-sharing regions
- Strategy B: hierarchical coarse-to-fine training
- Strategy A+B: coordinated overlap-aware partitioning plus coarse-to-fine
  training

## Source Of Truth

Use the smallest set of files that answers the current question.

- Scope and experiment intent: `Todo/README.md`
- Experiment matrix and run status: `docs/experiment_matrix.md`
- Latest completed or partial run status: `docs/progress.md`,
  `docs/reports/`
- Local machine assumptions: `LOCAL_SETUP_NOTES.md`
- Runnable behavior: `config/*.yaml`, `scripts/*.sh`
- Detailed agent routing and ownership: `.codex/agents/README.md`

If planning notes conflict with tracked configs, scripts, or current repository
state, prefer the tracked runnable files.

## Repository Map

- Partition entrypoints: `data_partition.py`, `data_partition_overlap.py`
- Training entrypoints: `train_large.py`, `train_large_overlap.py`
- Merge entrypoints: `merge.py`, `merge_overlap.py`
- Rendering: `render_large.py`, `render_large_lod.py`, `viewer.py`
- Evaluation: `metrics_large.py`
- Shared arguments: `arguments/__init__.py`
- Analysis and visualization tools: `tools/`
- Experiment configs and launch scripts: `config/`, `scripts/`
- Runtime artifacts: `data/`, `output/`

## Current Status

- Strategy A is implemented and actively used through dedicated overlap-aware
  entrypoints and configs.
- Strategy B should be treated as planned or partial unless a target
  `config/*.yaml` and `scripts/*.sh` clearly define a runnable path.
- Strategy A+B should be treated as a coordinated experiment plan until a full
  end-to-end config and launch path exist in the repository.

## Pipeline Invariants

- Baseline entrypoints must keep working when experimental options are disabled.
- New behavior must be opt-in through config, wrapper entrypoints, or both.
- Partition, training, merge, and evaluation changes must preserve
  baseline-to-variant comparability.
- Experiment-affecting work must record the config path, command, output
  directory, runtime assumptions, and primary metrics or failure evidence.
- Reports must distinguish completed, partial, failed, and planned runs.
- Unresolved risks, regressions, and environment blockers must be stated
  explicitly.

## Root Vs Agent Guides

Keep the root guide short. Put only shared rules and routing here.

Move the following to `.codex/agents/`:

- Detailed agent responsibilities
- Domain-specific examples and handoff patterns
- Agent-specific validation expectations
- Long command catalogs
- File-level ownership notes that matter only within one domain

## Routing

Use `.codex/agents/README.md` first if ownership is unclear.

- Agent 1: partition geometry, overlap definitions, spatial ranges, camera or
  sample assignment tied to partition layout
- Agent 2: training, merge, freeze schedules, blending, pruning, checkpoint
  flow, and optimization after partitioning is fixed
- Agent 3: experiment interpretation, reports, progress tracking, and next-step
  planning
- Agent 4: repo-level coordination, ownership boundaries, shared guidance, and
  handoff quality

Detailed guides:

- `.codex/agents/agent1_partition_overlap.md`
- `.codex/agents/agent2_training_merge.md`
- `.codex/agents/agent3_analysis_planning.md`
- `.codex/agents/agent4_project_lead.md`

## Mixed-Scope Rule

Combined experiment configs and orchestration scripts are coordination surfaces
when they mix partition, training, merge, and evaluation concerns.

- Agent 1 owns partition geometry fields.
- Agent 2 owns training and merge behavior fields.
- Agent 3 owns interpretation-only notes or report-facing outputs.
- Agent 4 owns routing, split decisions, and cross-scope review.

Do not solve a cross-cutting task by silently expanding one agent's scope.

## Shared Rules

- Preserve baseline behavior and make experimental behavior opt-in.
- Stay within scope. If a task crosses scopes, split it or coordinate through
  Agent 4.
- Do not silently rewrite, revert, or absorb another agent's work.
- Prefer additive wrappers, isolated utilities, and config flags over invasive
  edits when baseline preservation matters.
- Surface blockers early: missing data, unclear ownership, stale docs, or
  unexpected regressions.
- Leave clean handoff context so another agent or the user can continue
  safely.

## Experiment Workflow

- Check the relevant source-of-truth documents and runnable config or script
  before editing experiment-affecting behavior.
- Keep ownership boundaries explicit when touching mixed-scope configs or
  orchestration scripts.
- For experiment-affecting work, tie the change to a config path, exact
  command, output directory, and main artifact or failure evidence.
- Summarize what changed, what was validated, and the recommended next owner or
  action at handoff.

## Experiment Run Recording

- Record the config path, exact command, output directory, and artifact or log
  paths for long or experiment-affecting runs.
- Leave enough checkpoint and log context for another agent or the user to
  resume or inspect the run safely.

## Handoff Contract

Every handoff should include:

- Current goal
- Files touched
- What changed
- What was validated
- What remains uncertain or risky
- Recommended next owner
- Recommended next action

For experiment-affecting work, also include:

- Config path
- Exact command
- Output directory
- Artifact or log paths

If a field does not apply, state `N/A` explicitly.

## Definition Of Done

- Partition work: the intended layout or assignment behavior is verifiable from
  metadata, diagnostics, or visualization.
- Training or merge work: a smoke test or subset validation ran, or the exact
  blocker is documented with usable evidence.
- Analysis work: conclusions are grounded in actual artifacts and run status is
  explicit.
- Guidance work: paths, ownership notes, and workflow instructions match the
  current repository state.
