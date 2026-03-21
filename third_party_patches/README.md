# Third-Party Patches

This directory stores local patches that must be reapplied on top of upstream
submodule revisions to reproduce the current working environment.

Tracked patches:

- `diff-gaussian-rasterization-cuda12.8.patch`
  - Target: `submodules/diff-gaussian-rasterization`
  - Purpose: local CUDA 12.8 build compatibility adjustment
- `simple-knn-cuda12.8.patch`
  - Target: `submodules/simple-knn`
  - Purpose: local CUDA 12.8 build compatibility adjustment
- `large-light-gaussian-open-files.patch`
  - Target: `LargeLightGaussian`
  - Purpose: avoid open file descriptor accumulation in image loading paths

Usage:

```bash
./scripts/apply_third_party_patches.sh
```

Notes:

- The script is idempotent. It skips patches that are already applied.
- Apply these patches after `git submodule update --init --recursive`.
- Build artifacts such as `build/` and `*.egg-info/` are not preserved here.
