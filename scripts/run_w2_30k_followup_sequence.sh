#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
GPU_RETRY_SECONDS="${GPU_RETRY_SECONDS:-10}"
START_DELAY_SECONDS="${START_DELAY_SECONDS:-20}"
TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---max_cache_num 256}"
WAIT_INTERVAL_SECONDS="${WAIT_INTERVAL_SECONDS:-60}"
FIRST_PID="${FIRST_PID:-}"

BEST_GRID_CONFIG="smoke_test/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000"
MANUAL_CONFIG="smoke_test/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000"
MANUAL_TO_GRID_CONFIG="smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000"
RANGE_FILE="data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt"
EMPTY_TEMPLATE="output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000/cells/cell0/point_cloud_blocks/scale_1.0/iteration_15000/point_cloud.ply"

BEST_GRID_OUT="output/w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000"
MANUAL_OUT="output/w2_filtered_manual_passage_no415_manual_units_coarse30k_30000"
MANUAL_TO_GRID_OUT="output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000"

BEST_GRID_LOG="logs/20260603_w2_best_grid15k_to_citygs_xz10_30000.log"
MANUAL_LOG="logs/20260603_w2_manual_units_coarse30k_30000.log"
MANUAL_TO_GRID_LOG="logs/20260603_w2_manual_units30k_to_citygs_xz10_30000.log"

log() {
  printf '[%(%Y-%m-%dT%H:%M:%S%z)T] %s\n' -1 "$*"
}

wait_for_external_pid() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return
  fi
  while kill -0 "$pid" >/dev/null 2>&1; do
    log "Waiting for existing best-grid 30k process PID $pid."
    sleep "$WAIT_INTERVAL_SECONDS"
  done
}

ensure_no_failure_log() {
  local log_path="$1"
  if [[ -f "$log_path" ]] && rg -n 'Traceback|OutOfMemory|CUDA out of memory|Training failed|Skipping merge because' "$log_path"; then
    log "Failure pattern found in $log_path"
    exit 1
  fi
}

ensure_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    log "Missing expected file: $path"
    exit 1
  fi
}

run_best_grid_if_needed() {
  local merged_ply="$BEST_GRID_OUT/point_cloud/iteration_30000/point_cloud.ply"
  local results_json="$BEST_GRID_OUT/results.json"
  if [[ -f "$merged_ply" && -f "$results_json" ]]; then
    log "Best-grid 30k already completed."
    return
  fi
  if [[ -n "$FIRST_PID" ]]; then
    wait_for_external_pid "$FIRST_PID"
    ensure_no_failure_log "$BEST_GRID_LOG"
    ensure_file "$merged_ply"
    ensure_file "$results_json"
    log "Existing best-grid 30k process completed successfully."
    return
  fi
  log "Launching best-grid 15k -> xz10 grid 30k."
  SKIP_PARTITION=1 \
  SKIP_EXISTING_CELLS=1 \
  PYTHON_BIN="$PYTHON_BIN" \
  GPU_RETRY_SECONDS="$GPU_RETRY_SECONDS" \
  START_DELAY_SECONDS="$START_DELAY_SECONDS" \
  PORT=6700 \
  TRAIN_EXTRA_ARGS="$TRAIN_EXTRA_ARGS" \
  ./scripts/run_grid_citygs_experiment.sh "$BEST_GRID_CONFIG" \
    > "$BEST_GRID_LOG" 2>&1
  ensure_no_failure_log "$BEST_GRID_LOG"
  ensure_file "$merged_ply"
  ensure_file "$results_json"
}

run_manual_if_needed() {
  local merged_ply="$MANUAL_OUT/point_cloud/iteration_30000/point_cloud.ply"
  if [[ -f "$merged_ply" ]]; then
    log "Manual-unit 30k already completed."
    return
  fi
  log "Launching coarse 30k -> manual-unit 30k."
  CONFIG="$MANUAL_CONFIG" \
  RANGE_FILE="$RANGE_FILE" \
  PYTHON_BIN="$PYTHON_BIN" \
  GPU_RETRY_SECONDS="$GPU_RETRY_SECONDS" \
  START_DELAY_SECONDS="$START_DELAY_SECONDS" \
  PORT=6800 \
  TRAIN_EXTRA_ARGS="$TRAIN_EXTRA_ARGS" \
  SKIP_EXISTING_CELLS=1 \
  RUN_RENDER=1 \
  RUN_METRICS=1 \
  ./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh \
    > "$MANUAL_LOG" 2>&1
  ensure_no_failure_log "$MANUAL_LOG"
  ensure_file "$merged_ply"
}

run_manual_to_grid_if_needed() {
  local merged_ply="$MANUAL_TO_GRID_OUT/point_cloud/iteration_30000/point_cloud.ply"
  local results_json="$MANUAL_TO_GRID_OUT/results.json"
  if [[ -f "$merged_ply" && -f "$results_json" ]]; then
    log "Manual-unit30k -> xz10 grid 30k already completed."
    return
  fi

  log "Preparing empty xz10 grid cells for manual-unit30k pretrain."
  "$PYTHON_BIN" tools/prepare_grid_empty_cells.py \
    --config "config/${MANUAL_TO_GRID_CONFIG}.yaml" \
    --iteration 30000 \
    --prepare-empty-ply \
    --empty-template "$EMPTY_TEMPLATE" \
    --write-json "$MANUAL_TO_GRID_OUT/diagnostics/grid_pretrain_counts_iter30000.json"

  log "Launching manual-unit30k merged -> xz10 grid 30k."
  SKIP_PARTITION=1 \
  SKIP_EXISTING_CELLS=1 \
  PYTHON_BIN="$PYTHON_BIN" \
  GPU_RETRY_SECONDS="$GPU_RETRY_SECONDS" \
  START_DELAY_SECONDS="$START_DELAY_SECONDS" \
  PORT=6900 \
  TRAIN_EXTRA_ARGS="$TRAIN_EXTRA_ARGS" \
  ./scripts/run_grid_citygs_experiment.sh "$MANUAL_TO_GRID_CONFIG" \
    > "$MANUAL_TO_GRID_LOG" 2>&1
  ensure_no_failure_log "$MANUAL_TO_GRID_LOG"
  ensure_file "$merged_ply"
  ensure_file "$results_json"
}

run_best_grid_if_needed
run_manual_if_needed
run_manual_to_grid_if_needed

log "W2 30k followup sequence completed."
