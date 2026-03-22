#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
MAX_CACHE_NUM="${MAX_CACHE_NUM:-32}"
CUSTOM_TEST="${CUSTOM_TEST:-data/matrix_city/aerial/test/block_all_test}"
VIEW_MANIFEST="${VIEW_MANIFEST:-output/boundary_analysis/subset4_block_all_test_strict.json}"
TRAIN_SOURCE="data/matrix_city/aerial/train/block_all"
TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:-}"

export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.9}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export WANDB_MODE="${WANDB_MODE:-offline}"

log() {
  printf '[%s] %s\n' "$(date '+%F %T %z')" "$*"
}

need_file() {
  [[ -f "$1" ]]
}

run_step() {
  local label="$1"
  shift
  log "$label"
  "$@"
}

train_blocks() {
  local trainer="$1"
  local cfg="$2"
  local out_dir="$3"
  local iteration="$4"
  local -a extra_args=()

  if [[ -n "$TRAIN_EXTRA_ARGS" ]]; then
    read -r -a extra_args <<< "$TRAIN_EXTRA_ARGS"
  fi

  for block_id in 0 1 2 3; do
    local cell_ply="${out_dir}/cells/cell${block_id}/point_cloud_blocks/scale_1.0/iteration_${iteration}/point_cloud.ply"
    if need_file "$cell_ply"; then
      log "skip cell${block_id}: ${cell_ply} already exists"
      continue
    fi
    run_step "train cell${block_id}: ${cfg}" \
      "$PYTHON_BIN" "$trainer" --config "$cfg" --block_id "$block_id" --max_cache_num "$MAX_CACHE_NUM" "${extra_args[@]}"
  done
}

run_filtered_eval() {
  local out_dir="$1"
  local test_set="$2"
  local iteration="$3"

  local filtered_json="${out_dir}/${test_set}/ours_${iteration}/boundary_view_metrics.json"
  local proj_json="${out_dir}/${test_set}/ours_${iteration}/projected_boundary_lpips.json"

  if ! need_file "$filtered_json"; then
    run_step "filtered metrics: ${out_dir} iter ${iteration}" \
      "$PYTHON_BIN" tools/filtered_metrics.py \
      --output_dir "$out_dir" \
      --test_set "$test_set" \
      --iteration "$iteration" \
      --view_manifest "$VIEW_MANIFEST"
  else
    log "skip filtered metrics: ${filtered_json} already exists"
  fi

  if ! need_file "$proj_json"; then
    run_step "projected boundary LPIPS: ${out_dir} iter ${iteration}" \
      env PYTHONPATH="tools:${PYTHONPATH:-}" "$PYTHON_BIN" tools/projected_boundary_lpips.py \
      --output_dir "$out_dir" \
      --test_set "$test_set" \
      --iteration "$iteration" \
      --view_manifest "$VIEW_MANIFEST" \
      --save_crops
  else
    log "skip projected boundary LPIPS: ${proj_json} already exists"
  fi
}

run_coarse() {
  local cfg="$1"
  local out_dir="$2"
  local iteration="$3"
  local coarse_ply="${out_dir}/point_cloud/iteration_${iteration}/point_cloud.ply"

  if need_file "$coarse_ply"; then
    log "skip coarse: ${coarse_ply} already exists"
    return
  fi

  run_step "coarse train: ${cfg}" \
    "$PYTHON_BIN" train_large.py --config "$cfg" --max_cache_num "$MAX_CACHE_NUM"
}

run_non_overlap() {
  local cfg="$1"
  local out_dir="$2"
  local iteration="$3"
  local partition_name="$4"
  local partition_file="${TRAIN_SOURCE}/data_partitions/${partition_name}.npy"
  local merged_ply="${out_dir}/point_cloud/iteration_${iteration}/point_cloud.ply"
  local results_json="${out_dir}/results.json"

  if ! need_file "$partition_file"; then
    run_step "partition: ${cfg}" "$PYTHON_BIN" data_partition.py --config "$cfg"
  else
    log "skip partition: ${partition_file} already exists"
  fi

  train_blocks "train_large.py" "$cfg" "$out_dir" "$iteration"

  if ! need_file "$merged_ply"; then
    run_step "merge: ${cfg}" "$PYTHON_BIN" merge.py --config "$cfg" --iteration "$iteration"
  else
    log "skip merge: ${merged_ply} already exists"
  fi

  if [[ ! -d "${out_dir}/block_all_test/ours_${iteration}/renders" ]]; then
    run_step "render: ${cfg}" \
      "$PYTHON_BIN" render_large.py --config "$cfg" --iteration "$iteration" --custom_test "$CUSTOM_TEST"
  else
    log "skip render: ${out_dir}/block_all_test/ours_${iteration}/renders already exists"
  fi

  if ! need_file "$results_json"; then
    run_step "metrics: ${out_dir}" "$PYTHON_BIN" metrics_large.py -m "$out_dir" -t block_all_test
  else
    log "skip metrics: ${results_json} already exists"
  fi

  run_filtered_eval "$out_dir" "block_all_test" "$iteration"
}

run_overlap() {
  local cfg="$1"
  local out_dir="$2"
  local iteration="$3"
  local partition_name="$4"
  local partition_file="${TRAIN_SOURCE}/data_partitions/${partition_name}.npy"
  local merged_ply="${out_dir}/point_cloud/iteration_${iteration}/point_cloud.ply"
  local results_json="${out_dir}/results.json"

  if ! need_file "$partition_file"; then
    run_step "overlap partition: ${cfg}" "$PYTHON_BIN" data_partition_overlap.py --config "$cfg"
  else
    log "skip overlap partition: ${partition_file} already exists"
  fi

  train_blocks "train_large_overlap.py" "$cfg" "$out_dir" "$iteration"

  if ! need_file "$merged_ply"; then
    run_step "overlap merge: ${cfg}" "$PYTHON_BIN" merge_overlap.py --config "$cfg" --iteration "$iteration"
  else
    log "skip overlap merge: ${merged_ply} already exists"
  fi

  if [[ ! -d "${out_dir}/block_all_test/ours_${iteration}/renders" ]]; then
    run_step "render: ${cfg}" \
      "$PYTHON_BIN" render_large.py --config "$cfg" --iteration "$iteration" --custom_test "$CUSTOM_TEST"
  else
    log "skip render: ${out_dir}/block_all_test/ours_${iteration}/renders already exists"
  fi

  if ! need_file "$results_json"; then
    run_step "metrics: ${out_dir}" "$PYTHON_BIN" metrics_large.py -m "$out_dir" -t block_all_test
  else
    log "skip metrics: ${results_json} already exists"
  fi

  run_filtered_eval "$out_dir" "block_all_test" "$iteration"
}

run_overlap config/g1_overlap15_subset_5k.yaml output/g1_overlap15_subset_5k 5000 g1_overlap15_subset_5k
run_coarse config/mc_small_aerial_subset_coarse_10k.yaml output/mc_small_aerial_subset_coarse_10k 10000
run_non_overlap config/mc_small_aerial_subset_c4_10k.yaml output/mc_small_aerial_subset_c4_10k 10000 mc_small_aerial_subset_c4_10k
run_overlap config/g1_overlap15_subset_10k.yaml output/g1_overlap15_subset_10k 10000 g1_overlap15_subset_10k
