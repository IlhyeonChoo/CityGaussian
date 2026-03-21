import argparse
from pathlib import Path

import matplotlib.cm as cm
import numpy as np
from PIL import Image


def resolve_dirs(output_dir, pred_dir, gt_dir, test_set, iteration):
    if output_dir:
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
        return method_dir / "renders", method_dir / "gt", method_dir / "error_map"

    if not pred_dir or not gt_dir:
        raise ValueError("Either --output_dir or both --pred_dir and --gt_dir are required.")
    return Path(pred_dir), Path(gt_dir), Path(pred_dir).parent / "error_map"


def main():
    parser = argparse.ArgumentParser(description="Create per-image error maps")
    parser.add_argument("--output_dir", type=str, default="")
    parser.add_argument("--pred_dir", type=str, default="")
    parser.add_argument("--gt_dir", type=str, default="")
    parser.add_argument("--test_set", type=str, default="test")
    parser.add_argument("--iteration", type=int, default=-1)
    args = parser.parse_args()

    pred_dir, gt_dir, save_dir = resolve_dirs(args.output_dir, args.pred_dir, args.gt_dir, args.test_set, args.iteration)
    save_dir.mkdir(parents=True, exist_ok=True)

    common_files = sorted(set(path.name for path in pred_dir.glob("*.png")) & set(path.name for path in gt_dir.glob("*.png")))
    if not common_files:
        raise FileNotFoundError("No matching PNG files found for error maps.")

    for file_name in common_files:
        with Image.open(pred_dir / file_name) as pred_image, Image.open(gt_dir / file_name) as gt_image:
            pred = np.asarray(pred_image, dtype=np.float32)[..., :3] / 255.0
            gt = np.asarray(gt_image, dtype=np.float32)[..., :3] / 255.0
        error = np.abs(pred - gt).mean(axis=-1)
        heatmap = (cm.inferno(np.clip(error / max(error.max(), 1e-6), 0.0, 1.0))[..., :3] * 255).astype(np.uint8)
        Image.fromarray(heatmap).save(save_dir / file_name)


if __name__ == "__main__":
    main()
