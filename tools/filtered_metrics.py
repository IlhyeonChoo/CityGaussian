import argparse
import json
import sys
from pathlib import Path

import torch
import torchvision.transforms.functional as tf
from PIL import Image
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lpipsPyTorch import lpips
from utils.image_utils import psnr
from utils.loss_utils import ssim


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


def load_manifest(view_manifest):
    with open(view_manifest, "r", encoding="utf-8") as handle:
        return json.load(handle)


def to_tensor(image_path):
    with Image.open(image_path) as image:
        return tf.to_tensor(image).unsqueeze(0)[:, :3, :, :]


def main():
    parser = argparse.ArgumentParser(description="Compute PSNR/SSIM/LPIPS on a filtered boundary-view subset")
    parser.add_argument("--output_dir", required=True, type=str)
    parser.add_argument("--test_set", default="test", type=str)
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--view_manifest", required=True, type=str)
    args = parser.parse_args()

    device = torch.device("cuda:0")
    torch.cuda.set_device(device)

    method_dir = resolve_method_dir(args.output_dir, args.test_set, args.iteration)
    renders_dir = method_dir / "renders"
    gt_dir = method_dir / "gt"
    manifest = load_manifest(args.view_manifest)
    selected_images = manifest["selected_images"]
    if not selected_images:
        raise ValueError("Manifest does not contain any selected images.")

    ssims = []
    psnrs = []
    lpipss = []
    per_view = {}

    for image_name in tqdm(selected_images, desc="Filtered metric evaluation"):
        render = to_tensor(renders_dir / image_name).cuda()
        gt = to_tensor(gt_dir / image_name).cuda()
        ssim_value = float(ssim(render, gt).item())
        psnr_value = float(psnr(render, gt).item())
        lpips_value = float(lpips(render, gt, net_type="vgg").item())

        ssims.append(ssim_value)
        psnrs.append(psnr_value)
        lpipss.append(lpips_value)
        per_view[image_name] = {
            "SSIM": ssim_value,
            "PSNR": psnr_value,
            "LPIPS": lpips_value,
        }

    result = {
        "selection_manifest": str(args.view_manifest),
        "num_images": len(selected_images),
        "SSIM": float(sum(ssims) / len(ssims)),
        "PSNR": float(sum(psnrs) / len(psnrs)),
        "LPIPS": float(sum(lpipss) / len(lpipss)),
        "per_view": per_view,
    }

    out_path = method_dir / "boundary_view_metrics.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
