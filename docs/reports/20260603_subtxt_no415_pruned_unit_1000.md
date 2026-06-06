# 2026-06-03 Subtxt No415 Pruned Unit 1000-Iteration Smoke

## Current Goal

Run the `sub.txt` single-owner no-415 room/passage partition for 1000
iterations per block so densification and train-time unit bounds pruning are
both exercised.

## Config

- Smoke config: `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000.yaml`
- Source scene: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Partition name: `scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units`

## Exact Command

```bash
CONFIG=smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000 \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=5 \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
```

## Output

- Output directory: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000`
- Merged PLY: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_1000/point_cloud/iteration_1000/point_cloud.ply`
- Log: `/tmp/smoke_subtxt_pruned_units_1000.log`

## Results

- 1000-iteration block PLYs: `10 / 10`
- Merged vertices: `1179565`
- Merged PLY size: `279M`
- Output directory size: `596M`
- Error patterns: no `Traceback`, `ValueError`, `FileNotFound`, or `Training failed`

## Train-Time Bounds Prune

- Prune events by block: `{0: 4, 1: 4, 2: 5, 3: 5, 4: 5, 5: 5, 6: 4, 7: 4, 8: 4, 9: 5}`
- Pruned total by block: `{0: 79, 1: 76, 2: 66, 3: 91, 4: 68, 5: 71, 6: 89, 7: 24, 8: 44, 9: 34}`
- Total pruned gaussians: `642`

## Merge Counts

- block 0: `72992`
- block 1: `74067`
- block 2: `145090`
- block 3: `147794`
- block 4: `135819`
- block 5: `104038`
- block 6: `216328`
- block 7: `88994`
- block 8: `89897`
- block 9: `104546`

## Remaining Risk

This run validates the 1000-iteration training, densification, train-time bounds
pruning, strict per-block save, and strict merge path. Visual quality still
needs render inspection before using this setting as the 30k run baseline.
