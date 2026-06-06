import argparse
import json
from pathlib import Path

import torch
import torchvision.transforms.functional as tf
from PIL import Image

from lpipsPyTorch import lpips
from boundary_crop import (
    build_boundaries,
    crop_boundary_strips,
    infer_block_dim_from_cfg_args,
    parse_fraction_list,
    parse_grid_block_dim,
)


def resolve_render_dirs(output_dir, test_set, iteration):
    output_dir = Path(output_dir)
    test_dir = output_dir / test_set
    if iteration > 0:
        method_dir = test_dir / f"ours_{iteration}"
    else:
        candidates = sorted(
            [path for path in test_dir.iterdir() if path.is_dir() and path.name.startswith("ours_")],
            key=lambda path: int(path.name.split("_")[-1]),
        )
        if not candidates:
            raise FileNotFoundError(f"No rendered methods found in {test_dir}")
        method_dir = candidates[-1]
    return method_dir / "renders", method_dir / "gt", method_dir


def to_tensor(image):
    return tf.to_tensor(image).unsqueeze(0)[:, :3, :, :].cuda()


def main():
    parser = argparse.ArgumentParser(description="Evaluate LPIPS on boundary strips")
    parser.add_argument("--output_dir", type=str, default="")
    parser.add_argument("--pred_dir", type=str, default="")
    parser.add_argument("--gt_dir", type=str, default="")
    parser.add_argument("--test_set", type=str, default="test")
    parser.add_argument("--iteration", type=int, default=-1)
    parser.add_argument("--crop_size", type=int, default=128)
    parser.add_argument("--x_boundaries", type=str, default="")
    parser.add_argument("--y_boundaries", type=str, default="")
    parser.add_argument("--grid_block_dim", type=str, default="")
    args = parser.parse_args()

    if args.output_dir:
        pred_dir, gt_dir, method_dir = resolve_render_dirs(args.output_dir, args.test_set, args.iteration)
        grid_block_dim = parse_grid_block_dim(args.grid_block_dim) or infer_block_dim_from_cfg_args(args.output_dir)
    else:
        if not args.pred_dir or not args.gt_dir:
            raise ValueError("Either --output_dir or both --pred_dir and --gt_dir are required.")
        pred_dir = Path(args.pred_dir)
        gt_dir = Path(args.gt_dir)
        method_dir = pred_dir.parent
        grid_block_dim = parse_grid_block_dim(args.grid_block_dim)

    x_boundaries = parse_fraction_list(args.x_boundaries)
    y_boundaries = parse_fraction_list(args.y_boundaries)
    x_boundaries, y_boundaries = build_boundaries(x_boundaries, y_boundaries, grid_block_dim)
    if not x_boundaries and not y_boundaries:
        raise ValueError("No boundaries resolved. Provide explicit boundaries or grid_block_dim.")

    common_files = sorted(set(path.name for path in pred_dir.glob("*.png")) & set(path.name for path in gt_dir.glob("*.png")))
    if not common_files:
        raise FileNotFoundError("No matching PNG files found for boundary LPIPS.")

    strip_scores = {}
    all_scores = []
    for file_name in common_files:
        with Image.open(pred_dir / file_name) as pred_image, Image.open(gt_dir / file_name) as gt_image:
            pred_crops = crop_boundary_strips(pred_image, x_boundaries, y_boundaries, args.crop_size)
            gt_crops = crop_boundary_strips(gt_image, x_boundaries, y_boundaries, args.crop_size)

        for strip_name in sorted(pred_crops.keys()):
            score = float(lpips(to_tensor(pred_crops[strip_name]), to_tensor(gt_crops[strip_name]), net_type="vgg").item())
            strip_scores.setdefault(strip_name, []).append(score)
            all_scores.append(score)

    results = {
        "crop_size": args.crop_size,
        "x_boundaries": x_boundaries,
        "y_boundaries": y_boundaries,
        "mean_boundary_lpips": float(sum(all_scores) / len(all_scores)),
        "per_strip": {name: float(sum(values) / len(values)) for name, values in strip_scores.items()},
        "num_images": len(common_files),
        "num_crops": len(all_scores),
    }

    out_path = method_dir / "boundary_lpips.json"
    with open(out_path, "w") as fp:
        json.dump(results, fp, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
