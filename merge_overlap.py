import json
import os
import sys
from argparse import ArgumentParser

import torch
import yaml

from scene.gaussian_model import GaussianModel
from utils.general_utils import inverse_sigmoid, parse_cfg
from utils.large_utils import contract_to_unisphere
from utils.overlap_utils import (
    compute_blend_weights,
    compute_overlap_bounds,
    find_duplicates,
    normalize_aabb,
)


def resolve_block_path(out_dir, block_id, iteration):
    candidates = [
        os.path.join(out_dir, f"cells/cell{block_id}", "point_cloud_overlap", f"iteration_{iteration}", "point_cloud.ply"),
        os.path.join(out_dir, f"cells/cell{block_id}", "point_cloud_blocks", "scale_1.0", f"iteration_{iteration}", "point_cloud.ply"),
        os.path.join(out_dir, f"cells/cell{block_id}", "point_cloud_overlap", "iteration_1", "point_cloud.ply"),
        os.path.join(out_dir, f"cells/cell{block_id}", "point_cloud_blocks", "scale_1.0", "iteration_1", "point_cloud.ply"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"No block point cloud found for cell{block_id}")


def load_partition_aabb(lp):
    if lp.aabb is not None:
        return normalize_aabb(lp.aabb, torch.zeros((1, 3), device="cuda"))
    aabb_path = os.path.join(lp.source_path, "data_partitions", f"{lp.partition_name}_aabb.npy")
    if os.path.exists(aabb_path):
        return torch.tensor(torch.from_numpy(__import__("numpy").load(aabb_path)).tolist(), dtype=torch.float32, device="cuda")
    raise FileNotFoundError("AABB is required for overlap merge")


def block_merge_overlap(lp, iteration):
    out_dir = lp.model_path
    num_blocks = lp.block_dim[0] * lp.block_dim[1] * lp.block_dim[2]
    aabb = load_partition_aabb(lp)

    xyz_parts = []
    fdc_parts = []
    frest_parts = []
    scaling_parts = []
    rotation_parts = []
    opacity_parts = []
    block_ids = []
    blend_parts = []

    with torch.no_grad():
        for idx in range(num_blocks):
            gaussians = GaussianModel(lp.sh_degree)
            block_path = resolve_block_path(out_dir, idx, iteration)
            gaussians.load_ply(block_path)

            if getattr(lp, "blend_mode", "hard") == "soft" and getattr(lp, "overlap_ratio", 0.0) > 0:
                xyz_contracted = contract_to_unisphere(gaussians.get_xyz, aabb, ord=torch.inf)
                core_bounds, expanded_bounds = compute_overlap_bounds(
                    idx,
                    lp.block_dim,
                    lp.overlap_ratio,
                    device=xyz_contracted.device,
                    dtype=xyz_contracted.dtype,
                )
                blend_weight = compute_blend_weights(xyz_contracted, core_bounds, expanded_bounds)
                opacity = torch.sigmoid(gaussians._opacity) * blend_weight.unsqueeze(-1)
                opacity = torch.clamp(opacity, min=1e-6, max=1.0 - 1e-6)
                gaussians._opacity = torch.nn.Parameter(inverse_sigmoid(opacity))
            else:
                blend_weight = torch.ones((gaussians.get_xyz.shape[0],), dtype=gaussians.get_xyz.dtype, device=gaussians.get_xyz.device)

            xyz_parts.append(gaussians.get_xyz)
            fdc_parts.append(gaussians._features_dc)
            frest_parts.append(gaussians._features_rest)
            scaling_parts.append(gaussians._scaling)
            rotation_parts.append(gaussians._rotation)
            opacity_parts.append(gaussians._opacity)
            block_ids.append(torch.full((gaussians.get_xyz.shape[0],), idx, dtype=torch.long, device=gaussians.get_xyz.device))
            blend_parts.append(blend_weight)

            print(f"Merged {len(gaussians.get_xyz)} points from block {idx}.")

    merged_xyz = torch.cat(xyz_parts, dim=0) if xyz_parts else torch.empty((0, 3), device="cuda")
    merged_fdc = torch.cat(fdc_parts, dim=0) if fdc_parts else torch.empty((0, 1, 3), device="cuda")
    merged_frest = torch.cat(frest_parts, dim=0) if frest_parts else torch.empty((0, 15, 3), device="cuda")
    merged_scaling = torch.cat(scaling_parts, dim=0) if scaling_parts else torch.empty((0, 3), device="cuda")
    merged_rotation = torch.cat(rotation_parts, dim=0) if rotation_parts else torch.empty((0, 4), device="cuda")
    merged_opacity = torch.cat(opacity_parts, dim=0) if opacity_parts else torch.empty((0, 1), device="cuda")
    merged_block_ids = torch.cat(block_ids, dim=0) if block_ids else torch.empty((0,), dtype=torch.long, device="cuda")
    merged_blend = torch.cat(blend_parts, dim=0) if blend_parts else torch.empty((0,), device="cuda")

    num_before = int(merged_xyz.shape[0])
    if getattr(lp, "prune_duplicates", False) and num_before > 0:
        keep_mask = find_duplicates(
            merged_xyz,
            merged_block_ids,
            getattr(lp, "duplicate_threshold", 0.01),
            merged_blend,
        )
    else:
        keep_mask = torch.ones((num_before,), dtype=torch.bool, device=merged_xyz.device)

    merged_gaussians = GaussianModel(lp.sh_degree)
    merged_gaussians._xyz = merged_xyz[keep_mask]
    merged_gaussians._features_dc = merged_fdc[keep_mask]
    merged_gaussians._features_rest = merged_frest[keep_mask]
    merged_gaussians._scaling = merged_scaling[keep_mask]
    merged_gaussians._rotation = merged_rotation[keep_mask]
    merged_gaussians._opacity = merged_opacity[keep_mask]
    merged_gaussians.max_radii2D = torch.zeros((merged_gaussians.get_xyz.shape[0],), device=merged_gaussians.get_xyz.device)

    save_path = os.path.join(out_dir, "point_cloud", f"iteration_{iteration}", "point_cloud.ply")
    stats_path = os.path.join(out_dir, "point_cloud", f"iteration_{iteration}", "merge_stats.json")
    print(f"Saving merged {len(merged_gaussians.get_xyz)} point cloud to {save_path}")
    merged_gaussians.save_ply(save_path)
    with open(stats_path, "w") as fp:
        json.dump(
            {
                "num_blocks": num_blocks,
                "num_before_prune": num_before,
                "num_after_prune": int(merged_gaussians.get_xyz.shape[0]),
                "blend_mode": getattr(lp, "blend_mode", "hard"),
                "prune_duplicates": bool(getattr(lp, "prune_duplicates", False)),
            },
            fp,
            indent=2,
        )
    print("Done")


if __name__ == "__main__":
    parser = ArgumentParser(description="Overlap merge parameters")
    parser.add_argument("--config", type=str, required=True, help="train config file path")
    parser.add_argument("--model_path", type=str, help="model path of fused model")
    parser.add_argument("--iteration", default=30000, type=int)
    args = parser.parse_args(sys.argv[1:])

    if args.model_path is None:
        args.model_path = os.path.join("output", os.path.basename(args.config).split(".")[0])

    with open(args.config) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        lp, op, pp = parse_cfg(cfg, args)

    block_merge_overlap(lp, args.iteration)
