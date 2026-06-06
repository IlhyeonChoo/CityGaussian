#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
GPU_ID="${GPU_ID:-0}"
ITERATION="${ITERATION:-30000}"
CUSTOM_TEST="${CUSTOM_TEST:-data/W2_4_3_merge_rooms_with_passage_v3_undistorted/render_subsets/balanced_manual_units_500}"
TEST_SET_NAME="${TEST_SET_NAME:-$(basename "$CUSTOM_TEST")}"

LABELS=(
  "grid30k_to_grid30k"
  "grid30k_to_manual30k"
  "manual30k_to_grid30k"
)

CONFIGS=(
  "config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_citygs_xz10_30000.yaml"
  "config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000.yaml"
  "config/smoke_test/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000.yaml"
)

MODEL_PATHS=(
  "output/w2_filtered_manual_passage_no415_best_grid30k_to_citygs_xz10_30000"
  "output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000"
  "output/w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000"
)

expected_count() {
  "$PYTHON_BIN" - "$1" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(0)
else:
    print(sum(1 for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".png"))
PY
}

for idx in "${!LABELS[@]}"; do
  label="${LABELS[$idx]}"
  config="${CONFIGS[$idx]}"
  model_path="${MODEL_PATHS[$idx]}"
  render_dir="$model_path/$TEST_SET_NAME/ours_$ITERATION/renders"
  render_count="$(expected_count "$render_dir")"

  echo "[$(date -Is)] Render check: $label ($render_count/500)"
  if [[ "${FORCE_RENDER:-0}" == "1" || "$render_count" != "500" ]]; then
    echo "[$(date -Is)] Rendering $label"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PYTHON_BIN" render_large.py \
      --config "$config" \
      --iteration "$ITERATION" \
      --custom_test "$CUSTOM_TEST"
  else
    echo "[$(date -Is)] Skipping render for $label"
  fi
done

for idx in "${!LABELS[@]}"; do
  label="${LABELS[$idx]}"
  model_path="${MODEL_PATHS[$idx]}"
  echo "[$(date -Is)] Metrics $label"
  CUDA_VISIBLE_DEVICES="$GPU_ID" "$PYTHON_BIN" tools/streaming_metrics_large.py \
    --model_paths "$model_path" \
    --test_sets "$TEST_SET_NAME"
done

echo "[$(date -Is)] Done"
