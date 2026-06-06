#
# Copyright (C) 2023, Inria
# GRAPHDECO research group, https://team.inria.fr/graphdeco
# All rights reserved.
#
# This software is free for non-commercial, research and evaluation use 
# under the terms of the LICENSE.md file.
#
# For inquiries contact  george.drettakis@inria.fr
#

import torch
import yaml
import os
import sys

import torchvision
import numpy as np
import matplotlib.pyplot as plt
import torchvision.transforms.functional as tf
from PIL import Image
from tqdm import tqdm
from os import makedirs
from scene import Scene
from gaussian_renderer import render
from utils.general_utils import safe_state
from argparse import ArgumentParser
from arguments import ModelParams, PipelineParams
from gaussian_renderer import GaussianModel
from arguments import ModelParams, PipelineParams, OptimizationParams, GroupParams
from utils.loss_utils import l1_loss, ssim
from utils.general_utils import parse_cfg

def _is_colmap_unit_partition(lp):
    return getattr(lp, "partition_mode", "grid") == "colmap_unit"


def _partition_base_path(lp):
    return os.path.join(lp.source_path, "data_partitions", lp.partition_name)


def _expand_bounds(bounds, lp):
    bounds = np.asarray(bounds, dtype=np.float32)
    bounds_min = bounds[:3]
    bounds_max = bounds[3:]
    extent = np.maximum(bounds_max - bounds_min, 1e-6)
    margin = float(getattr(lp, "unit_aabb_margin", 0.0))
    margin_ratio = float(getattr(lp, "unit_aabb_margin_ratio", 0.02))
    padding = margin + extent * margin_ratio
    return np.concatenate([bounds_min - padding, bounds_max + padding])


def _bounds_mask_tensor(xyz, bounds):
    bounds_tensor = torch.tensor(bounds, dtype=xyz.dtype, device=xyz.device)
    bounds_min = bounds_tensor[:3]
    bounds_max = bounds_tensor[3:]
    return (
        (xyz[:, 0] >= bounds_min[0])
        & (xyz[:, 0] <= bounds_max[0])
        & (xyz[:, 1] >= bounds_min[1])
        & (xyz[:, 1] <= bounds_max[1])
        & (xyz[:, 2] >= bounds_min[2])
        & (xyz[:, 2] <= bounds_max[2])
    )


def _apply_gaussian_mask_in_place(gaussians, mask):
    gaussians._xyz = gaussians.get_xyz[mask]
    gaussians._features_dc = gaussians._features_dc[mask]
    gaussians._features_rest = gaussians._features_rest[mask]
    gaussians._scaling = gaussians._scaling[mask]
    gaussians._rotation = gaussians._rotation[mask]
    gaussians._opacity = gaussians._opacity[mask]
    gaussians.max_radii2D = gaussians.max_radii2D[mask]


def _load_unit_bounds(lp):
    bounds_path = f"{_partition_base_path(lp)}_bounds.npy"
    if not os.path.exists(bounds_path):
        raise FileNotFoundError(f"Missing unit bounds file: {bounds_path}")
    return np.load(bounds_path)


def _block_ply_path(out_dir, block_id, iteration):
    return os.path.join(
        out_dir,
        f"cells/cell{block_id}",
        "point_cloud_blocks",
        "scale_1.0",
        f"iteration_{iteration}",
        "point_cloud.ply",
    )


def readImages(renders_dir, gt_dir):
    renders = []
    gts = []
    image_names = []
    for fname in os.listdir(renders_dir):
        with Image.open(renders_dir / fname) as render:
            renders.append(tf.to_tensor(render).unsqueeze(0)[:, :3, :, :].cuda())
        with Image.open(gt_dir / fname) as gt:
            gts.append(tf.to_tensor(gt).unsqueeze(0)[:, :3, :, :].cuda())
        image_names.append(fname)
    return renders, gts, image_names

