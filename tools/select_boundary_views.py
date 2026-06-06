import argparse
import json
from pathlib import Path

import numpy as np

from projected_boundary_utils import (
    build_internal_boundaries,
    compute_crop_box,
    compute_render_size,
    contract_to_unisphere_np,
    frame_to_w2c,
    get_scaled_intrinsics,
    load_model_params,
    load_point_cloud_xyz,
    load_transforms,
    project_points,
    resolve_point_cloud_path,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Select test views where projected block boundaries are visible")
    parser.add_argument("--config", required=True, type=str)
    parser.add_argument("--test_dir", required=True, type=str)
    parser.add_argument("--output_json", required=True, type=str)
    parser.add_argument("--point_cloud", type=str, default="")
    parser.add_argument("--boundary_band", type=float, default=0.01)
    parser.add_argument("--min_side_points", type=int, default=20)
    parser.add_argument("--min_span_px", type=float, default=120.0)
    parser.add_argument("--min_depth", type=float, default=0.2)
    parser.add_argument("--crop_size", type=int, default=128)
    parser.add_argument("--padding_px", type=int, default=16)
    return parser.parse_args()


def build_boundary_point_sets(points_xyz, aabb, block_dim, boundary_band):
    contracted = contract_to_unisphere_np(points_xyz, aabb)
    point_sets = {}
    for boundary in build_internal_boundaries(block_dim):
        axis_index = 0 if boundary["axis"] == "x" else 1
        coord = contracted[:, axis_index]
        in_band = np.abs(coord - boundary["fraction"]) <= boundary_band
        neg = coord < boundary["fraction"]
        pos = coord >= boundary["fraction"]
        point_sets[boundary["id"]] = {
            "meta": boundary,
            "neg": points_xyz[in_band & neg],
            "pos": points_xyz[in_band & pos],
        }
    return point_sets


def main():
    args = parse_args()
    test_dir = Path(args.test_dir)
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    model_params = load_model_params(args.config)
    transforms = load_transforms(test_dir)
    render_w, render_h = compute_render_size(
        int(transforms["w"]),
        int(transforms["h"]),
        model_params.get("resolution", -1),
    )
    intrinsics = get_scaled_intrinsics(transforms, render_w, render_h)
    point_cloud_path = resolve_point_cloud_path(test_dir, args.point_cloud)
    point_cloud_xyz = load_point_cloud_xyz(point_cloud_path)
    point_sets = build_boundary_point_sets(
        point_cloud_xyz,
        model_params["aabb"],
        model_params["block_dim"],
        args.boundary_band,
    )

    per_view = []
    selected_images = []
    boundary_coverage = {boundary_id: 0 for boundary_id in point_sets}

    for frame_index, frame in enumerate(transforms["frames"]):
        image_name = Path(frame["file_path"]).name
        if not Path(image_name).suffix:
            image_name = f"{image_name}.png"

        w2c = frame_to_w2c(frame)
        hits = []
        for boundary_id, boundary_points in point_sets.items():
            neg_points = boundary_points["neg"]
            pos_points = boundary_points["pos"]
            neg_2d, neg_inside = project_points(
                neg_points,
                w2c,
                intrinsics,
                render_w,
                render_h,
                args.min_depth,
            )
            pos_2d, pos_inside = project_points(
                pos_points,
                w2c,
                intrinsics,
                render_w,
                render_h,
                args.min_depth,
            )

            neg_visible = neg_2d[neg_inside]
            pos_visible = pos_2d[pos_inside]
            neg_count = int(len(neg_visible))
            pos_count = int(len(pos_visible))
            if neg_count < args.min_side_points or pos_count < args.min_side_points:
                continue

            visible_points = np.concatenate([neg_visible, pos_visible], axis=0)
            axis = boundary_points["meta"]["axis"]
            span_axis = 1 if axis == "x" else 0
            span_px = float(np.ptp(visible_points[:, span_axis]))
            if span_px < args.min_span_px:
                continue

            crop = compute_crop_box(
                visible_points,
                axis,
                render_w,
                render_h,
                args.crop_size,
                args.padding_px,
            )
            boundary_coverage[boundary_id] += 1
            hits.append(
                {
                    "boundary_id": boundary_id,
                    "axis": axis,
                    "fraction": boundary_points["meta"]["fraction"],
                    "neg_visible_points": neg_count,
                    "pos_visible_points": pos_count,
                    "span_px": span_px,
                    "center_px": crop["center_px"],
                    "crop_xyxy": crop["crop_xyxy"],
                }
            )

        if hits:
            selected_images.append(image_name)

        per_view.append(
            {
                "frame_index": frame_index,
                "image_name": image_name,
                "selected": bool(hits),
                "hits": hits,
            }
        )

    result = {
        "selector": "strict_projected_boundary_v1",
        "config_path": str(Path(args.config)),
        "test_dir": str(test_dir),
        "point_cloud": str(point_cloud_path),
        "config": {
            "aabb": list(model_params["aabb"]),
            "block_dim": list(model_params["block_dim"]),
            "resolution": model_params.get("resolution", -1),
            "render_size": [render_w, render_h],
            "orig_size": [int(transforms["w"]), int(transforms["h"])],
        },
        "thresholds": {
            "boundary_band": args.boundary_band,
            "min_side_points": args.min_side_points,
            "min_span_px": args.min_span_px,
            "min_depth": args.min_depth,
            "crop_size": args.crop_size,
            "padding_px": args.padding_px,
        },
        "boundary_coverage": boundary_coverage,
        "selected_images": selected_images,
        "num_total_views": len(transforms["frames"]),
        "num_selected_views": len(selected_images),
        "per_view": per_view,
    }

    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    print(json.dumps(
        {
            "output_json": str(output_json),
            "num_selected_views": len(selected_images),
            "boundary_coverage": boundary_coverage,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
