import argparse
import json
import os
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
from utils.image_utils import color_correct, psnr
from utils.loss_utils import ssim


def load_image(path: Path) -> torch.Tensor:
    with Image.open(path) as image:
        return tf.to_tensor(image).unsqueeze(0)[:, :3, :, :]


def resolve_test_sets(model_paths: list[str], test_sets: list[str]) -> list[str]:
    if len(test_sets) == 1 and len(model_paths) > 1:
        return test_sets * len(model_paths)
    if len(test_sets) != len(model_paths):
        raise ValueError("Provide either one test set or one test set per model path.")
    return test_sets


def evaluate_method(method_dir: Path, correct_color: bool) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    gt_dir = method_dir / "gt"
    renders_dir = method_dir / "renders"
    image_names = sorted(
        name
        for name in os.listdir(renders_dir)
        if (renders_dir / name).is_file() and (gt_dir / name).is_file()
    )
    if not image_names:
        raise FileNotFoundError(f"No matching render/gt PNG files found in {method_dir}")

    ssims: list[float] = []
    psnrs: list[float] = []
    lpipss: list[float] = []
    per_view: dict[str, dict[str, float]] = {}

    for image_name in tqdm(image_names, desc=f"Metrics {method_dir}"):
        render = load_image(renders_dir / image_name)
        gt = load_image(gt_dir / image_name)

        if correct_color:
            render_np = render.numpy().transpose(0, 2, 3, 1)
            gt_np = gt.numpy().transpose(0, 2, 3, 1)
            render = torch.from_numpy(color_correct(render_np, gt_np).transpose(0, 3, 1, 2)).contiguous()

        render = render.cuda()
        gt = gt.cuda()

        with torch.no_grad():
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

        del render, gt
        torch.cuda.empty_cache()

    summary = {
        "SSIM": float(sum(ssims) / len(ssims)),
        "PSNR": float(sum(psnrs) / len(psnrs)),
        "LPIPS": float(sum(lpipss) / len(lpipss)),
    }
    return summary, per_view


def main() -> None:
    parser = argparse.ArgumentParser(description="Streaming metric evaluation for rendered CityGaussian outputs")
    parser.add_argument("--model_paths", "-m", required=True, nargs="+", type=str)
    parser.add_argument("--test_sets", "-t", required=False, nargs="+", type=str, default=["test"])
    parser.add_argument("--correct_color", "-c", action="store_true", default=False)
    args = parser.parse_args()

    torch.cuda.set_device(torch.device("cuda:0"))
    test_sets = resolve_test_sets(args.model_paths, args.test_sets)

    for scene_dir, test_set in zip(args.model_paths, test_sets):
        scene_path = Path(scene_dir)
        test_dir = scene_path / test_set
        if not test_dir.exists():
            raise FileNotFoundError(f"Missing test set directory: {test_dir}")

        full_dict: dict[str, dict[str, float]] = {}
        per_view_dict: dict[str, dict[str, dict[str, float]]] = {}

        print(f"Scene: {scene_dir}")
        for method_dir in sorted(path for path in test_dir.iterdir() if path.is_dir()):
            print(f"Method: {method_dir.name}")
            summary, per_view = evaluate_method(method_dir, args.correct_color)
            full_dict[method_dir.name] = summary
            per_view_dict[method_dir.name] = {
                "SSIM": {name: values["SSIM"] for name, values in per_view.items()},
                "PSNR": {name: values["PSNR"] for name, values in per_view.items()},
                "LPIPS": {name: values["LPIPS"] for name, values in per_view.items()},
            }
            print(json.dumps(summary, indent=2))

        with (scene_path / "results.json").open("w", encoding="utf-8") as handle:
            json.dump(full_dict, handle, indent=2)
        with (scene_path / "per_view.json").open("w", encoding="utf-8") as handle:
            json.dump(per_view_dict, handle, indent=2)


if __name__ == "__main__":
    main()
