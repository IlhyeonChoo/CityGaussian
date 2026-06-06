# Legacy Notes

This directory stores historical notes from the temporary 16GB server and the
server-migration phase.

These files are kept for traceability, but they are not the active source of
truth for the current workspace.

## Use These Files As Historical Context Only

- `20260321_local_setup_prev_server.md`
  - Temporary 16GB server setup notes before the current-server workflow was
    stabilized.
- `20260322_worktree_change_inventory.md`
  - Migration-era inventory of what to keep, copy, or ignore while moving work
    off the old machine.
- `20260323_prev_current_server_comparison.md`
  - Point-in-time comparison between the old 16GB server and the current
    workspace before the current notes were refreshed.

## Current Sources Of Truth

- `LOCAL_SETUP_NOTES.md`
  - Active current-server setup notes.
- `docs/progress.md`
  - Current progress timeline with legacy classification recorded.
- `scripts/setup_current_server_experiments.sh`
  - Active current-server subset setup entrypoint.
- `scripts/run_subset_progression_current_server.sh`
  - Active current-server subset progression entrypoint.

## Legacy Operational Scripts

- `scripts/legacy/run_subset_progression_resume.sh`
  - Archived 16GB recovery flow. Do not use this as the default path for the
    current server.