def blockMerge(lp, iteration):
    out_dir = lp.model_path
    merged_gaussians = GaussianModel(lp.sh_degree)
    num_blocks = lp.block_dim[0] * lp.block_dim[1] * lp.block_dim[2]
    strict_iteration = bool(getattr(lp, "unit_merge_strict_iteration", False))
    merge_filter_mode = getattr(lp, "unit_merge_filter_mode", "none")
    if merge_filter_mode not in {"none", "bounds"}:
        raise ValueError(f"Unknown unit_merge_filter_mode: {merge_filter_mode}")
    unit_bounds = _load_unit_bounds(lp) if _is_colmap_unit_partition(lp) and merge_filter_mode == "bounds" else None

    with torch.no_grad():
        for idx in range(num_blocks):
            gaussians = GaussianModel(lp.sh_degree)
            ply_path = _block_ply_path(out_dir, idx, iteration)
            if os.path.exists(ply_path):
                gaussians.load_ply(ply_path)
                num_iter = iteration
            elif strict_iteration:
                raise FileNotFoundError(f"Missing block {idx} ply for strict merge: {ply_path}")
            else:
                fallback_path = _block_ply_path(out_dir, idx, 1)
                gaussians.load_ply(fallback_path)
                num_iter = 1

            if unit_bounds is not None:
                if idx >= unit_bounds.shape[0]:
                    raise ValueError(f"Missing bounds for block {idx}; bounds shape is {unit_bounds.shape}.")
                before_count = int(gaussians.get_xyz.shape[0])
                block_bounds = _expand_bounds(unit_bounds[idx], lp)
                keep_mask = _bounds_mask_tensor(gaussians.get_xyz, block_bounds)
                if not keep_mask.any():
                    raise ValueError(f"Unit bounds merge filter removed all gaussians for block_id {idx}.")
                _apply_gaussian_mask_in_place(gaussians, keep_mask)
                pruned_count = before_count - int(gaussians.get_xyz.shape[0])
                if pruned_count > 0:
                    print(f"Merge bounds filter pruned {pruned_count} / {before_count} points from block {idx}.")
            
            if len(merged_gaussians._xyz) == 0:
                merged_gaussians._xyz = gaussians.get_xyz
                merged_gaussians._features_dc = gaussians._features_dc
                merged_gaussians._features_rest = gaussians._features_rest
                merged_gaussians._scaling = gaussians._scaling
                merged_gaussians._rotation = gaussians._rotation
                merged_gaussians._opacity = gaussians._opacity
                merged_gaussians.max_radii2D = gaussians.max_radii2D
            else:
                merged_gaussians._xyz = torch.cat([merged_gaussians._xyz, gaussians.get_xyz], dim=0)
                merged_gaussians._features_dc = torch.cat([merged_gaussians._features_dc, gaussians._features_dc], dim=0)
                merged_gaussians._features_rest = torch.cat([merged_gaussians._features_rest, gaussians._features_rest], dim=0)
                merged_gaussians._scaling = torch.cat([merged_gaussians._scaling, gaussians._scaling], dim=0)
                merged_gaussians._rotation = torch.cat([merged_gaussians._rotation, gaussians._rotation], dim=0)
                merged_gaussians._opacity = torch.cat([merged_gaussians._opacity, gaussians._opacity], dim=0)
                merged_gaussians.max_radii2D = torch.cat([merged_gaussians.max_radii2D, gaussians.max_radii2D], dim=0)
            
            print(f"Merged {len(gaussians.get_xyz)} points from block {idx} from iteration {num_iter}.")
    
    save_path = os.path.join(out_dir, "point_cloud", "iteration_" + str(iteration), "point_cloud.ply")
    print(f"Saving merged {len(merged_gaussians.get_xyz)} point cloud to {save_path}")
    merged_gaussians.save_ply(save_path)
    print('Done')


if __name__ == "__main__":
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)

    # Set up command line argument parser
    parser = ArgumentParser(description="Training script parameters")
    parser.add_argument('--config', type=str, help='train config file path')
    parser.add_argument('--model_path', type=str, help='model path of fused model')
    parser.add_argument("--iteration", default=30_000, type=int)
    args = parser.parse_args(sys.argv[1:])
    if args.model_path is None:
        args.model_path = os.path.join('output', os.path.basename(args.config).split('.')[0])

    with open(args.config) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        lp, op, pp = parse_cfg(cfg, args)

    blockMerge(lp, args.iteration)
