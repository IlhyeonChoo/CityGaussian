#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <config-path> [extra args for training/render]"
  exit 1
fi

CONFIG="$1"
shift || true

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
MODEL_NAME="$(basename "${CONFIG%.*}")"

ITERATIONS="$("$PYTHON_BIN" -c 'import sys,yaml; cfg=yaml.safe_load(open(sys.argv[1])); print(cfg["optim_params"]["iterations"])' "$CONFIG")"
BLOCKS="$("$PYTHON_BIN" -c 'import sys,yaml; cfg=yaml.safe_load(open(sys.argv[1])); bd=cfg["model_params"]["block_dim"]; print(bd[0]*bd[1]*bd[2])' "$CONFIG")"

echo "[1/5] overlap partition: ${CONFIG}"
"$PYTHON_BIN" data_partition_overlap.py --config "$CONFIG"

echo "[2/5] block training: ${BLOCKS} cells"
for ((block_id = 0; block_id < BLOCKS; block_id++)); do
  echo "  - cell ${block_id}/${BLOCKS}"
  "$PYTHON_BIN" train_large_overlap.py --config "$CONFIG" --block_id "$block_id" "$@"
done

echo "[3/5] overlap merge"
"$PYTHON_BIN" merge_overlap.py --config "$CONFIG" --iteration "$ITERATIONS"

echo "[4/5] render"
"$PYTHON_BIN" render_large.py --config "$CONFIG" --iteration "$ITERATIONS" --skip_train

echo "[5/5] metrics"
"$PYTHON_BIN" metrics_large.py -m "output/${MODEL_NAME}" -t test
