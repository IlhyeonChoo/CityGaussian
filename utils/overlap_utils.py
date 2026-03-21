import torch

from scene.gaussian_model import GaussianModel
from utils.large_utils import contract_to_unisphere


def normalize_aabb(aabb, xyz_org):
    xyz_tensor = torch.as_tensor(xyz_org, dtype=torch.float32, device=xyz_org.device)
    if len(aabb) == 4:
        aabb = [
            aabb[0],
            aabb[1],
            float(xyz_tensor[:, 2].min().item()),
            aabb[2],
            aabb[3],
            float(xyz_tensor[:, 2].max().item()),
        ]
    elif len(aabb) != 6:
        raise ValueError("Unknown aabb format")
    return torch.tensor(aabb, dtype=torch.float32, device=xyz_tensor.device)


def compute_overlap_bounds(block_id, block_dim, overlap_ratio, device=None, dtype=torch.float32):
    blocks_per_layer = block_dim[0] * block_dim[1]
    block_id_z = block_id // blocks_per_layer
    block_id_y = (block_id % blocks_per_layer) // block_dim[0]
    block_id_x = block_id % block_dim[0]

    core_bounds = torch.tensor(
        [
            float(block_id_x) / block_dim[0],
            float(block_id_x + 1) / block_dim[0],
            float(block_id_y) / block_dim[1],
            float(block_id_y + 1) / block_dim[1],
            float(block_id_z) / block_dim[2],
            float(block_id_z + 1) / block_dim[2],
        ],
        dtype=dtype,
        device=device,
    )

    expanded_bounds = core_bounds.clone()
    if overlap_ratio <= 0:
        return core_bounds, expanded_bounds

    for axis, dim in enumerate(block_dim):
        min_idx = axis * 2
        max_idx = min_idx + 1
        delta = (core_bounds[max_idx] - core_bounds[min_idx]) * overlap_ratio
        expanded_bounds[min_idx] = torch.clamp(core_bounds[min_idx] - delta / 2.0, min=0.0)
        expanded_bounds[max_idx] = torch.clamp(core_bounds[max_idx] + delta / 2.0, max=1.0)

    return core_bounds, expanded_bounds


def classify_zones(xyz_contracted, core_bounds, expanded_bounds):
    in_core = (
        (xyz_contracted[:, 0] >= core_bounds[0])
        & (xyz_contracted[:, 0] < core_bounds[1])
        & (xyz_contracted[:, 1] >= core_bounds[2])
        & (xyz_contracted[:, 1] < core_bounds[3])
        & (xyz_contracted[:, 2] >= core_bounds[4])
        & (xyz_contracted[:, 2] < core_bounds[5])
    )
    in_expanded = (
        (xyz_contracted[:, 0] >= expanded_bounds[0])
        & (xyz_contracted[:, 0] <= expanded_bounds[1])
        & (xyz_contracted[:, 1] >= expanded_bounds[2])
        & (xyz_contracted[:, 1] <= expanded_bounds[3])
        & (xyz_contracted[:, 2] >= expanded_bounds[4])
        & (xyz_contracted[:, 2] <= expanded_bounds[5])
    )
    overlap = in_expanded & ~in_core
    outside = ~in_expanded
    return in_core, overlap, outside


def block_filtering_overlap(block_id, xyz_org, aabb, block_dim, overlap_ratio, mask_only=True):
    xyz_tensor = torch.as_tensor(xyz_org, dtype=torch.float32, device=xyz_org.device)
    normalized_aabb = normalize_aabb(aabb, xyz_tensor)
    xyz = contract_to_unisphere(xyz_tensor, normalized_aabb, ord=torch.inf)
    _, expanded_bounds = compute_overlap_bounds(
        block_id,
        block_dim,
        overlap_ratio,
        device=xyz.device,
        dtype=xyz.dtype,
    )
    block_mask = (
        (xyz[:, 0] >= expanded_bounds[0])
        & (xyz[:, 0] <= expanded_bounds[1])
        & (xyz[:, 1] >= expanded_bounds[2])
        & (xyz[:, 1] <= expanded_bounds[3])
        & (xyz[:, 2] >= expanded_bounds[4])
        & (xyz[:, 2] <= expanded_bounds[5])
    )

    if mask_only:
        return block_mask
    return block_mask, xyz, expanded_bounds


