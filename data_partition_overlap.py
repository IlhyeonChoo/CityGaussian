import os
import sys
from argparse import ArgumentParser, Namespace

import numpy as np
import torch
import yaml

from data_partition import block_partitioning
from scene import LargeScene
from utils.camera_utils import loadCam_woImage
from utils.general_utils import parse_cfg, safe_state
from utils.large_utils import contract_to_unisphere, get_default_aabb
from utils.overlap_utils import compute_overlap_bounds, normalize_aabb


def expanded_camera_selection(cameras, gaussians, args, scale=1.0):
    xyz_org = gaussians.get_xyz
    if args.aabb is None:
        args.aabb = get_default_aabb(args, cameras, xyz_org, scale)

    aabb = normalize_aabb(args.aabb, xyz_org)
    block_num = args.block_dim[0] * args.block_dim[1] * args.block_dim[2]
    camera_mask = torch.zeros((len(cameras), block_num), dtype=torch.bool, device=xyz_org.device)

    cam_centers = []
    for idx, cam in enumerate(cameras):
        viewpoint_cam = loadCam_woImage(args, idx, cam, scale)
        cam_centers.append(contract_to_unisphere(viewpoint_cam.camera_center, aabb, ord=torch.inf))
    cam_centers = torch.stack(cam_centers, dim=0)

    for block_id in range(block_num):
        _, expanded_bounds = compute_overlap_bounds(
            block_id,
            args.block_dim,
            getattr(args, "overlap_ratio", 0.0),
            device=cam_centers.device,
            dtype=cam_centers.dtype,
        )
        camera_mask[:, block_id] = (
            (cam_centers[:, 0] >= expanded_bounds[0])
            & (cam_centers[:, 0] <= expanded_bounds[1])
            & (cam_centers[:, 1] >= expanded_bounds[2])
            & (cam_centers[:, 1] <= expanded_bounds[3])
            & (cam_centers[:, 2] >= expanded_bounds[4])
            & (cam_centers[:, 2] <= expanded_bounds[5])
        )

    return camera_mask


if __name__ == "__main__":
    parser = ArgumentParser(description="Overlap-aware partitioning")
    parser.add_argument("--config", type=str, required=True, help="train config file path")
    parser.add_argument("--debug_from", type=int, default=-1)
    parser.add_argument("--detect_anomaly", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--disable_inblock", action="store_true")
    args = parser.parse_args(sys.argv[1:])

    with open(args.config) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        lp, op, pp = parse_cfg(cfg, args)

    safe_state(args.quiet)

    config_name = os.path.splitext(os.path.basename(lp.config))[0]
    if not lp.model_path:
        lp.model_path = os.path.join("./output/", config_name)

    print(f"Output folder: {lp.model_path}")
    os.makedirs(lp.model_path, exist_ok=True)
    with open(os.path.join(lp.model_path, "cfg_args"), "w") as cfg_log_f:
        cfg_log_f.write(str(Namespace(**vars(lp))))

    modules = __import__("scene")
    model_config = lp.model_config
    gaussians = getattr(modules, model_config["name"])(lp.sh_degree, **model_config["kwargs"])
    scene = LargeScene(lp, gaussians, shuffle=False)

    partition_dir = os.path.join(lp.source_path, "data_partitions")
    os.makedirs(partition_dir, exist_ok=True)

    base_mask = block_partitioning(
        scene.getTrainCameras(),
        gaussians,
        lp,
        pp,
        1.0,
        args.quiet,
        args.disable_inblock,
        simple_selection=False,
    )
    if getattr(lp, "overlap_ratio", 0.0) > 0:
        expanded_mask = expanded_camera_selection(scene.getTrainCameras(), gaussians, lp, 1.0)
        camera_mask = base_mask | expanded_mask
    else:
        camera_mask = base_mask

    if lp.aabb is not None:
        aabb = normalize_aabb(lp.aabb, gaussians.get_xyz)
        np.save(os.path.join(partition_dir, f"{config_name}_aabb.npy"), aabb.detach().cpu().numpy())

    camera_mask_np = camera_mask.cpu().numpy()
    np.save(os.path.join(partition_dir, f"{config_name}.npy"), camera_mask_np)

    for block_id in range(camera_mask_np.shape[1]):
        print(f"Block {block_id} / {camera_mask_np.shape[1]} has {camera_mask_np[:, block_id].sum()} cameras.")

    print("\nPartition complete.")
