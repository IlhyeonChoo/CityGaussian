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
    echo "No GPU available. Retrying in 2 minutes." >&2
    sleep 120
  done
}

CONFIG="${CONFIG:-scene_W2_4_3_merged_rooms_passage_v3_no405410416_units}"
SOURCE_PATH="${SOURCE_PATH:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416}"
PARTITION_NAME="${PARTITION_NAME:-scene_W2_4_3_merged_rooms_passage_v3_no405410416_units}"
MAX_BLOCK_ID="${MAX_BLOCK_ID:-7}"
PORT="${PORT:-6200}"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

UNIT_PATHS=(
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/401_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/404_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/409_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/411_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/412_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/413_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/414_passage_v3
  data/W2_4_3_merge_rooms_with_passage_v3_undistorted/415_passage_v3
)

"$PYTHON_BIN" tools/create_colmap_unit_partition.py \
  --source-path "$SOURCE_PATH" \
  --partition-name "$PARTITION_NAME" \
  --unit-paths "${UNIT_PATHS[@]}" \
  --overwrite

pids=()
blocks=()
for block_id in $(seq 0 "$MAX_BLOCK_ID"); do
  gpu_id=$(wait_for_available_gpu)
  echo "GPU $gpu_id is available. Starting unit block '$block_id'"
  CUDA_VISIBLE_DEVICES="$gpu_id" WANDB_MODE=offline "$PYTHON_BIN" train_large.py \
    --config "config/$CONFIG.yaml" \
    --block_id "$block_id" \
    --port "$PORT" &
  pids+=("$!")
  blocks+=("$block_id")
  PORT=$((PORT + 1))
  sleep 120
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
echo "GPU $gpu_id is available. Merging unit blocks."
CUDA_VISIBLE_DEVICES="$gpu_id" "$PYTHON_BIN" merge.py --config "config/$CONFIG.yaml"
