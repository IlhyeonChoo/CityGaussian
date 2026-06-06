# 2026-06-03 Subtxt No415 Pruned Unit Smoke

## Current Goal

Rebuild the no-415 room/passage unit partition from `sub.txt`, constrain
train-time Gaussian growth with unit bounds pruning, and validate the new path
with a 100-iteration smoke run.

## Config

- Full config: `config/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units.yaml`
- Smoke config: `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_100.yaml`
- Source scene: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Point source: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416`
- Range file: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub.txt`

## Exact Command

```bash
CONFIG=smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_100 \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=5 \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
```

## Output

- Output directory: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_100`
- Merged PLY: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_no415_pruned_units_100/point_cloud/iteration_100/point_cloud.ply`
- Log: `/tmp/smoke_subtxt_pruned_units.log`

## Results

- Partition shape: `(6580, 10)`
- Unit order: `401, 404, 409, 411, 412, 413, 414, passage1, passage2, passage3`
- Camera counts: `[395, 379, 906, 789, 568, 465, 644, 666, 394, 695]`
- Unassigned cameras: `679`
- Multi-unit cameras: `0`
- Multi-unit core points: `0`
- Multi-unit points: `29608`
- Unassigned core points: `216821`
- 100-iteration block PLYs: `10 / 10`
- Merged vertices: `1053305`
- Merged PLY size: `250M`

## Validation

```bash
.venv/bin/python -m py_compile \
  tools/create_colmap_unit_partition.py scene/__init__.py train_large.py \
  merge.py arguments/__init__.py utils/general_utils.py

bash -n scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
```

Partition assertions passed:

- `cam.shape == (6580, 10)`
- no multi-unit camera assignment
- expected unit order
- no multi-unit core point assignment

## Remaining Risk

This validates data flow, partition generation, train-time prune calls, strict
merge, and artifact creation. Visual quality still needs render inspection for
room-only, passage-only, and room+passage combinations before starting a long
30k run.
