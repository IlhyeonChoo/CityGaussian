#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

apply_patch_if_needed() {
  local target_dir="$1"
  local patch_file="$2"

  if git -C "$target_dir" apply --reverse --check "$patch_file" >/dev/null 2>&1; then
    echo "Skipping already-applied patch: $patch_file"
    return 0
  fi

  if git -C "$target_dir" apply --check "$patch_file" >/dev/null 2>&1; then
    echo "Applying patch: $patch_file"
    git -C "$target_dir" apply "$patch_file"
    return 0
  fi

  echo "Patch does not apply cleanly: $patch_file" >&2
  echo "Target: $target_dir" >&2
  return 1
}

apply_patch_if_needed \
  "$repo_root/submodules/diff-gaussian-rasterization" \
  "$repo_root/third_party_patches/diff-gaussian-rasterization-cuda12.8.patch"

apply_patch_if_needed \
  "$repo_root/submodules/simple-knn" \
  "$repo_root/third_party_patches/simple-knn-cuda12.8.patch"

apply_patch_if_needed \
  "$repo_root/LargeLightGaussian" \
  "$repo_root/third_party_patches/large-light-gaussian-open-files.patch"

echo "Third-party patch application complete."
