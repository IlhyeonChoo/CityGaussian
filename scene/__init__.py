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

import os
import tqdm
import random
import json
import yaml
import torch
import numpy as np
from utils.system_utils import searchForMaxIteration
from utils.graphics_utils import BasicPointCloud
from scene.dataset_readers import sceneLoadTypeCallbacks, storePly, SceneInfo
from scene.gaussian_model import GaussianModel, GaussianModelLOD, GatheredGaussian
from arguments import ModelParams, GroupParams
from plyfile import PlyData, PlyElement
from utils.camera_utils import cameraList_from_camInfos, camera_to_JSON


def _is_colmap_unit_partition(args):
    return getattr(args, "partition_mode", "grid") == "colmap_unit"


def _partition_base_path(args):
    return os.path.join(args.source_path, "data_partitions", args.partition_name)


def _load_unit_bounds(args):
    bounds_path = f"{_partition_base_path(args)}_bounds.npy"
    if not os.path.exists(bounds_path):
        raise FileNotFoundError(f"Missing unit bounds file: {bounds_path}")
    bounds = np.load(bounds_path)
    if args.block_id < 0 or args.block_id >= bounds.shape[0]:
        raise ValueError(f"Invalid block_id {args.block_id} for unit bounds with shape {bounds.shape}")
    return bounds[args.block_id].astype(np.float32)


def _expand_unit_bounds(bounds, args):
    bounds = np.asarray(bounds, dtype=np.float32)
    bounds_min = bounds[:3]
    bounds_max = bounds[3:]
    extent = np.maximum(bounds_max - bounds_min, 1e-6)
    margin = float(getattr(args, "unit_aabb_margin", 0.0))
    margin_ratio = float(getattr(args, "unit_aabb_margin_ratio", 0.02))
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


def _contract_to_unisphere_tensor(x: torch.Tensor, aabb: torch.Tensor, ord: float = torch.inf):
    aabb_min, aabb_max = torch.split(aabb, 3, dim=-1)
    x = (x - aabb_min) / (aabb_max - aabb_min)
    x = x * 2 - 1
    mag = torch.linalg.norm(x, ord=ord, dim=-1, keepdim=True)
    mask = mag.squeeze(-1) > 1
    x = x.clone()
    x[mask] = (2 - 1 / mag[mask]) * (x[mask] / mag[mask])
    return x / 4 + 0.5


def _grid_aabb_tensor(args, xyz: torch.Tensor):
    raw_aabb = args.aabb
    if raw_aabb is None:
        raise ValueError("Grid pretrain filtering requires args.aabb.")
    if isinstance(raw_aabb, torch.Tensor):
        values = raw_aabb.to(dtype=xyz.dtype, device=xyz.device)
    else:
        values = torch.tensor(raw_aabb, dtype=xyz.dtype, device=xyz.device)
    if values.numel() == 4:
        z_min = xyz[:, -1].min()
        z_max = xyz[:, -1].max()
        values = torch.stack([values[0], values[1], z_min, values[2], values[3], z_max])
    if values.numel() != 6:
        raise ValueError(f"Unknown grid aabb format with {values.numel()} values.")
    return values


def _grid_block_mask_tensor(xyz: torch.Tensor, args, padding: float = 0.0):
    aabb = _grid_aabb_tensor(args, xyz)
    xyz_contracted = _contract_to_unisphere_tensor(xyz, aabb, ord=torch.inf)
    block_id_z = args.block_id // (args.block_dim[0] * args.block_dim[1])
    block_id_y = (args.block_id % (args.block_dim[0] * args.block_dim[1])) // args.block_dim[0]
    block_id_x = (args.block_id % (args.block_dim[0] * args.block_dim[1])) % args.block_dim[0]

    min_x = max(0.0, float(block_id_x) / args.block_dim[0] - padding)
    max_x = min(1.0, float(block_id_x + 1) / args.block_dim[0] + padding)
    min_y = max(0.0, float(block_id_y) / args.block_dim[1] - padding)
    max_y = min(1.0, float(block_id_y + 1) / args.block_dim[1] + padding)
    min_z = max(0.0, float(block_id_z) / args.block_dim[2] - padding)
    max_z = min(1.0, float(block_id_z + 1) / args.block_dim[2] + padding)

    return (
        (xyz_contracted[:, 0] >= min_x)
        & (xyz_contracted[:, 0] < max_x)
        & (xyz_contracted[:, 1] >= min_y)
        & (xyz_contracted[:, 1] < max_y)
        & (xyz_contracted[:, 2] >= min_z)
        & (xyz_contracted[:, 2] < max_z)
    )


