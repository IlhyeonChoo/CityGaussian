# Filtered No415 Passage3 Unit 100-Iteration Smoke

## Goal

Validate the COLMAP-unit partition workflow on the previously filtered
`combined_no_405_410_416_filtered` scene, excluding `415_passage_v3` and
splitting shared corridor cameras into `passage1`, `passage2`, and `passage3`.

## Config

- Full-run config:
  `config/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_no415_passage3_units.yaml`
- 100-iteration config:
  `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_no415_passage3_units_100.yaml`
- Orchestration script:
  `scripts/run_colmap_unit_citygs_filtered_no415_passage3.sh`

## Data Cleanup

- Source scene:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Point-track source:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416`
- Point filter box:
  `[-12.0, -4.0, -14.0, 12.0, 7.0, 8.0]`
- Excluded unit source:
  `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/415_passage_v3`

Generated partition:

```bash
.venv/bin/python tools/create_colmap_unit_partition.py \
  --source-path data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered \
  --partition-name scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_no415_passage3_units \
  --unit-paths \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/401_passage_v3 \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/404_passage_v3 \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/409_passage_v3 \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/411_passage_v3 \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/412_passage_v3 \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/413_passage_v3 \
    data/W2_4_3_merge_rooms_with_passage_v3_undistorted/414_passage_v3 \
  --shared-camera-policy split \
  --passage-splits 3 \
  --passage-prefix passage \
  --camera-outlier-filter robust \
  --camera-outlier-z-threshold 8.0 \
  --camera-outlier-min-distance 5.0 \
  --camera-outlier-distance-ratio 4.0 \
  --point-source-path data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416 \
  --point-filter-box -12.0 -4.0 -14.0 12.0 7.0 8.0 \
  --validate-point-cloud-length \
  --overwrite
```

## Execution

100-iteration block training:

```bash
set -e
for block_id in $(seq 0 9); do
  CUDA_VISIBLE_DEVICES=0 WANDB_MODE=offline .venv/bin/python train_large.py \
    --config config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_no415_passage3_units_100.yaml \
    --block_id "$block_id" \
    --port $((6500 + block_id)) \
    --max_cache_num 1 \
    --quiet
done
```

Merge:

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python merge.py \
  --config config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_no415_passage3_units_100.yaml \
  --iteration 100
```

## Results

- Partition images: `6,580`
- Partition points: `1,274,646`
- Original point source count: `1,278,351`
- Filtered point count: `1,274,646`
- Excluded camera outliers after filtered source cleanup: `1`
  (`frame_008548.png`)
- Unassigned cameras: `741` (`740` from excluded `415`, plus one outlier)
- Per-block normalization radius after partition filtering: `1.474271` to
  `9.527863`

Merged output:

- Path:
  `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_no415_passage3_units_100/point_cloud/iteration_100/point_cloud.ply`
- Merged point count: `1,101,713`
- File size: `261M`
- Merged xyz min: `[-11.048763, -3.749738, -10.285385]`
- Merged xyz max: `[6.805228, 5.148762, 7.994670]`

Per-block merged point counts:

| Block | Unit | Points |
|---:|---|---:|
| 0 | `401_passage_v3` | 51,949 |
| 1 | `404_passage_v3` | 54,631 |
| 2 | `409_passage_v3` | 139,484 |
| 3 | `411_passage_v3` | 130,348 |
| 4 | `412_passage_v3` | 110,873 |
| 5 | `413_passage_v3` | 90,813 |
| 6 | `414_passage_v3` | 202,165 |
| 7 | `passage1` | 129,739 |
| 8 | `passage2` | 103,617 |
| 9 | `passage3` | 88,094 |

## Validation

- `py_compile` passed for:
  `tools/create_colmap_unit_partition.py`, `scene/dataset_readers.py`,
  `scene/__init__.py`, `arguments/__init__.py`, `utils/general_utils.py`
- `bash -n` passed for:
  `scripts/run_colmap_unit_citygs_filtered_no415_passage3.sh`
- 100-iteration training completed for all 10 blocks.
- Merge completed for `iteration_100`.
- GPU was idle after completion.

## Remaining Risk

This is still a 100-iteration smoke, not a quality validation of a 30k run.
The filtered source and partition-after-normalization fix remove the known raw
camera-scale failure mode, and the point filter removes the large raw
points3D outliers seen in the original source.
