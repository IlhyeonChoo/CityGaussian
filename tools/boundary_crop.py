import argparse
import os
import re
from pathlib import Path

from PIL import Image


def parse_fraction_list(raw_value):
    if not raw_value:
        return []
    return [float(value.strip()) for value in raw_value.split(",") if value.strip()]


def parse_grid_block_dim(raw_value):
    if not raw_value:
        return None
    values = [int(value.strip()) for value in raw_value.split(",") if value.strip()]
    if len(values) == 2:
        values.append(1)
    if len(values) != 3:
        raise ValueError("grid_block_dim must have 2 or 3 integers")
    return values


def infer_block_dim_from_cfg_args(model_dir):
    cfg_path = Path(model_dir) / "cfg_args"
    if not cfg_path.exists():
        return None
    match = re.search(r"block_dim=\[([0-9,\s]+)\]", cfg_path.read_text())
    if not match:
        return None
    values = [int(value.strip()) for value in match.group(1).split(",")]
    if len(values) == 2:
        values.append(1)
    return values


def build_boundaries(x_boundaries, y_boundaries, grid_block_dim=None):
    if not x_boundaries and grid_block_dim and grid_block_dim[0] > 1:
        x_boundaries = [idx / grid_block_dim[0] for idx in range(1, grid_block_dim[0])]
    if not y_boundaries and grid_block_dim and grid_block_dim[1] > 1:
        y_boundaries = [idx / grid_block_dim[1] for idx in range(1, grid_block_dim[1])]
    return x_boundaries, y_boundaries


def crop_boundary_strips(image, x_boundaries, y_boundaries, crop_size):
    width, height = image.size
    crops = {}

    for boundary in x_boundaries:
        center = int(round(boundary * (width - 1)))
        left = max(0, center - crop_size // 2)
        right = min(width, left + crop_size)
        left = max(0, right - crop_size)
        crops[f"x_{boundary:.4f}"] = image.crop((left, 0, right, height))

    for boundary in y_boundaries:
        center = int(round(boundary * (height - 1)))
        top = max(0, center - crop_size // 2)
        bottom = min(height, top + crop_size)
        top = max(0, bottom - crop_size)
        crops[f"y_{boundary:.4f}"] = image.crop((0, top, width, bottom))

    return crops


def main():
    parser = argparse.ArgumentParser(description="Crop boundary strips from rendered images")
    parser.add_argument("--input_dir", required=True, type=str)
    parser.add_argument("--output_dir", required=True, type=str)
    parser.add_argument("--crop_size", type=int, default=128)
    parser.add_argument("--x_boundaries", type=str, default="")
    parser.add_argument("--y_boundaries", type=str, default="")
    parser.add_argument("--grid_block_dim", type=str, default="")
    parser.add_argument("--model_dir", type=str, default="")
    args = parser.parse_args()

    x_boundaries = parse_fraction_list(args.x_boundaries)
    y_boundaries = parse_fraction_list(args.y_boundaries)
    grid_block_dim = parse_grid_block_dim(args.grid_block_dim)
    if grid_block_dim is None and args.model_dir:
        grid_block_dim = infer_block_dim_from_cfg_args(args.model_dir)
    x_boundaries, y_boundaries = build_boundaries(x_boundaries, y_boundaries, grid_block_dim)

    if not x_boundaries and not y_boundaries:
        raise ValueError("No boundaries specified. Provide x/y boundaries, grid_block_dim, or model_dir.")

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for image_path in sorted(input_dir.glob("*.png")):
        with Image.open(image_path) as image:
            for boundary_name, crop in crop_boundary_strips(image, x_boundaries, y_boundaries, args.crop_size).items():
                crop.save(output_dir / f"{image_path.stem}__{boundary_name}.png")


if __name__ == "__main__":
    main()
