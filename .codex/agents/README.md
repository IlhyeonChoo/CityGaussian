# Agent Guides

This directory contains detailed working guides for the four project agents
defined in the repository root [`AGENTS.md`](../../AGENTS.md).

Use this directory when the root guide is too high level and a task needs a
clear owner, concrete file scope, validation expectations, or a handoff target.

## Reading Order

1. Read the root [`AGENTS.md`](../../AGENTS.md) for shared rules and project
   invariants.
2. Read the matching guide below for task-specific ownership details.
3. If a task crosses two guides, split the work or coordinate through Agent 4.
4. Treat legacy references to `CLAUDE.md` in older planning notes or reports as
   historical only. Use the root guide plus this directory for current routing.

## Guides

- [Agent 1: Dataset Partition And Overlap Definition](./agent1_partition_overlap.md)
- [Agent 2: Block Training And Overlap Optimization](./agent2_training_merge.md)
- [Agent 3: Experiment Analysis, Discussion, And Planning](./agent3_analysis_planning.md)
- [Agent 4: Project Lead And Repository Steward](./agent4_project_lead.md)

## Quick Routing

- Choose Agent 1 when the task changes how blocks, ranges, overlap regions, or
  camera assignment are defined. Agent 1 also owns
  `tools/visualize_partitions.py`.
- Choose Agent 2 when the task changes how already-defined blocks are trained,
  frozen, blended, merged, resumed, or pruned. Agent 2 also owns rendering
  entrypoints (`render_large.py`, `render_large_lod.py`).
- Choose Agent 3 when the task is mainly about interpreting results, recording
  experiment status, or proposing the next experiment. Agent 3 owns boundary
  analysis tools under `tools/` (boundary_lpips, projected_boundary_lpips,
  filtered_metrics, error_map, plot_results, select_boundary_views).
- Choose Agent 4 when the task is mainly about ownership boundaries, repo-level
  documentation, task coordination, or handoff quality.
- Choose Agent 4 first when a config file or shell script mixes partition,
  training, merge, and evaluation concerns and the ownership split is not
  already obvious.

## Mixed-Scope Files

- Combined experiment configs are coordination surfaces when they contain both
  partition geometry and training or merge controls. Agent 4 decides the split;
  Agent 1 owns geometry fields, Agent 2 owns training and merge fields, and
  Agent 3 owns interpretation-only notes.
- Orchestration scripts that call multiple pipeline stages are also coordination
  surfaces. Agent 4 owns task decomposition and review of those scripts, while
  domain agents own the behavior of the specific pipeline steps they modify.
- When a mixed-scope file is touched for only one domain reason, keep the edit
  limited to that domain and mention the cross-scope surface explicitly in the
  handoff.

## Cross-Agent Rule

Do not solve a cross-cutting problem by silently expanding one agent's scope.
If the required change spans partition logic, training behavior, and reporting,
split the work into separate handoffs with explicit owners.
