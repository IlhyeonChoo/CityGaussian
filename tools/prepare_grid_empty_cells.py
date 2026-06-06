"""Prepare explicit empty grid cell PLYs for strict merge runs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from plyfile import PlyData


def config_model_name(config_path: Path) -> str:
    return config_path.stem


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=yaml.FullLoader)


def load_xyz(ply_path: Path) -> np.ndarray:
    ply = PlyData.read(ply_path)
    vertex = ply["vertex"].data
    return np.column_stack([vertex["x"], vertex["y"], vertex["z"]]).astype(np.float32)


def grid_aabb(xyz: np.ndarray, raw_aabb: list[float]) -> np.ndarray:
    values = np.asarray(raw_aabb, dtype=np.float32)
    if values.size == 4:
        values = np.asarray(
            [values[0], values[1], xyz[:, 2].min(), values[2], values[3], xyz[:, 2].max()],
            dtype=np.float32,
        )
    if values.size != 6:
        raise ValueError(f"Unsupported aabb length: {values.size}")
    return values


def contract_to_unisphere(xyz: np.ndarray, aabb: np.ndarray) -> np.ndarray:
    aabb_min = aabb[:3]
    aabb_max = aabb[3:]
    x = (xyz - aabb_min) / (aabb_max - aabb_min)
    x = x * 2.0 - 1.0
    mag = np.max(np.abs(x), axis=1, keepdims=True)
    mask = mag[:, 0] > 1.0
    x = x.copy()
    x[mask] = (2.0 - 1.0 / mag[mask]) * (x[mask] / mag[mask])
    return x / 4.0 + 0.5


def grid_counts(
    xyz: np.ndarray,
    block_dim: list[int],
    raw_aabb: list[float],
    padding: float,
) -> list[int]:
    aabb = grid_aabb(xyz, raw_aabb)
    contracted = contract_to_unisphere(xyz, aabb)
    dim_x, dim_y, dim_z = block_dim
    counts: list[int] = []
    for block_id in range(dim_x * dim_y * dim_z):
        block_id_z = block_id // (dim_x * dim_y)
        block_id_y = (block_id % (dim_x * dim_y)) // dim_x
        block_id_x = (block_id % (dim_x * dim_y)) % dim_x

        min_x = max(0.0, float(block_id_x) / dim_x - padding)
        max_x = min(1.0, float(block_id_x + 1) / dim_x + padding)
        min_y = max(0.0, float(block_id_y) / dim_y - padding)
        max_y = min(1.0, float(block_id_y + 1) / dim_y + padding)
        min_z = max(0.0, float(block_id_z) / dim_z - padding)
        max_z = min(1.0, float(block_id_z + 1) / dim_z + padding)

        mask = (
            (contracted[:, 0] >= min_x)
            & (contracted[:, 0] < max_x)
            & (contracted[:, 1] >= min_y)
            & (contracted[:, 1] < max_y)
            & (contracted[:, 2] >= min_z)
            & (contracted[:, 2] < max_z)
        )
        counts.append(int(mask.sum()))
    return counts


def prepare_empty_cells(
    output_path: Path,
    iteration: int,
    empty_cells: list[int],
    empty_template: Path,
    overwrite: bool,
) -> list[str]:
    copied: list[str] = []
    for cell in empty_cells:
        target = (
            output_path
            / "cells"
            / f"cell{cell}"
            / "point_cloud_blocks"
            / "scale_1.0"
            / f"iteration_{iteration}"
            / "point_cloud.ply"
        )
        if target.exists() and not overwrite:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(empty_template, target)
        copied.append(str(target))
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--output-path", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--prepare-empty-ply", action="store_true")
    parser.add_argument("--empty-template", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    model_params = cfg["model_params"]
    pretrain_path = Path(model_params["pretrain_path"])
    pretrain_ply = pretrain_path / "point_cloud.ply"
    output_path = args.output_path or Path("output") / config_model_name(args.config)
    padding = float(model_params.get("grid_pretrain_filter_padding", 0.0))

    xyz = load_xyz(pretrain_ply)
    counts = grid_counts(
        xyz=xyz,
        block_dim=list(model_params["block_dim"]),
        raw_aabb=list(model_params["aabb"]),
        padding=padding,
    )
    empty_cells = [idx for idx, count in enumerate(counts) if count == 0]

    copied: list[str] = []
    if args.prepare_empty_ply and empty_cells:
        if args.empty_template is None:
            raise ValueError("--empty-template is required when preparing empty PLYs.")
        copied = prepare_empty_cells(
            output_path=output_path,
            iteration=args.iteration,
            empty_cells=empty_cells,
            empty_template=args.empty_template,
            overwrite=args.overwrite,
        )

    result = {
        "config": str(args.config),
        "output_path": str(output_path),
        "pretrain_ply": str(pretrain_ply),
        "total_pretrain_gaussians": int(xyz.shape[0]),
        "padding": padding,
        "counts": counts,
        "empty_cells": empty_cells,
        "prepared_empty_plys": copied,
    }

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
