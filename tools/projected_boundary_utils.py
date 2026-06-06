import json
import math
from pathlib import Path

import numpy as np
import yaml
from plyfile import PlyData


def load_model_params(config_path):
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return config["model_params"]


def normalize_block_dim(block_dim):
    values = list(block_dim)
    if len(values) == 2:
        values.append(1)
    if len(values) != 3:
        raise ValueError(f"block_dim must have 2 or 3 entries, got {block_dim}")
    return [int(value) for value in values]


def compute_render_size(orig_w, orig_h, resolution):
    if resolution in [1, 2, 4, 8]:
        return round(orig_w / resolution), round(orig_h / resolution)

    if resolution == -1:
        global_down = orig_w / 1600 if orig_w > 1600 else 1
    else:
        global_down = orig_w / float(resolution)

    scale = float(global_down)
    return int(orig_w / scale), int(orig_h / scale)


def load_transforms(test_dir):
    test_dir = Path(test_dir)
    with (test_dir / "transforms.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_point_cloud_path(test_dir, explicit_path=""):
    if explicit_path:
        point_cloud = Path(explicit_path)
    else:
        prep_summary_path = Path(test_dir).parents[1] / "prep_summary.json"
        with prep_summary_path.open("r", encoding="utf-8") as handle:
            prep_summary = json.load(handle)
        point_cloud = Path(prep_summary["test"]["point_cloud"])

    if not point_cloud.exists():
        raise FileNotFoundError(f"Point cloud not found: {point_cloud}")
    return point_cloud


def load_point_cloud_xyz(point_cloud_path):
    vertices = PlyData.read(str(point_cloud_path))["vertex"]
    return np.vstack([vertices["x"], vertices["y"], vertices["z"]]).T.astype(np.float32)


def contract_to_unisphere_np(points, aabb):
    aabb = np.asarray(aabb, dtype=np.float32)
    aabb_min, aabb_max = aabb[:3], aabb[3:]
    points = (points - aabb_min) / (aabb_max - aabb_min)
    points = points * 2.0 - 1.0
    magnitude = np.max(np.abs(points), axis=-1, keepdims=True)
    mask = magnitude[:, 0] > 1.0
    contracted = points.copy()
    contracted[mask] = (2.0 - 1.0 / magnitude[mask]) * (contracted[mask] / magnitude[mask])
    return contracted / 4.0 + 0.5


def build_internal_boundaries(block_dim):
    block_dim = normalize_block_dim(block_dim)
    boundaries = []
    for axis_name, axis_size in zip(["x", "y"], block_dim[:2]):
        for index in range(1, axis_size):
            fraction = index / axis_size
            boundaries.append(
                {
                    "id": f"{axis_name}_{fraction:.4f}",
                    "axis": axis_name,
                    "fraction": float(fraction),
                }
            )
    return boundaries


def get_scaled_intrinsics(transforms, render_w, render_h):
    orig_w = float(transforms["w"])
    orig_h = float(transforms["h"])
    scale_x = render_w / orig_w
    scale_y = render_h / orig_h

    if "fl_x" in transforms:
        fx = float(transforms["fl_x"]) * scale_x
    else:
        fx = render_w / (2.0 * math.tan(float(transforms["camera_angle_x"]) / 2.0))

    if "fl_y" in transforms:
        fy = float(transforms["fl_y"]) * scale_y
    else:
        fy = fx

    cx = float(transforms.get("cx", orig_w / 2.0)) * scale_x
    cy = float(transforms.get("cy", orig_h / 2.0)) * scale_y

    return {
        "fx": fx,
        "fy": fy,
        "cx": cx,
        "cy": cy,
    }


def frame_to_w2c(frame):
    c2w = np.array(frame["transform_matrix"], dtype=np.float32)
    c2w = c2w.copy()
    c2w[:3, 1:3] *= -1.0
    return np.linalg.inv(c2w)


def project_points(points_xyz, w2c, intrinsics, render_w, render_h, min_depth):
    if len(points_xyz) == 0:
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=bool)

    points_h = np.concatenate(
        [points_xyz, np.ones((len(points_xyz), 1), dtype=np.float32)],
        axis=1,
    )
    camera_points = points_h @ w2c.T
    z = camera_points[:, 2]
    valid_depth = z > min_depth

    x = (camera_points[:, 0] / np.maximum(z, 1e-6)) * intrinsics["fx"] + intrinsics["cx"]
    y = (-camera_points[:, 1] / np.maximum(z, 1e-6)) * intrinsics["fy"] + intrinsics["cy"]

    inside = (
        valid_depth
        & (x >= 0.0)
        & (x < render_w)
        & (y >= 0.0)
        & (y < render_h)
    )
    return np.stack([x, y], axis=1), inside


def clamp_interval(start, end, limit, min_size):
    start = float(start)
    end = float(end)
    if end - start < min_size:
        center = 0.5 * (start + end)
        start = center - min_size / 2.0
        end = center + min_size / 2.0

    if start < 0.0:
        end -= start
        start = 0.0
    if end > limit:
        start -= end - limit
        end = float(limit)

    start = max(0.0, start)
    end = min(float(limit), end)
    if end - start < min_size and limit >= min_size:
        if start <= 0.0:
            end = min(float(limit), min_size)
        else:
            start = max(0.0, float(limit) - min_size)

    return start, end


def compute_crop_box(points_2d, axis, render_w, render_h, crop_size, padding_px):
    line_center_x = float(np.median(points_2d[:, 0]))
    line_center_y = float(np.median(points_2d[:, 1]))

    if axis == "x":
        left = line_center_x - crop_size / 2.0
        right = line_center_x + crop_size / 2.0
        top = float(points_2d[:, 1].min()) - padding_px
        bottom = float(points_2d[:, 1].max()) + padding_px
        left, right = clamp_interval(left, right, render_w, crop_size)
        top, bottom = clamp_interval(top, bottom, render_h, crop_size)
    elif axis == "y":
        left = float(points_2d[:, 0].min()) - padding_px
        right = float(points_2d[:, 0].max()) + padding_px
        top = line_center_y - crop_size / 2.0
        bottom = line_center_y + crop_size / 2.0
        left, right = clamp_interval(left, right, render_w, crop_size)
        top, bottom = clamp_interval(top, bottom, render_h, crop_size)
    else:
        raise ValueError(f"Unsupported axis: {axis}")

    return {
        "center_px": [line_center_x, line_center_y],
        "crop_xyxy": [
            int(round(left)),
            int(round(top)),
            int(round(right)),
            int(round(bottom)),
        ],
    }
