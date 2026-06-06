import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from plyfile import PlyData
from scipy.spatial import cKDTree


def load_model_params(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    return dict(cfg.get("model_params", {}))


def expand_bounds(bounds: np.ndarray, margin: float, margin_ratio: float) -> np.ndarray:
    bounds = np.asarray(bounds, dtype=np.float64)
    bounds_min = bounds[:3]
    bounds_max = bounds[3:]
    extent = np.maximum(bounds_max - bounds_min, 1e-6)
    padding = margin + extent * margin_ratio
    return np.concatenate([bounds_min - padding, bounds_max + padding])


def bounds_mask(xyz: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    bounds = np.asarray(bounds, dtype=xyz.dtype)
    bounds_min = bounds[:3]
    bounds_max = bounds[3:]
    return (
        (xyz[:, 0] >= bounds_min[0])
        & (xyz[:, 0] <= bounds_max[0])
        & (xyz[:, 1] >= bounds_min[1])
        & (xyz[:, 1] <= bounds_max[1])
        & (xyz[:, 2] >= bounds_min[2])
        & (xyz[:, 2] <= bounds_max[2])
    )


def aabb_intersects(lhs: np.ndarray, rhs: np.ndarray, padding: float = 0.0) -> bool:
    lhs_min = lhs[:3] - padding
    lhs_max = lhs[3:] + padding
    rhs_min = rhs[:3] - padding
    rhs_max = rhs[3:] + padding
    return bool(np.all(lhs_min <= rhs_max) and np.all(rhs_min <= lhs_max))


def aabb_overlap_volume(lhs: np.ndarray, rhs: np.ndarray) -> float:
    overlap_min = np.maximum(lhs[:3], rhs[:3])
    overlap_max = np.minimum(lhs[3:], rhs[3:])
    extent = np.maximum(overlap_max - overlap_min, 0.0)
    return float(np.prod(extent))


def read_vertices(path: Path) -> np.ndarray:
    return PlyData.read(str(path))["vertex"].data


def vertex_xyz(vertices: np.ndarray) -> np.ndarray:
    return np.column_stack([vertices["x"], vertices["y"], vertices["z"]]).astype(np.float64)


def scale_stats(vertices: np.ndarray) -> dict[str, float] | None:
    scale_names = sorted(name for name in vertices.dtype.names or () if name.startswith("scale_"))
    if not scale_names:
        return None
    log_scales = np.column_stack([vertices[name] for name in scale_names]).astype(np.float64)
    max_scales = np.exp(np.max(log_scales, axis=1))
    return {
        "mean_max_scale": float(np.mean(max_scales)),
        "p50_max_scale": float(np.percentile(max_scales, 50.0)),
        "p95_max_scale": float(np.percentile(max_scales, 95.0)),
        "p99_max_scale": float(np.percentile(max_scales, 99.0)),
        "max_max_scale": float(np.max(max_scales)),
    }


def sample_xyz(xyz: np.ndarray, sample_size: int, rng: np.random.Generator) -> np.ndarray:
    if sample_size <= 0 or len(xyz) <= sample_size:
        return xyz
    indices = rng.choice(len(xyz), size=sample_size, replace=False)
    return xyz[indices]


def close_fraction(
    source_xyz: np.ndarray,
    target_tree: cKDTree,
    threshold: float,
) -> float:
    if len(source_xyz) == 0:
        return 0.0
    distances, _ = target_tree.query(source_xyz, k=1, distance_upper_bound=threshold, workers=-1)
    return float(np.isfinite(distances).mean())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze per-unit Gaussian bounds leakage and cross-unit center overlap."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--scale", default="1.0")
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=[0.05, 0.1, 0.2],
        help="World-space nearest-neighbor distance thresholds.",
    )
    parser.add_argument(
        "--sample-per-unit",
        type=int,
        default=100000,
        help="Deterministic per-unit sample size for pairwise nearest-neighbor checks. Use 0 for all points.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--write-json", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_params = load_model_params(args.config)
    source_path = Path(model_params["source_path"])
    partition_name = model_params["partition_name"]
    margin = float(model_params.get("unit_aabb_margin", 0.0))
    margin_ratio = float(model_params.get("unit_aabb_margin_ratio", 0.02))

    partition_base = source_path / "data_partitions" / partition_name
    bounds = np.load(f"{partition_base}_bounds.npy").astype(np.float64)
    with Path(f"{partition_base}_units.json").open("r", encoding="utf-8") as handle:
        units = json.load(handle)

    rng = np.random.default_rng(args.seed)
    unit_records = []
    xyz_by_unit = []
    sampled_xyz_by_unit = []

    for unit in units:
        unit_id = int(unit["id"])
        ply_path = (
            args.output
            / "cells"
            / f"cell{unit_id}"
            / "point_cloud_blocks"
            / f"scale_{args.scale}"
            / f"iteration_{args.iteration}"
            / "point_cloud.ply"
        )
        if not ply_path.exists():
            raise FileNotFoundError(f"Missing unit PLY: {ply_path}")

        vertices = read_vertices(ply_path)
        xyz = vertex_xyz(vertices)
        raw_bounds = bounds[unit_id]
        expanded_bounds = expand_bounds(raw_bounds, margin, margin_ratio)
        inside_raw = bounds_mask(xyz, raw_bounds)
        inside_expanded = bounds_mask(xyz, expanded_bounds)
        actual_bounds = np.concatenate([xyz.min(axis=0), xyz.max(axis=0)])

        xyz_by_unit.append(xyz)
        sampled_xyz_by_unit.append(sample_xyz(xyz, args.sample_per_unit, rng))
        unit_records.append(
            {
                "id": unit_id,
                "name": unit["name"],
                "point_count": int(len(xyz)),
                "raw_bounds": raw_bounds.tolist(),
                "expanded_bounds": expanded_bounds.tolist(),
                "actual_bounds": actual_bounds.tolist(),
                "inside_raw_count": int(inside_raw.sum()),
                "inside_raw_ratio": float(inside_raw.mean()) if len(xyz) else 0.0,
                "outside_expanded_count": int((~inside_expanded).sum()),
                "outside_expanded_ratio": float((~inside_expanded).mean()) if len(xyz) else 0.0,
                "scale_stats": scale_stats(vertices),
            }
        )

    trees = [cKDTree(xyz) for xyz in xyz_by_unit]
    thresholds = sorted(float(item) for item in args.thresholds)
    max_threshold = thresholds[-1] if thresholds else 0.0
    pair_records = []

    for left_id in range(len(units)):
        for right_id in range(left_id + 1, len(units)):
            left_bounds = np.asarray(unit_records[left_id]["expanded_bounds"], dtype=np.float64)
            right_bounds = np.asarray(unit_records[right_id]["expanded_bounds"], dtype=np.float64)
            intersects = aabb_intersects(left_bounds, right_bounds)
            if not aabb_intersects(left_bounds, right_bounds, padding=max_threshold):
                continue

            threshold_records = {}
            for threshold in thresholds:
                left_to_right = close_fraction(sampled_xyz_by_unit[left_id], trees[right_id], threshold)
                right_to_left = close_fraction(sampled_xyz_by_unit[right_id], trees[left_id], threshold)
                threshold_records[str(threshold)] = {
                    "left_sample_close_ratio": left_to_right,
                    "right_sample_close_ratio": right_to_left,
                    "mean_sample_close_ratio": (left_to_right + right_to_left) / 2.0,
                }

            pair_records.append(
                {
                    "left_id": left_id,
                    "left_name": units[left_id]["name"],
                    "right_id": right_id,
                    "right_name": units[right_id]["name"],
                    "expanded_aabb_intersects": intersects,
                    "expanded_aabb_overlap_volume": aabb_overlap_volume(left_bounds, right_bounds),
                    "thresholds": threshold_records,
                }
            )

    top_threshold = str(max_threshold)
    pair_records.sort(
        key=lambda record: record["thresholds"][top_threshold]["mean_sample_close_ratio"],
        reverse=True,
    )

    merged_ply = args.output / "point_cloud" / f"iteration_{args.iteration}" / "point_cloud.ply"
    merged_count = None
    if merged_ply.exists():
        merged_count = int(len(read_vertices(merged_ply)))

    report = {
        "config": str(args.config),
        "output": str(args.output),
        "iteration": args.iteration,
        "source_path": str(source_path),
        "partition_name": partition_name,
        "margin": margin,
        "margin_ratio": margin_ratio,
        "thresholds": thresholds,
        "sample_per_unit": args.sample_per_unit,
        "unit_count": len(units),
        "cell_point_total": int(sum(record["point_count"] for record in unit_records)),
        "merged_point_count": merged_count,
        "units": unit_records,
        "pairs_checked": len(pair_records),
        "pairs": pair_records,
    }

    print("Unit bounds summary")
    for record in unit_records:
        scale = record["scale_stats"] or {}
        print(
            f"- cell{record['id']} {record['name']}: "
            f"points={record['point_count']} "
            f"inside_raw={record['inside_raw_ratio']:.3f} "
            f"outside_expanded={record['outside_expanded_count']} "
            f"p95_scale={scale.get('p95_max_scale', float('nan')):.4f}"
        )

    print(f"\nTop cross-unit close pairs at threshold {max_threshold}")
    for record in pair_records[:10]:
        stats = record["thresholds"][top_threshold]
        print(
            f"- {record['left_name']} <-> {record['right_name']}: "
            f"mean={stats['mean_sample_close_ratio']:.3f} "
            f"left={stats['left_sample_close_ratio']:.3f} "
            f"right={stats['right_sample_close_ratio']:.3f} "
            f"aabb_overlap={record['expanded_aabb_overlap_volume']:.3f}"
        )

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        with args.write_json.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print(f"\nWrote {args.write_json}")


if __name__ == "__main__":
    main()