def _unit_bounds_mask_tensor(xyz, args):
    unit_bounds = _expand_unit_bounds(_load_unit_bounds(args), args)
    return _bounds_mask_tensor(xyz, unit_bounds)


def _bounds_mask_numpy(xyz, bounds):
    bounds = np.asarray(bounds, dtype=xyz.dtype)
    bounds_min = bounds[:3]
    bounds_max = bounds[3:]
    return (
        (xyz[:, 0] >= bounds_min[0])
        & (xyz[:, 0] <= bounds_max[0])
        & (xyz[:, 1] >= bounds_min[1])
        & (xyz[:, 1] <= bounds_max[1])
        & (xyz[:, 2] >= bounds_min[2])
        & (xyz[:, 2] <= bounds_max[2])
    )


def _copy_gaussian_subset(gaussians, mask):
    sh_degree = gaussians.max_sh_degree
    masked_gaussians = GaussianModel(sh_degree)
    masked_gaussians._xyz = gaussians.get_xyz[mask]
    masked_gaussians._scaling = gaussians._scaling[mask]
    masked_gaussians._rotation = gaussians._rotation[mask]
    masked_gaussians._features_dc = gaussians._features_dc[mask]
    masked_gaussians._features_rest = gaussians._features_rest[mask]
    masked_gaussians._opacity = gaussians._opacity[mask]
    masked_gaussians.max_radii2D = gaussians.max_radii2D[mask]
    return masked_gaussians


def _apply_gaussian_mask_in_place(gaussians, mask):
    gaussians._xyz = torch.nn.Parameter(gaussians.get_xyz[mask].requires_grad_(True))
    gaussians._scaling = torch.nn.Parameter(gaussians._scaling[mask].requires_grad_(True))
    gaussians._rotation = torch.nn.Parameter(gaussians._rotation[mask].requires_grad_(True))
    gaussians._features_dc = torch.nn.Parameter(gaussians._features_dc[mask].requires_grad_(True))
    gaussians._features_rest = torch.nn.Parameter(gaussians._features_rest[mask].requires_grad_(True))
    gaussians._opacity = torch.nn.Parameter(gaussians._opacity[mask].requires_grad_(True))
    gaussians.max_radii2D = gaussians.max_radii2D[mask]


def _filter_scene_info_points_for_unit(scene_info, args):
    point_source = getattr(args, "unit_init_point_source", "all")
    if point_source == "core":
        point_membership_path = f"{_partition_base_path(args)}_core_points.npy"
    elif point_source == "all":
        point_membership_path = f"{_partition_base_path(args)}_points.npy"
    else:
        raise ValueError(f"Unknown unit_init_point_source: {point_source}")
    if not os.path.exists(point_membership_path):
        raise FileNotFoundError(f"Missing unit point membership file: {point_membership_path}")
    if scene_info.point_cloud is None:
        raise ValueError("Cannot filter unit point cloud because scene_info.point_cloud is None.")

    point_membership = np.load(point_membership_path, mmap_mode="r")
    if args.block_id >= point_membership.shape[1]:
        raise ValueError(
            f"Invalid block_id {args.block_id} for point membership with shape {point_membership.shape}"
        )
    point_mask = np.asarray(point_membership[:, args.block_id], dtype=bool).copy()
    if point_mask.shape[0] != scene_info.point_cloud.points.shape[0]:
        raise ValueError(
            "Unit point membership length does not match loaded point cloud: "
            f"{point_mask.shape[0]} vs {scene_info.point_cloud.points.shape[0]}"
        )

    filter_mode = getattr(args, "unit_init_point_filter_mode", "membership")
    if filter_mode == "membership":
        pass
    elif filter_mode == "membership_and_bounds":
        unit_bounds = _expand_unit_bounds(_load_unit_bounds(args), args)
        point_mask &= _bounds_mask_numpy(scene_info.point_cloud.points, unit_bounds)
    else:
        raise ValueError(f"Unknown unit_init_point_filter_mode: {filter_mode}")

    if not point_mask.any():
        raise ValueError(
            f"Unit point membership for block_id {args.block_id} is empty after {filter_mode} filtering."
        )

    filtered_pcd = BasicPointCloud(
        points=scene_info.point_cloud.points[point_mask],
        colors=scene_info.point_cloud.colors[point_mask],
        normals=scene_info.point_cloud.normals[point_mask],
    )
    filtered_scene_info = SceneInfo(
        point_cloud=filtered_pcd,
        train_cameras=scene_info.train_cameras,
        test_cameras=scene_info.test_cameras,
        nerf_normalization=scene_info.nerf_normalization,
        ply_path=scene_info.ply_path,
    )
    print(
        f"Filtered unit point cloud ({point_source}, {filter_mode}): "
        f"{point_mask.sum()} / {point_mask.shape[0]} points."
    )
    return filtered_scene_info, filtered_pcd