def compute_blend_weights(xyz_contracted, core_bounds, expanded_bounds, eps=1e-6):
    if xyz_contracted.numel() == 0:
        return torch.empty((0,), dtype=xyz_contracted.dtype, device=xyz_contracted.device)

    weights = torch.ones((xyz_contracted.shape[0],), dtype=xyz_contracted.dtype, device=xyz_contracted.device)
    for axis in range(3):
        axis_weights = torch.ones_like(weights)
        core_min = core_bounds[axis * 2]
        core_max = core_bounds[axis * 2 + 1]
        expanded_min = expanded_bounds[axis * 2]
        expanded_max = expanded_bounds[axis * 2 + 1]
        coords = xyz_contracted[:, axis]

        outside_axis = (coords < expanded_min) | (coords > expanded_max)
        axis_weights[outside_axis] = 0.0

        left_width = core_min - expanded_min
        if left_width > eps:
            left_mask = (coords >= expanded_min) & (coords < core_min)
            axis_weights[left_mask] = (coords[left_mask] - expanded_min) / left_width

        right_width = expanded_max - core_max
        if right_width > eps:
            right_mask = (coords > core_max) & (coords <= expanded_max)
            axis_weights[right_mask] = (expanded_max - coords[right_mask]) / right_width

        weights = torch.minimum(weights, axis_weights)

    core_mask, _, outside_mask = classify_zones(xyz_contracted, core_bounds, expanded_bounds)
    weights[core_mask] = 1.0
    weights[outside_mask] = 0.0
    return torch.clamp(weights, min=0.0, max=1.0)


def build_masked_gaussians(gaussians, mask):
    masked_gaussians = GaussianModel(gaussians.max_sh_degree)
    masked_gaussians._xyz = gaussians.get_xyz[mask]
    masked_gaussians._scaling = gaussians._scaling[mask]
    masked_gaussians._rotation = gaussians._rotation[mask]
    masked_gaussians._features_dc = gaussians._features_dc[mask]
    masked_gaussians._features_rest = gaussians._features_rest[mask]
    masked_gaussians._opacity = gaussians._opacity[mask]
    if gaussians.max_radii2D.numel() == gaussians.get_xyz.shape[0]:
        masked_gaussians.max_radii2D = gaussians.max_radii2D[mask]
    else:
        masked_gaussians.max_radii2D = torch.zeros((int(mask.sum().item()),), device=gaussians.get_xyz.device)
    return masked_gaussians


def find_duplicates(xyz_all, block_ids_all, threshold, blend_weights=None):
    if xyz_all.numel() == 0 or threshold <= 0:
        return torch.ones((xyz_all.shape[0],), dtype=torch.bool, device=xyz_all.device)

    xyz_cpu = xyz_all.detach().cpu()
    block_cpu = block_ids_all.detach().cpu()
    blend_cpu = None if blend_weights is None else blend_weights.detach().cpu()

    voxel_coords = torch.floor(xyz_cpu / threshold).to(torch.int64)
    keep_mask = torch.ones((xyz_cpu.shape[0],), dtype=torch.bool)
    buckets = {}

    for idx, voxel in enumerate(voxel_coords.tolist()):
        key = tuple(voxel)
        bucket = buckets.setdefault(key, [])
        for other_idx in list(bucket):
            if not keep_mask[other_idx]:
                continue
            if block_cpu[other_idx].item() == block_cpu[idx].item():
                continue
            if torch.linalg.norm(xyz_cpu[idx] - xyz_cpu[other_idx]).item() >= threshold:
                continue

            current_weight = 1.0 if blend_cpu is None else float(blend_cpu[idx].item())
            other_weight = 1.0 if blend_cpu is None else float(blend_cpu[other_idx].item())

            if current_weight > other_weight:
                keep_mask[other_idx] = False
            else:
                keep_mask[idx] = False
                break

        if keep_mask[idx]:
            bucket.append(idx)

    return keep_mask.to(xyz_all.device)
