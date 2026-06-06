# 2026-06-03 Subtxt Manual Passage No415 Pruned Unit 1000

## Current Goal

Apply the manual passage split requested after the first 1000-iteration run and
validate it with a 1000-iteration smoke run.

## Manual Passage Split

- `passage2`: `000000 ~ 000515`, `005110 ~ 005124`
- `passage3`: `005125 ~ 005131`, `005700 ~ 005800`, `006595 ~ 006747`, `007480 ~ 007520`, `008510 ~ 008991`
- `passage1`: remaining global passage ranges from `sub.txt`

Frame `005125` is assigned to `passage3` to keep single-owner partitioning.

## Config

- Range file: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt`
- Full config: `config/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units.yaml`
- Smoke config: `config/smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000.yaml`
- Source scene: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416_filtered`
- Point source: `data/W2_4_3_merge_rooms_with_passage_v3_undistorted/combined_no_405_410_416`

## Exact Command

```bash
CONFIG=smoke_test/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000 \
RANGE_FILE=data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt \
GPU_RETRY_SECONDS=10 \
START_DELAY_SECONDS=5 \
./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh
```

## Output

- Output directory: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000`
- Merged PLY: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_1000/point_cloud/iteration_1000/point_cloud.ply`
- Log: `/tmp/smoke_subtxt_passage_manual_no415_1000.log`

## Results

- Partition shape: `(6580, 10)`
- Unit order: `401, 404, 409, 411, 412, 413, 414, passage1, passage2, passage3`
- Camera counts: `[395, 379, 906, 789, 568, 465, 644, 476, 512, 767]`
- Unassigned cameras: `679`
- Multi-unit cameras: `0`
- Multi-unit points: `8639`
- Multi-unit core points: `0`
- 1000-iteration block PLYs: `10 / 10`
- Merged vertices: `1199072`
- Merged PLY size: `284M`

## Actual Passage Assignments

`passage1`: `000940~000970`, `001375~001405`, `001613~001640`,
`002045~002084`, `002735~002840`, `003520~003522`,
`003525~003553`, `003555~003640`, `004285~004335`,
`004337~004364`, `004366~004372`, `004375~004410`.

`passage2`: `000000~000480`, `000497~000512`, `005110~005124`.

`passage3`: `005125~005131`, `005700~005701`, `005703~005759`,
`005762~005800`, `006595~006623`, `006625~006717`,
`006719~006747`, `007480~007520`, `008510~008531`,
`008534~008570`, `008572~008641`, `008644~008734`,
`008738~008823`, `008825~008871`, `008874~008901`,
`008903~008991`.

Missing frame numbers inside the requested ranges are absent from the COLMAP
image table, so they do not appear in the final partition rows.

## Remaining Risk

This validates the custom assignment, point/core-point regeneration,
train-time bounds pruning, and strict merge. Visual render inspection is still
needed before choosing this split for a 30k run.
