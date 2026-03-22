#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <label> <command> [args...]" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LABEL="$1"
shift

mkdir -p logs

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
SAFE_LABEL="${LABEL//[^A-Za-z0-9_.-]/_}"
CMD_LOG="logs/${TIMESTAMP}_${SAFE_LABEL}.log"
GPU_LOG="logs/${TIMESTAMP}_${SAFE_LABEL}_gpu.csv"
META_LOG="logs/${TIMESTAMP}_${SAFE_LABEL}_meta.txt"

{
  echo "timestamp=${TIMESTAMP}"
  echo "label=${LABEL}"
  echo "cwd=${ROOT_DIR}"
  echo "command=$*"
  echo "hostname=$(hostname)"
  echo "date_start=$(date '+%F %T %z')"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
  echo "PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-}"
  echo "MAX_CACHE_NUM=${MAX_CACHE_NUM:-}"
} > "$META_LOG"

nvidia-smi -L >> "$META_LOG" 2>&1 || true

cleanup() {
  if [[ -n "${MONITOR_PID:-}" ]]; then
    kill "$MONITOR_PID" >/dev/null 2>&1 || true
    wait "$MONITOR_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

{
  echo "timestamp,index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw"
  nvidia-smi \
    --query-gpu=timestamp,index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw \
    --format=csv,noheader,nounits \
    --loop=5
} > "$GPU_LOG" &
MONITOR_PID=$!

echo "[monitor] meta: ${META_LOG}" | tee "$CMD_LOG"
echo "[monitor] gpu : ${GPU_LOG}" | tee -a "$CMD_LOG"
echo "[monitor] cmd : ${CMD_LOG}" | tee -a "$CMD_LOG"
echo "[monitor] run : $*" | tee -a "$CMD_LOG"

START_EPOCH="$(date +%s)"
set +e
stdbuf -oL -eL "$@" 2>&1 | tee -a "$CMD_LOG"
CMD_STATUS=${PIPESTATUS[0]}
set -e
END_EPOCH="$(date +%s)"
DURATION="$((END_EPOCH - START_EPOCH))"

{
  echo "date_end=$(date '+%F %T %z')"
  echo "exit_code=${CMD_STATUS}"
  echo "duration_sec=${DURATION}"
} >> "$META_LOG"

echo "[monitor] exit_code=${CMD_STATUS}" | tee -a "$CMD_LOG"
echo "[monitor] duration_sec=${DURATION}" | tee -a "$CMD_LOG"

exit "$CMD_STATUS"
