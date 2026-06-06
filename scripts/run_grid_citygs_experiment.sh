#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  echo "Usage: $0 <config-name-or-path>"
  echo "Example: $0 smoke_test/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000"
}

CONFIG_ARG="${1:-${CONFIG:-}}"
if [[ -z "$CONFIG_ARG" ]]; then
  usage >&2
  exit 1
fi

if [[ "$CONFIG_ARG" == *.yaml || "$CONFIG_ARG" == config/* ]]; then
  CONFIG_PATH="$CONFIG_ARG"
else
  CONFIG_PATH="config/${CONFIG_ARG}.yaml"
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Missing config: $CONFIG_PATH" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
MODEL_NAME="$(basename "${CONFIG_PATH%.yaml}")"
MODEL_PATH="output/${MODEL_NAME}"
PORT="${PORT:-6400}"
GPU_RETRY_SECONDS="${GPU_RETRY_SECONDS:-120}"
START_DELAY_SECONDS="${START_DELAY_SECONDS:-120}"
SKIP_PARTITION="${SKIP_PARTITION:-0}"
SKIP_EXISTING_CELLS="${SKIP_EXISTING_CELLS:-1}"
RUN_RENDER="${RUN_RENDER:-1}"
RUN_METRICS="${RUN_METRICS:-1}"
CUSTOM_TEST="${CUSTOM_TEST:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/manual_passage_review_15000}"
TEST_SET_NAME="${TEST_SET_NAME:-$(basename "$CUSTOM_TEST")}"

TRAIN_EXTRA_ARGS_ARRAY=()
if [[ -n "${TRAIN_EXTRA_ARGS:-}" ]]; then
  read -r -a TRAIN_EXTRA_ARGS_ARRAY <<< "$TRAIN_EXTRA_ARGS"
fi

PARTITION_EXTRA_ARGS_ARRAY=()
if [[ -n "${PARTITION_EXTRA_ARGS:-}" ]]; then
  read -r -a PARTITION_EXTRA_ARGS_ARRAY <<< "$PARTITION_EXTRA_ARGS"
fi

get_available_gpu() {
  local mem_threshold="${GPU_MEM_THRESHOLD:-500}"
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

ITERATION="$("$PYTHON_BIN" - <<PY
import yaml
with open("$CONFIG_PATH", "r", encoding="utf-8") as handle:
    cfg = yaml.load(handle, Loader=yaml.FullLoader)
print(cfg["optim_params"]["iterations"])
PY
)"

BLOCKS="$("$PYTHON_BIN" - <<PY
import yaml
with open("$CONFIG_PATH", "r", encoding="utf-8") as handle:
    cfg = yaml.load(handle, Loader=yaml.FullLoader)
block_dim = cfg["model_params"]["block_dim"]
print(block_dim[0] * block_dim[1] * block_dim[2])
PY
)"

echo "Config: $CONFIG_PATH"
echo "Model path: $MODEL_PATH"
echo "Blocks: $BLOCKS"
echo "Iteration: $ITERATION"

if [[ "$SKIP_PARTITION" != "1" ]]; then
  gpu_id=$(wait_for_available_gpu)
  echo "GPU $gpu_id is available. Running grid partition."
  CUDA_VISIBLE_DEVICES="$gpu_id" "$PYTHON_BIN" data_partition.py \
    --config "$CONFIG_PATH" \
    "${PARTITION_EXTRA_ARGS_ARRAY[@]}"
else
  echo "Skipping partition because SKIP_PARTITION=1."
fi

pids=()
blocks=()
for ((block_id = 0; block_id < BLOCKS; block_id++)); do
  cell_ply="${MODEL_PATH}/cells/cell${block_id}/point_cloud_blocks/scale_1.0/iteration_${ITERATION}/point_cloud.ply"
  if [[ "$SKIP_EXISTING_CELLS" == "1" && -f "$cell_ply" ]]; then
    echo "Skipping cell ${block_id}; existing PLY found: $cell_ply"
    continue
  fi

  gpu_id=$(wait_for_available_gpu)
  echo "GPU $gpu_id is available. Starting grid block '$block_id'."
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
    echo "Training failed for grid block '${blocks[$idx]}' (pid ${pids[$idx]})." >&2
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "Skipping merge because one or more grid block trainings failed." >&2
  exit 1
fi

gpu_id=$(wait_for_available_gpu)
echo "GPU $gpu_id is available. Merging grid blocks at iteration $ITERATION."
CUDA_VISIBLE_DEVICES="$gpu_id" "$PYTHON_BIN" merge.py \
  --config "$CONFIG_PATH" \
  --iteration "$ITERATION"

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
