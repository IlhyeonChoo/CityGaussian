import argparse
import json
import shutil
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import yaml
from plyfile import PlyData, PlyElement

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.general_utils import parse_cfg


def contract_to_unisphere_np(xyz: np.ndarray, aabb: list[float]) -> np.ndarray:
    aabb_array = np.asarray(aabb, dtype=np.float64)
    aabb_min = aabb_array[:3]
    aabb_max = aabb_array[3:]
    contracted = (xyz - aabb_min) / (aabb_max - aabb_min)
    contracted = contracted * 2.0 - 1.0
    mag = np.linalg.norm(contracted, ord=np.inf, axis=-1, keepdims=True)
    mask = mag[:, 0] > 1.0
    contracted[mask] = (2.0 - 1.0 / mag[mask]) * (contracted[mask] / mag[mask])
    return contracted / 4.0 + 0.5


def load_config(config_path: Path, model_path: str):
    with config_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    lp, _, _ = parse_cfg(cfg, Namespace(config=str(config_path), model_path=model_path))
    if lp.aabb is None or lp.block_dim is None:
        raise ValueError("Config must define both aabb and block_dim.")
    return lp


def write_cfg_args(config_path: Path, output_path: Path, model_path: Path, block_id: int) -> None:
    with config_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    lp, _, _ = parse_cfg(
        cfg,
        Namespace(config=str(config_path), model_path=str(model_path), block_id=block_id),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(str(Namespace(**vars(lp))))


def block_ids_for_vertices(
    vertices: np.ndarray,
    aabb: list[float],
    block_dim: list[int],
    split_space: str,
) -> np.ndarray:
    xyz = np.column_stack([vertices["x"], vertices["y"], vertices["z"]]).astype(np.float64)
    if split_space == "contracted":
        normalized = contract_to_unisphere_np(xyz, aabb)
    elif split_space == "world":
        aabb_array = np.asarray(aabb, dtype=np.float64)
        aabb_min = aabb_array[:3]
        aabb_max = aabb_array[3:]
        normalized = (xyz - aabb_min) / (aabb_max - aabb_min)
    else:
        raise ValueError(f"Unknown split space: {split_space}")

    block_x = np.floor(np.clip(normalized[:, 0] * block_dim[0], 0, block_dim[0] - 1)).astype(np.int64)
    block_y = np.floor(np.clip(normalized[:, 1] * block_dim[1], 0, block_dim[1] - 1)).astype(np.int64)
    block_z = np.floor(np.clip(normalized[:, 2] * block_dim[2], 0, block_dim[2] - 1)).astype(np.int64)
    return block_z * block_dim[0] * block_dim[1] + block_y * block_dim[0] + block_x


def write_ply(path: Path, vertices: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertices, "vertex")]).write(str(path))


def copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a merged CityGaussian PLY using a config aabb/block_dim.")
    parser.add_argument("--source-output", required=True, type=Path)
    parser.add_argument("--dest-output", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--iteration", default=30000, type=int)
    parser.add_argument("--scale", default="1.0", type=str)
    parser.add_argument("--split-space", choices=("contracted", "world"), default="contracted")
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()

    if args.dest_output.exists() and not args.allow_existing:
        raise FileExistsError(f"Destination already exists: {args.dest_output}")

    lp = load_config(args.config, str(args.dest_output))
    block_count = lp.block_dim[0] * lp.block_dim[1] * lp.block_dim[2]
    source_ply = args.source_output / "point_cloud" / f"iteration_{args.iteration}" / "point_cloud.ply"
    if not source_ply.exists():
        raise FileNotFoundError(f"Missing source PLY: {source_ply}")

    args.dest_output.mkdir(parents=True, exist_ok=args.allow_existing)
    copy_if_exists(args.source_output / "input.ply", args.dest_output / "input.ply")
    copy_if_exists(args.source_output / "cameras.json", args.dest_output / "cameras.json")
    write_cfg_args(args.config, args.dest_output / "cfg_args", args.dest_output, -1)
    dest_merged_ply = args.dest_output / "point_cloud" / f"iteration_{args.iteration}" / "point_cloud.ply"
    dest_merged_ply.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_ply, dest_merged_ply)

    vertices = PlyData.read(str(source_ply))["vertex"].data
    block_ids = block_ids_for_vertices(vertices, lp.aabb, lp.block_dim, args.split_space)

    summary = {
        "source_output": str(args.source_output),
        "source_ply": str(source_ply),
        "dest_output": str(args.dest_output),
        "config": str(args.config),
        "iteration": args.iteration,
        "aabb": lp.aabb,
        "block_dim": lp.block_dim,
        "split_space": args.split_space,
        "source_points": int(len(vertices)),
        "cells": {},
    }

    for block_id in range(block_count):
        cell_vertices = vertices[block_ids == block_id]
        cell_dir = args.dest_output / "cells" / f"cell{block_id}"
        output_ply = (
            cell_dir
            / "point_cloud_blocks"
            / f"scale_{args.scale}"
            / f"iteration_{args.iteration}"
            / "point_cloud.ply"
        )
        write_ply(output_ply, cell_vertices)
        copy_if_exists(args.source_output / "input.ply", cell_dir / "input.ply")
        copy_if_exists(args.source_output / "cameras.json", cell_dir / "cameras.json")
        write_cfg_args(args.config, cell_dir / "cfg_args", cell_dir, block_id)
        (cell_dir / "lightning_logs" / "version_0").mkdir(parents=True, exist_ok=True)
        summary["cells"][f"cell{block_id}"] = {
            "point_count": int(len(cell_vertices)),
            "point_cloud": str(output_ply),
        }

    with (args.dest_output / "split_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
