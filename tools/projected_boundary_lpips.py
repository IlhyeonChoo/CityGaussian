import argparse
import json
import sys
from pathlib import Path

import torch
import torchvision.transforms.functional as tf
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lpipsPyTorch import lpips


def resolve_method_dir(output_dir, test_set, iteration):
    test_dir = Path(output_dir) / test_set
    if iteration > 0:
        return test_dir / f"ours_{iteration}"

    candidates = sorted(
        [path for path in test_dir.iterdir() if path.is_dir() and path.name.startswith("ours_")],
        key=lambda path: int(path.name.split("_")[-1]),
    )
    if not candidates:
        raise FileNotFoundError(f"No rendered methods found in {test_dir}")
    return candidates[-1]


def crop_image(image, crop_xyxy):
    left, top, right, bottom = crop_xyxy
    return image.crop((left, top, right, bottom))


def to_tensor(image):
    return tf.to_tensor(image).unsqueeze(0)[:, :3, :, :].cuda()


def main():
    parser = argparse.ArgumentParser(description="Compute LPIPS on projected boundary crops")
    parser.add_argument("--output_dir", required=True, type=str)
    parser.add_argument("--test_set", default="test", type=str)
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--view_manifest", required=True, type=str)
    parser.add_argument("--save_crops", action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda:0")
    torch.cuda.set_device(device)

    method_dir = resolve_method_dir(args.output_dir, args.test_set, args.iteration)
    renders_dir = method_dir / "renders"
    gt_dir = method_dir / "gt"
    with open(args.view_manifest, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    selected_views = [view for view in manifest["per_view"] if view["selected"]]
    if not selected_views:
        raise ValueError("Manifest does not contain any selected views.")

    if args.save_crops:
        crop_root = method_dir / "projected_boundary_crops"
        render_crop_dir = crop_root / "renders"
        gt_crop_dir = crop_root / "gt"
        render_crop_dir.mkdir(parents=True, exist_ok=True)
        gt_crop_dir.mkdir(parents=True, exist_ok=True)

    all_scores = []
    per_boundary = {}
    per_view = {}

    for view in selected_views:
        image_name = view["image_name"]
        with Image.open(renders_dir / image_name) as render_image, Image.open(gt_dir / image_name) as gt_image:
            crop_scores = []
            for hit_index, hit in enumerate(view["hits"]):
                crop_xyxy = hit["crop_xyxy"]
                render_crop = crop_image(render_image, crop_xyxy)
                gt_crop = crop_image(gt_image, crop_xyxy)
                score = float(lpips(to_tensor(render_crop), to_tensor(gt_crop), net_type="vgg").item())

                boundary_id = hit["boundary_id"]
                crop_scores.append(score)
                all_scores.append(score)
                per_boundary.setdefault(boundary_id, []).append(score)

                if args.save_crops:
                    crop_name = f"{Path(image_name).stem}__{boundary_id}__{hit_index}.png"
                    render_crop.save(render_crop_dir / crop_name)
                    gt_crop.save(gt_crop_dir / crop_name)

            per_view[image_name] = float(sum(crop_scores) / len(crop_scores))

    result = {
        "selection_manifest": str(args.view_manifest),
        "num_images": len(selected_views),
        "num_crops": len(all_scores),
        "mean_projected_boundary_lpips": float(sum(all_scores) / len(all_scores)),
        "per_boundary": {name: float(sum(values) / len(values)) for name, values in per_boundary.items()},
        "per_view": per_view,
    }

    if args.save_crops:
        result["crop_dir"] = str(method_dir / "projected_boundary_crops")

    out_path = method_dir / "projected_boundary_lpips.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