class Scene:

    gaussians : GaussianModel

    def __init__(self, args : ModelParams, gaussians : GaussianModel, load_iteration=None, shuffle=True, resolution_scales=[1.0]):
        """b
        :param path: Path to colmap scene main folder.
        """
        self.model_path = args.model_path
        self.loaded_iter = None
        self.gaussians = gaussians

        if load_iteration:
            if load_iteration == -1:
                self.loaded_iter = searchForMaxIteration(os.path.join(self.model_path, "point_cloud"))
            else:
                self.loaded_iter = load_iteration
            print("Loading trained model at iteration {}".format(self.loaded_iter))

        self.train_cameras = {}
        self.test_cameras = {}

        if os.path.exists(os.path.join(args.source_path, "sparse")):
            scene_info = sceneLoadTypeCallbacks["Colmap"](args.source_path, args.images, args.eval)
        elif os.path.exists(os.path.join(args.source_path, "transforms_train.json")):
            print("Found transforms_train.json file, assuming Blender data set!")
            scene_info = sceneLoadTypeCallbacks["Blender"](args.source_path, args.white_background, args.eval)
        else:
            assert False, "Could not recognize scene type!"

        if not self.loaded_iter:
            with open(scene_info.ply_path, 'rb') as src_file, open(os.path.join(self.model_path, "input.ply") , 'wb') as dest_file:
                dest_file.write(src_file.read())
            json_cams = []
            camlist = []
            if scene_info.test_cameras:
                camlist.extend(scene_info.test_cameras)
            if scene_info.train_cameras:
                camlist.extend(scene_info.train_cameras)
            for id, cam in enumerate(camlist):
                json_cams.append(camera_to_JSON(id, cam))
            with open(os.path.join(self.model_path, "cameras.json"), 'w') as file:
                json.dump(json_cams, file)

        if shuffle:
            random.shuffle(scene_info.train_cameras)  # Multi-res consistent random shuffcameras_extentling
            random.shuffle(scene_info.test_cameras)  # Multi-res consistent random shuffling

        self.cameras_extent = scene_info.nerf_normalization["radius"]

        for resolution_scale in resolution_scales:
            print("Loading Training Cameras")
            self.train_cameras[resolution_scale] = cameraList_from_camInfos(scene_info.train_cameras, resolution_scale, args)
            print("Loading Test Cameras")
            self.test_cameras[resolution_scale] = cameraList_from_camInfos(scene_info.test_cameras, resolution_scale, args)

        if self.loaded_iter:
            self.gaussians.load_ply(os.path.join(self.model_path,
                                                           "point_cloud",
                                                           "iteration_" + str(self.loaded_iter),
                                                           "point_cloud.ply"))
        else:
            self.gaussians.create_from_pcd(scene_info.point_cloud, self.cameras_extent)

    def save(self, iteration):
        point_cloud_path = os.path.join(self.model_path, "point_cloud/iteration_{}".format(iteration))
        self.gaussians.save_ply(os.path.join(point_cloud_path, "point_cloud.ply"))

    def getTrainCameras(self, scale=1.0):
        return self.train_cameras[scale]

    def getTestCameras(self, scale=1.0):
        return self.test_cameras[scale]
    
