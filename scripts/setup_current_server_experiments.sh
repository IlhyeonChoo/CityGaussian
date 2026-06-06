#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
RAW_DIR="${RAW_DIR:-/mnt/3dgs-ssd/3dgs-stage/MatrixCity/small_city/aerial}"
SUBSET_DATA_ROOT_REL="${SUBSET_DATA_ROOT_REL:-data/matrix_city/aerial_subset}"
SUBSET_DATA_ROOT="$ROOT_DIR/$SUBSET_DATA_ROOT_REL"
RUNTIME_CFG_DIR_REL="${RUNTIME_CFG_DIR_REL:-output/runtime_configs/current_server}"
RUNTIME_CFG_DIR="$ROOT_DIR/$RUNTIME_CFG_DIR_REL"
BOUNDARY_MANIFEST_REL="${BOUNDARY_MANIFEST_REL:-output/boundary_analysis/subset4_block_all_test_strict_current_server.json}"
BOUNDARY_MANIFEST="$ROOT_DIR/$BOUNDARY_MANIFEST_REL"
TRAIN_BLOCKS="${TRAIN_BLOCKS:-block_1,block_4,block_7,block_10}"
TEST_BLOCKS="${TEST_BLOCKS:-block_1_test}"
LINK_MODE="${LINK_MODE:-symlink}"
REAPPLY_PATCHES="${REAPPLY_PATCHES:-1}"

export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-12.0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export WANDB_MODE="${WANDB_MODE:-offline}"

log() {
  printf '[%s] %s\n' "$(date '+%F %T %z')" "$*"
}

require_path() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    printf 'missing required path: %s\n' "$path" >&2
    exit 1
  fi
}

render_subset_config() {
  local src="$1"
  local dest="$2"
  sed "s#data/matrix_city/aerial/train/block_all#${SUBSET_DATA_ROOT_REL}/train/block_all#g" "$src" > "$dest"
}

log "verify current server prerequisites"
require_path "$PYTHON_BIN"
require_path "$RAW_DIR"
require_path "$ROOT_DIR/output/mc_small_aerial_coarse/point_cloud/iteration_30000/point_cloud.ply"

if [[ "$REAPPLY_PATCHES" == "1" ]]; then
  log "reapply third-party patches (idempotent)"
  bash "$ROOT_DIR/scripts/apply_third_party_patches.sh"
fi

log "verify python and CUDA extension imports"
"$PYTHON_BIN" -c "import torch; import diff_gaussian_rasterization; import simple_knn._C; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'available', torch.cuda.is_available())"

log "prepare dedicated subset dataset under ${SUBSET_DATA_ROOT_REL}"
"$PYTHON_BIN" tools/prepare_matrixcity_small_aerial_v1.py \
  --raw-dir "$RAW_DIR" \
  --output-dir "$SUBSET_DATA_ROOT" \
  --train-blocks "$TRAIN_BLOCKS" \
  --test-blocks "$TEST_BLOCKS" \
  --link-mode "$LINK_MODE"

mkdir -p "$RUNTIME_CFG_DIR"

log "generate current-server runtime configs under ${RUNTIME_CFG_DIR_REL}"
render_subset_config "config/mc_small_aerial_subset_coarse_smoke.yaml" "$RUNTIME_CFG_DIR/mc_small_aerial_subset_coarse_smoke.yaml"
render_subset_config "config/mc_small_aerial_subset_c4_smoke.yaml" "$RUNTIME_CFG_DIR/mc_small_aerial_subset_c4_smoke.yaml"
render_subset_config "config/smoke_test/g1_overlap15_subset_smoke.yaml" "$RUNTIME_CFG_DIR/g1_overlap15_subset_smoke.yaml"
render_subset_config "config/mc_small_aerial_subset_coarse_5k.yaml" "$RUNTIME_CFG_DIR/mc_small_aerial_subset_coarse_5k.yaml"
render_subset_config "config/mc_small_aerial_subset_c4_5k.yaml" "$RUNTIME_CFG_DIR/mc_small_aerial_subset_c4_5k.yaml"
render_subset_config "config/g1_overlap15_subset_5k.yaml" "$RUNTIME_CFG_DIR/g1_overlap15_subset_5k.yaml"
render_subset_config "config/g2_overlap25_subset_5k.yaml" "$RUNTIME_CFG_DIR/g2_overlap25_subset_5k.yaml"
render_subset_config "config/mc_small_aerial_subset_coarse_10k.yaml" "$RUNTIME_CFG_DIR/mc_small_aerial_subset_coarse_10k.yaml"
render_subset_config "config/mc_small_aerial_subset_c4_10k.yaml" "$RUNTIME_CFG_DIR/mc_small_aerial_subset_c4_10k.yaml"
render_subset_config "config/g1_overlap15_subset_10k.yaml" "$RUNTIME_CFG_DIR/g1_overlap15_subset_10k.yaml"
render_subset_config "config/g2_overlap25_subset_10k.yaml" "$RUNTIME_CFG_DIR/g2_overlap25_subset_10k.yaml"

log "generate boundary-view manifest"
"$PYTHON_BIN" tools/select_boundary_views.py \
  --config "$RUNTIME_CFG_DIR/mc_small_aerial_subset_c4_smoke.yaml" \
  --test_dir "$SUBSET_DATA_ROOT/test/block_all_test" \
  --output_json "$BOUNDARY_MANIFEST"

cat <<EOF

Current-server experiment setup complete.

- subset dataset: ${SUBSET_DATA_ROOT_REL}
- runtime configs: ${RUNTIME_CFG_DIR_REL}
- boundary manifest: ${BOUNDARY_MANIFEST_REL}

Recommended next commands:
  bash scripts/run_subset_progression_current_server.sh
  PYTHON_BIN=.venv/bin/python bash scripts/run_overlap_experiment.sh config/g1_overlap15.yaml --max_cache_num 64
  PYTHON_BIN=.venv/bin/python bash scripts/run_overlap_experiment.sh config/g2_overlap25.yaml --max_cache_num 64

EOF
