#!/usr/bin/env bash
set -euo pipefail

get_available_gpu() {
  local mem_threshold=500
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -v threshold="$mem_threshold" -F', ' '
  $2 < threshold { print $1; exit }
  '
}

wait_for_available_gpu() {
  local gpu_id
  while true; do
    gpu_id=$(get_available_gpu)
    if [[ -n "$gpu_id" ]]; then
      echo "$gpu_id"
      return
    fi
    echo "No GPU available. Retrying in ${GPU_RETRY_SECONDS} seconds." >&2
    sleep "$GPU_RETRY_SECONDS"
  done
}

CONFIG="${CONFIG:-scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units}"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
CONFIG_PATH="config/$CONFIG.yaml"
SOURCE_PATH="${SOURCE_PATH:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered}"
POINT_SOURCE_PATH="${POINT_SOURCE_PATH:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416}"
PARTITION_NAME="${PARTITION_NAME:-$("$PYTHON_BIN" - <<PY
import yaml
with open("$CONFIG_PATH", "r", encoding="utf-8") as handle:
    cfg = yaml.load(handle, Loader=yaml.FullLoader)
print(cfg["model_params"]["partition_name"])
PY
)}"
RANGE_FILE="${RANGE_FILE:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub.txt}"
MAX_BLOCK_ID="${MAX_BLOCK_ID:-9}"
PORT="${PORT:-6200}"
GPU_RETRY_SECONDS="${GPU_RETRY_SECONDS:-120}"
START_DELAY_SECONDS="${START_DELAY_SECONDS:-120}"
MODEL_NAME="$(basename "$CONFIG")"
MODEL_PATH="output/$MODEL_NAME"
SKIP_EXISTING_CELLS="${SKIP_EXISTING_CELLS:-0}"
RUN_RENDER="${RUN_RENDER:-0}"
RUN_METRICS="${RUN_METRICS:-0}"
CUSTOM_TEST="${CUSTOM_TEST:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000}"
TEST_SET_NAME="${TEST_SET_NAME:-$(basename "$CUSTOM_TEST")}"

TRAIN_EXTRA_ARGS_ARRAY=()
if [[ -n "${TRAIN_EXTRA_ARGS:-}" ]]; then
  read -r -a TRAIN_EXTRA_ARGS_ARRAY <<< "$TRAIN_EXTRA_ARGS"
fi

RANGE_UNIT_NAMES=(
  401
  404
  409
  411
  412
  413
  414
  passage1
  passage2
  passage3
)

ITERATION="${ITERATION:-$("$PYTHON_BIN" - <<PY
import yaml
with open("$CONFIG_PATH", "r", encoding="utf-8") as handle:
    cfg = yaml.load(handle, Loader=yaml.FullLoader)
print(cfg["optim_params"]["iterations"])
PY
)}"

"$PYTHON_BIN" tools/create_colmap_unit_partition.py \
  --source-path "$SOURCE_PATH" \
  --partition-name "$PARTITION_NAME" \
  --range-file "$RANGE_FILE" \
  --range-unit-names "${RANGE_UNIT_NAMES[@]}" \
  --range-overlap-policy single_owner \
  --camera-outlier-filter robust \
  --camera-outlier-z-threshold 8.0 \
  --camera-outlier-min-distance 5.0 \
  --camera-outlier-distance-ratio 4.0 \
  --point-source-path "$POINT_SOURCE_PATH" \
  --point-filter-box -12.0 -4.0 -14.0 12.0 7.0 8.0 \
  --core-point-policy single_owner \
  --validate-point-cloud-length \
  --overwrite

pids=()
blocks=()
for block_id in $(seq 0 "$MAX_BLOCK_ID"); do
  cell_ply="${MODEL_PATH}/cells/cell${block_id}/point_cloud_blocks/scale_1.0/iteration_${ITERATION}/point_cloud.ply"
  if [[ "$SKIP_EXISTING_CELLS" == "1" && -f "$cell_ply" ]]; then
    echo "Skipping cell ${block_id}; existing PLY found: $cell_ply"
    continue
  fi

  gpu_id=$(wait_for_available_gpu)
  echo "GPU $gpu_id is available. Starting unit block '$block_id'"
  CUDA_VISIBLE_DEVICES="$gpu_id" WANDB_MODE=offline "$PYTHON_BIN" train_large.py \
    --config "$CONFIG_PATH" \
    --block_id "$block_id" \
    --port "$PORT" \
    "${TRAIN_EXTRA_ARGS_ARRAY[@]}" &
  pids+=("$!")
  blocks+=("$block_id")
  PORT=$((PORT + 1))
  sleep "$START_DELAY_SECONDS"
done

failed=0
for idx in "${!pids[@]}"; do
  if ! wait "${pids[$idx]}"; then
    echo "Training failed for unit block '${blocks[$idx]}' (pid ${pids[$idx]})." >&2
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "Skipping merge because one or more unit block trainings failed." >&2
  exit 1
fi

gpu_id=$(wait_for_available_gpu)
echo "GPU $gpu_id is available. Merging unit blocks at iteration $ITERATION."
CUDA_VISIBLE_DEVICES="$gpu_id" "$PYTHON_BIN" merge.py --config "$CONFIG_PATH" --iteration "$ITERATION"

if [[ "$RUN_RENDER" == "1" ]]; then
  gpu_id=$(wait_for_available_gpu)
  echo "GPU $gpu_id is available. Rendering $TEST_SET_NAME."
  CUDA_VISIBLE_DEVICES="$gpu_id" "$PYTHON_BIN" render_large.py \
    --config "$CONFIG_PATH" \
    --iteration "$ITERATION" \
    --custom_test "$CUSTOM_TEST"
fi

if [[ "$RUN_METRICS" == "1" ]]; then
  gpu_id=$(wait_for_available_gpu)
  echo "GPU $gpu_id is available. Computing metrics for $TEST_SET_NAME."
  CUDA_VISIBLE_DEVICES="$gpu_id" "$PYTHON_BIN" metrics_large.py \
    --model_paths "$MODEL_PATH" \
    --test_sets "$TEST_SET_NAME"
fi
