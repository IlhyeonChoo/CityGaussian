import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from plyfile import PlyData, PlyElement


def parse_groups(raw_groups: str) -> list[list[int]]:
    groups = []
    for raw_group in raw_groups.split(";"):
        group = [int(item.strip()) for item in raw_group.split(",") if item.strip()]
        if not group:
            raise ValueError("Empty cell group is not allowed.")
        groups.append(group)
    return groups


def read_vertices(path: Path) -> np.ndarray:
    ply = PlyData.read(str(path))
    return ply["vertex"].data


def write_vertices(path: Path, vertices: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertices, "vertex")]).write(str(path))


def concatenate_plys(paths: list[Path], output_path: Path) -> int:
    arrays = [read_vertices(path) for path in paths]
    dtype = arrays[0].dtype
    if any(array.dtype != dtype for array in arrays):
        raise ValueError("Cannot concatenate PLY files with different vertex dtypes.")
    vertices = np.concatenate(arrays)
    write_vertices(output_path, vertices)
    return len(vertices)


def load_cameras(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_group_cameras(source_dir: Path, group: list[int], output_path: Path) -> int:
    cameras_by_name = {}
    for cell_id in group:
        cameras = load_cameras(source_dir / "cells" / f"cell{cell_id}" / "cameras.json")
        for camera in cameras:
            cameras_by_name[camera["img_name"]] = camera

    grouped_cameras = [cameras_by_name[name] for name in sorted(cameras_by_name)]
    for idx, camera in enumerate(grouped_cameras):
        camera["id"] = idx

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(grouped_cameras, handle, indent=2)
    return len(grouped_cameras)


def copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def discover_iterations(source_dir: Path, groups: list[list[int]]) -> list[int]:
    common_iterations = None
    for group in groups:
        for cell_id in group:
            scale_dir = source_dir / "cells" / f"cell{cell_id}" / "point_cloud_blocks" / "scale_1.0"
            iterations = {
                int(path.name.split("_")[-1])
                for path in scale_dir.iterdir()
                if path.is_dir() and path.name.startswith("iteration_")
            }
            common_iterations = iterations if common_iterations is None else common_iterations & iterations
    if not common_iterations:
        raise FileNotFoundError("No common cell iterations found across all source groups.")
    return sorted(common_iterations)


def group_partition(source_partition: Path, destination_partition: Path, groups: list[list[int]]) -> None:
    if not source_partition.exists():
        return
    mask = np.load(source_partition)
    grouped_mask = np.zeros((mask.shape[0], len(groups)), dtype=bool)
    for group_id, group in enumerate(groups):
        grouped_mask[:, group_id] = mask[:, group].any(axis=1)
    destination_partition.parent.mkdir(parents=True, exist_ok=True)
    np.save(destination_partition, grouped_mask)


def main() -> None:
    parser = argparse.ArgumentParser(description="Group trained CityGaussian cell PLYs into larger cells.")
    parser.add_argument("--source-output", required=True, type=Path)
    parser.add_argument("--dest-output", required=True, type=Path)
    parser.add_argument("--groups", required=True, type=str)
    parser.add_argument("--iterations", nargs="*", type=int, default=None)
    parser.add_argument("--source-partition", type=Path, default=None)
    parser.add_argument("--dest-partition", type=Path, default=None)
    args = parser.parse_args()

    if args.dest_output.exists():
        raise FileExistsError(f"Destination already exists: {args.dest_output}")

    groups = parse_groups(args.groups)
    iterations = args.iterations or discover_iterations(args.source_output, groups)

    args.dest_output.mkdir(parents=True)
    copy_if_exists(args.source_output / "input.ply", args.dest_output / "input.ply")
    copy_if_exists(args.source_output / "cameras.json", args.dest_output / "cameras.json")

    summary = {
        "source_output": str(args.source_output),
        "dest_output": str(args.dest_output),
        "groups": groups,
        "iterations": iterations,
        "cells": {},
    }

    for new_cell_id, group in enumerate(groups):
        cell_dir = args.dest_output / "cells" / f"cell{new_cell_id}"
        cell_dir.mkdir(parents=True, exist_ok=True)
        copy_if_exists(args.source_output / "input.ply", cell_dir / "input.ply")
        camera_count = write_group_cameras(args.source_output, group, cell_dir / "cameras.json")
        summary["cells"][f"cell{new_cell_id}"] = {
            "source_cells": group,
            "camera_count": camera_count,
            "iterations": {},
        }

        for iteration in iterations:
            input_paths = [
                args.source_output
                / "cells"
                / f"cell{source_cell_id}"
                / "point_cloud_blocks"
                / "scale_1.0"
                / f"iteration_{iteration}"
                / "point_cloud.ply"
                for source_cell_id in group
            ]
            output_path = (
                cell_dir
                / "point_cloud_blocks"
                / "scale_1.0"
                / f"iteration_{iteration}"
                / "point_cloud.ply"
            )
            point_count = concatenate_plys(input_paths, output_path)
            summary["cells"][f"cell{new_cell_id}"]["iterations"][str(iteration)] = point_count

    for iteration in iterations:
        grouped_paths = [
            args.dest_output
            / "cells"
            / f"cell{cell_id}"
            / "point_cloud_blocks"
            / "scale_1.0"
            / f"iteration_{iteration}"
            / "point_cloud.ply"
            for cell_id in range(len(groups))
        ]
        merged_path = args.dest_output / "point_cloud" / f"iteration_{iteration}" / "point_cloud.ply"
        summary.setdefault("merged", {})[str(iteration)] = concatenate_plys(grouped_paths, merged_path)

    if args.source_partition and args.dest_partition:
        group_partition(args.source_partition, args.dest_partition, groups)
        summary["source_partition"] = str(args.source_partition)
        summary["dest_partition"] = str(args.dest_partition)

    with (args.dest_output / "grouping.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