class LargeScene(Scene):
    def __init__(self, args : ModelParams, gaussians : GaussianModel, load_iteration=None, load_vq=False, shuffle=True, resolution_scales=[1.0]):
        """b
        :param path: Path to colmap scene main folder.
        """
        self.model_path = args.model_path
        self.loaded_iter = None
        self.load_vq = load_vq
        self.gaussians = gaussians
        self.pretrain_path = args.pretrain_path

        if load_iteration:
            if load_iteration == -1:
                self.loaded_iter = searchForMaxIteration(os.path.join(self.model_path, "point_cloud"))
            else:
                self.loaded_iter = load_iteration
            print("Loading trained model at iteration {}".format(self.loaded_iter))

        self.train_cameras = {}
        self.test_cameras = {}

        if args.block_id >= 0:
            partition = np.load(os.path.join(args.source_path, "data_partitions", f"{args.partition_name}.npy"))[:, args.block_id]
            if args.aabb is None and not _is_colmap_unit_partition(args):
                args.aabb = np.load(os.path.join(args.source_path, "data_partitions", f"{args.partition_name}_aabb.npy")).tolist()
            print(f"Using Partition File {args.partition_name}.npy")
        else:
            partition = None

        if os.path.exists(os.path.join(args.source_path, "sparse")):
            scene_info = sceneLoadTypeCallbacks["Colmap"](
                args.source_path,
                args.images,
                args.eval,
                args.llffhold,
                partition=partition,
                normalize_after_partition=_is_colmap_unit_partition(args),
            )
        elif os.path.exists(os.path.join(args.source_path, "transforms_train.json")):
            print("Found transforms_train.json file, assuming Blender data set!")
            scene_info = sceneLoadTypeCallbacks["Blender"](args.source_path, args.white_background, args.eval)
        else:
            assert False, "Could not recognize scene type!"

        unit_input_pcd = None
        if (
            args.block_id >= 0
            and _is_colmap_unit_partition(args)
            and getattr(args, "unit_init_point_filter", True)
        ):
            scene_info, unit_input_pcd = _filter_scene_info_points_for_unit(scene_info, args)

        if not self.loaded_iter:
            if unit_input_pcd is not None:
                input_ply_path = os.path.join(self.model_path, "input.ply")
                input_rgb = np.clip(unit_input_pcd.colors * 255.0, 0, 255).astype(np.uint8)
                storePly(input_ply_path, unit_input_pcd.points, input_rgb)
            else:
                with open(scene_info.ply_path, 'rb') as src_file, open(os.path.join(self.model_path, "input.ply") , 'wb') as dest_file:
                    dest_file.write(src_file.read())
            json_cams = []
            camlist = []
            if scene_info.test_cameras:
                camlist.extend(scene_info.test_cameras)
            if scene_info.train_cameras:
                camlist.extend(scene_info.train_cameras)
            for id, cam in enumerate(camlist):
                json_cams.append(camera_to_JSON(id, cam))
            with open(os.path.join(self.model_path, "cameras.json"), 'w') as file:
                json.dump(json_cams, file)

        if shuffle:
            random.shuffle(scene_info.train_cameras)  # Multi-res consistent random shuffcameras_extentling
            random.shuffle(scene_info.test_cameras)  # Multi-res consistent random shuffling

        self.cameras_extent = scene_info.nerf_normalization["radius"]
        self.train_cameras = scene_info.train_cameras
        self.test_cameras = scene_info.test_cameras

        if self.load_vq:
            self.gaussians.load_vq(self.model_path)
        elif self.loaded_iter:
            self.gaussians.load_ply(os.path.join(self.model_path,
                                                "point_cloud",
                                                "iteration_" + str(self.loaded_iter),
                                                "point_cloud.ply"))
        elif self.pretrain_path:
            self.gaussians.load_ply(os.path.join(self.pretrain_path, "point_cloud.ply"))
            grid_pretrain_filter_mode = getattr(args, "grid_pretrain_filter_mode", "none")
            if grid_pretrain_filter_mode not in {"none", "bounds"}:
                raise ValueError(f"Unknown grid_pretrain_filter_mode: {grid_pretrain_filter_mode}")
            if (
                args.block_id >= 0
                and _is_colmap_unit_partition(args)
                and getattr(args, "unit_pretrain_filter_mode", "bounds") == "bounds"
            ):
                unit_bounds = _expand_unit_bounds(_load_unit_bounds(args), args)
                unit_mask = _bounds_mask_tensor(self.gaussians.get_xyz, unit_bounds)
                if not unit_mask.any():
                    raise ValueError(f"Unit bounds filter removed all pretrained gaussians for block_id {args.block_id}.")
                print(f"Filtered pretrained gaussians: {unit_mask.sum()} / {unit_mask.shape[0]}.")
                _apply_gaussian_mask_in_place(self.gaussians, unit_mask)
            elif (
                args.block_id >= 0
                and not _is_colmap_unit_partition(args)
                and grid_pretrain_filter_mode == "bounds"
            ):
                padding = float(getattr(args, "grid_pretrain_filter_padding", 0.0))
                block_mask = _grid_block_mask_tensor(self.gaussians.get_xyz, args, padding=padding)
                if not block_mask.any():
                    raise ValueError(f"Grid bounds filter removed all pretrained gaussians for block_id {args.block_id}.")
                print(f"Filtered grid pretrained gaussians: {block_mask.sum()} / {block_mask.shape[0]}.")
                _apply_gaussian_mask_in_place(self.gaussians, block_mask)
            self.gaussians.spatial_lr_scale = self.cameras_extent
        else:
            if args.add_background_sphere:
                import math
                scene_center = -scene_info.nerf_normalization['translate']
                scene_radius = scene_info.nerf_normalization['radius']
                # build unit sphere points
                n_points = args.background_sphere_points
                samples = np.arange(n_points)
                y = 1 - (samples / float(n_points - 1)) * 2  # y goes from 1 to -1
                radius = np.sqrt(1 - y * y)  # radius at y
                phi = math.pi * (math.sqrt(5.) - 1.)  # golden angle in radians
                theta = phi * samples  # golden angle increment
                x = np.cos(theta) * radius
                z = np.sin(theta) * radius
                unit_sphere_points = np.concatenate([x[:, None], y[:, None], z[:, None]], axis=1)
                # build background sphere
                background_sphere_point_xyz = (unit_sphere_points * scene_radius * args.background_sphere_radius) + scene_center
                background_sphere_point_rgb = np.asarray(np.random.random(background_sphere_point_xyz.shape), dtype=np.float64)
                # add background sphere to scene
                scene_info = SceneInfo(
                    point_cloud=BasicPointCloud(
                                points=np.concatenate([scene_info.point_cloud.points, background_sphere_point_xyz], axis=0),
                                colors=np.concatenate([scene_info.point_cloud.colors, background_sphere_point_rgb], axis=0),
                                normals=np.zeros_like(background_sphere_point_xyz)),
                    train_cameras=scene_info.train_cameras,
                    test_cameras=scene_info.test_cameras,
                    nerf_normalization=scene_info.nerf_normalization,
                    ply_path=scene_info.ply_path)
                # increase prune extent
                # TODO: resize scene_extent without changing lr
                self.cameras_extent = scene_radius * args.background_sphere_radius * 1.0001

                print("added {} background sphere points, rescale prune extent from {} to {}".format(n_points, scene_radius, self.cameras_extent))

            self.gaussians.create_from_pcd(scene_info.point_cloud, self.cameras_extent)

    def prune_unit_bounds(self, args, iteration=None):
        if not (
            args.block_id >= 0
            and _is_colmap_unit_partition(args)
            and getattr(args, "unit_train_prune_mode", "none") == "bounds"
        ):
            return 0

        xyz = self.gaussians.get_xyz
        inside_mask = _unit_bounds_mask_tensor(xyz, args)
        prune_mask = ~inside_mask
        prune_count = int(prune_mask.sum().item())
        if prune_count == 0:
            return 0
        if not inside_mask.any():
            raise ValueError(
                f"Unit bounds train prune would remove all gaussians for block_id {args.block_id}."
            )

        before_count = int(xyz.shape[0])
        self.gaussians.prune_points(prune_mask)
        iteration_text = f" at iter {iteration}" if iteration is not None else ""
        print(
            f"Pruned {prune_count} / {before_count} gaussians outside unit bounds"
            f"{iteration_text} for block_id {args.block_id}."
        )
        return prune_count
    
    def save(self, iteration, args=None):
        point_cloud_path = os.path.join(self.model_path, "point_cloud/iteration_{}".format(iteration))

        if args.block_id >= 0:
            if _is_colmap_unit_partition(args):
                xyz_org = self.gaussians.get_xyz
                save_filter_mode = getattr(args, "unit_save_filter_mode", "all")
                if save_filter_mode == "bounds":
                    block_mask = _unit_bounds_mask_tensor(xyz_org, args)
                    if not block_mask.any():
                        raise ValueError(f"Unit bounds save filter removed all gaussians for block_id {args.block_id}.")
                    masked_gaussians = _copy_gaussian_subset(self.gaussians, block_mask)
                elif save_filter_mode == "all":
                    block_mask = torch.ones((xyz_org.shape[0],), dtype=torch.bool, device=xyz_org.device)
                    masked_gaussians = _copy_gaussian_subset(self.gaussians, block_mask)
                else:
                    raise ValueError(f"Unknown unit_save_filter_mode: {save_filter_mode}")

                block_point_cloud_path = os.path.join(self.model_path, "point_cloud_blocks/scale_1.0/iteration_{}".format(iteration))
                masked_gaussians.save_ply(os.path.join(block_point_cloud_path, "point_cloud.ply"))

                if args.save_block_only:
                    return

                self.gaussians.save_ply(os.path.join(point_cloud_path, "point_cloud.ply"))
                return

            xyz_org = self.gaussians.get_xyz
            if len(args.aabb) == 4:
                aabb = [args.aabb[0], args.aabb[1], xyz_org[:, -1].min(), 
                        args.aabb[2], args.aabb[3], xyz_org[:, -1].max()]
            elif len(args.aabb) == 6:
                aabb = args.aabb
            else:
                assert False, "Unknown aabb format!"
            aabb = torch.tensor(aabb, dtype=torch.float32, device=xyz_org.device)
            xyz_contracted = self.contract_to_unisphere(xyz_org, aabb, ord=torch.inf)
            block_id_z = args.block_id // (args.block_dim[0] * args.block_dim[1])
            block_id_y = (args.block_id % (args.block_dim[0] * args.block_dim[1])) // args.block_dim[0]
            block_id_x = (args.block_id % (args.block_dim[0] * args.block_dim[1])) % args.block_dim[0]

            min_x, max_x = float(block_id_x) / args.block_dim[0], float(block_id_x + 1) / args.block_dim[0]
            min_y, max_y = float(block_id_y) / args.block_dim[1], float(block_id_y + 1) / args.block_dim[1]
            min_z, max_z = float(block_id_z) / args.block_dim[2], float(block_id_z + 1) / args.block_dim[2]

            block_mask = (xyz_contracted[:, 0] >= min_x) & (xyz_contracted[:, 0] < max_x)  \
                        & (xyz_contracted[:, 1] >= min_y) & (xyz_contracted[:, 1] < max_y) \
                        & (xyz_contracted[:, 2] >= min_z) & (xyz_contracted[:, 2] < max_z)
            
            sh_degree = self.gaussians.max_sh_degree
            masked_gaussians = GaussianModel(sh_degree)
            masked_gaussians._xyz = self.gaussians.get_xyz[block_mask]
            masked_gaussians._scaling = self.gaussians._scaling[block_mask]
            masked_gaussians._rotation = self.gaussians._rotation[block_mask]
            masked_gaussians._features_dc = self.gaussians._features_dc[block_mask]
            masked_gaussians._features_rest = self.gaussians._features_rest[block_mask]
            masked_gaussians._opacity = self.gaussians._opacity[block_mask]
            masked_gaussians.max_radii2D = self.gaussians.max_radii2D[block_mask]

            block_point_cloud_path = os.path.join(self.model_path, "point_cloud_blocks/scale_1.0/iteration_{}".format(iteration))
            masked_gaussians.save_ply(os.path.join(block_point_cloud_path, "point_cloud.ply"))

            if args.save_block_only:
                return
            
        self.gaussians.save_ply(os.path.join(point_cloud_path, "point_cloud.ply"))
    
    def getTrainCameras(self):
        return self.train_cameras

    def getTestCameras(self):
        return self.test_cameras

    def contract_to_unisphere(self,
        x: torch.Tensor,
        aabb: torch.Tensor,
        ord: float = 2,
        eps: float = 1e-6,
        derivative: bool = False,
    ):
        aabb_min, aabb_max = torch.split(aabb, 3, dim=-1)
        x = (x - aabb_min) / (aabb_max - aabb_min)
        x = x * 2 - 1  # aabb is at [-1, 1]
        mag = torch.linalg.norm(x, ord=ord, dim=-1, keepdim=True)
        mask = mag.squeeze(-1) > 1

        if derivative:
            dev = (2 * mag - 1) / mag**2 + 2 * x**2 * (
                1 / mag**3 - (2 * mag - 1) / mag**4
            )
            dev[~mask] = 1.0
            dev = torch.clamp(dev, min=eps)
            return dev
        else:
            x[mask] = (2 - 1 / mag[mask]) * (x[mask] / mag[mask])
            x = x / 4 + 0.5  # [-inf, inf] is at [0, 1]
            return x
