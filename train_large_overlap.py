import os
import sys
import time
from argparse import ArgumentParser

import torch
import yaml
from tqdm import tqdm

from gaussian_renderer import network_gui, render, render_large
from scene import LargeScene
from scene.datasets import CacheDataLoader, GSDataset
from train_large import prepare_output_and_logger, training_report
from utils.general_utils import parse_cfg, safe_state
from utils.large_utils import contract_to_unisphere
from utils.loss_utils import l1_loss, ssim
from utils.overlap_utils import (
    block_filtering_overlap,
    build_masked_gaussians,
    classify_zones,
    compute_overlap_bounds,
    normalize_aabb,
)


def compute_zone_masks(gaussians, dataset):
    if dataset.block_id < 0 or getattr(dataset, "overlap_ratio", 0.0) <= 0:
        return None, None, None

    aabb = normalize_aabb(dataset.aabb, gaussians.get_xyz)
    xyz_contracted = contract_to_unisphere(gaussians.get_xyz, aabb, ord=torch.inf)
    core_bounds, expanded_bounds = compute_overlap_bounds(
        dataset.block_id,
        dataset.block_dim,
        dataset.overlap_ratio,
        device=xyz_contracted.device,
        dtype=xyz_contracted.dtype,
    )
    return classify_zones(xyz_contracted, core_bounds, expanded_bounds)


def log_zone_summary(iteration, core_mask, overlap_mask, outside_mask):
    total = core_mask.numel()
    core_count = int(core_mask.sum().item())
    overlap_count = int(overlap_mask.sum().item())
    outside_count = int(outside_mask.sum().item())
    print(
        f"[ITER {iteration}] zone summary: "
        f"core={core_count}/{total}, overlap={overlap_count}/{total}, outside={outside_count}/{total}"
    )


def freeze_overlap_gradients(gaussians, overlap_mask):
    if overlap_mask is None or not torch.any(overlap_mask):
        return

    for param_group in gaussians.optimizer.param_groups:
        param = param_group["params"][0]
        if param.grad is None:
            continue
        if param.grad.shape[0] != overlap_mask.shape[0]:
            continue
        param.grad[overlap_mask] = 0.0


def save_overlap_scene(scene, iteration, dataset):
    scene.save(iteration, dataset)
    if dataset.block_id < 0 or getattr(dataset, "overlap_ratio", 0.0) <= 0:
        return

    overlap_mask = block_filtering_overlap(
        dataset.block_id,
        scene.gaussians.get_xyz,
        dataset.aabb,
        dataset.block_dim,
        dataset.overlap_ratio,
    )
    masked_gaussians = build_masked_gaussians(scene.gaussians, overlap_mask)
    overlap_path = os.path.join(scene.model_path, "point_cloud_overlap", f"iteration_{iteration}", "point_cloud.ply")
    masked_gaussians.save_ply(overlap_path)


def training(dataset, opt, pipe, testing_iterations, saving_iterations, refilter_iterations, checkpoint_iterations, checkpoint, max_cache_num, debug_from):
    first_iter = 0
    log_writer, image_logger = prepare_output_and_logger(dataset)

    modules = __import__("scene")
    model_config = dataset.model_config
    gaussians = getattr(modules, model_config["name"])(dataset.sh_degree, **model_config["kwargs"])
    scene = LargeScene(dataset, gaussians)
    gs_dataset = GSDataset(scene.getTrainCameras(), scene, dataset, pipe)
    if len(gs_dataset) > 0:
        print(f"Using maximum cache size of {max_cache_num} for {len(gs_dataset)} training images")
        data_loader = CacheDataLoader(gs_dataset, max_cache_num=max_cache_num, seed=42, batch_size=1, shuffle=True, num_workers=8)
    gaussians.training_setup(opt)
    if checkpoint:
        model_params, first_iter = torch.load(checkpoint)
        gaussians.restore(model_params, opt)

    bg_color = [1, 1, 1] if dataset.white_background else [0, 0, 0]
    background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")

    iter_start = torch.cuda.Event(enable_timing=True)
    iter_end = torch.cuda.Event(enable_timing=True)

    ema_loss_for_log = 0.0
    ema_time_render = 0.0
    ema_time_loss = 0.0
    ema_time_densify = 0.0
    progress_bar = tqdm(range(first_iter, opt.iterations), desc="Training progress")
    first_iter += 1
    iteration = first_iter

    core_mask, overlap_mask, outside_mask = compute_zone_masks(gaussians, dataset)
    if overlap_mask is not None:
        log_zone_summary(iteration, core_mask, overlap_mask, outside_mask)

    while iteration <= opt.iterations:
        if len(gs_dataset) == 0:
            print("No training data found")
            print(f"\n[ITER {iteration}] Saving Gaussians")
            save_overlap_scene(scene, iteration, dataset)
            break

        for cam_info, gt_image in data_loader:
            if network_gui.conn is None:
                network_gui.try_connect()
            while network_gui.conn is not None:
                try:
                    net_image_bytes = None
                    custom_cam, do_training, pipe.convert_SHs_python, pipe.compute_cov3D_python, keep_alive, scaling_modifer = network_gui.receive()
                    if custom_cam is not None:
                        net_image = render(custom_cam, gaussians, pipe, background, scaling_modifer)["render"]
                        net_image_bytes = memoryview(
                            (torch.clamp(net_image, min=0, max=1.0) * 255)
                            .byte()
                            .permute(1, 2, 0)
                            .contiguous()
                            .cpu()
                            .numpy()
                        )
                    network_gui.send(net_image_bytes, dataset.source_path)
                    if do_training and ((iteration < int(opt.iterations)) or not keep_alive):
                        break
                except Exception:
                    network_gui.conn = None

            iter_start.record()
            gaussians.update_learning_rate(iteration)

            if iteration % 1000 == 0:
                gaussians.oneupSHdegree()

            start = time.time()
            if (iteration - 1) == debug_from:
                pipe.debug = True
            render_pkg = render_large(cam_info, gaussians, pipe, background)
            image = render_pkg["render"]
            viewspace_point_tensor = render_pkg["viewspace_points"]
            visibility_filter = render_pkg["visibility_filter"]
            radii = render_pkg["radii"]
            end = time.time()
            ema_time_render = 0.4 * (end - start) + 0.6 * ema_time_render

            start = time.time()
            gt_image = gt_image.cuda()
            ll1 = l1_loss(image, gt_image)
            loss = (1.0 - opt.lambda_dssim) * ll1 + opt.lambda_dssim * (1.0 - ssim(image, gt_image))
            loss.backward()
            if (
                overlap_mask is not None
                and getattr(dataset, "overlap_freeze", False)
                and iteration > getattr(dataset, "freeze_after_iter", 3000)
            ):
                freeze_overlap_gradients(gaussians, overlap_mask)
            end = time.time()
            ema_time_loss = 0.4 * (end - start) + 0.6 * ema_time_loss

            iter_end.record()

            with torch.no_grad():
                ema_loss_for_log = 0.4 * loss.item() + 0.6 * ema_loss_for_log
                if iteration % 10 == 0:
                    progress_bar.set_postfix({"Loss": f"{ema_loss_for_log:.7f}"})
                    progress_bar.update(10)
                if iteration == opt.iterations:
                    progress_bar.close()

                grads = gaussians.xyz_gradient_accum / gaussians.denom
                grads[grads.isnan()] = 0.0
                ema_time = {
                    "render": ema_time_render,
                    "loss": ema_time_loss,
                    "densify": ema_time_densify,
                    "num_points": radii.shape[0],
                    "mean_grad": grads.mean().item(),
                }

                lr = {}
                for param_group in gaussians.optimizer.param_groups:
                    lr[param_group["name"]] = param_group["lr"]

                training_report(
                    dataset,
                    log_writer,
                    image_logger,
                    iteration,
                    ll1,
                    loss,
                    l1_loss,
                    ema_time,
                    lr,
                    iter_start.elapsed_time(iter_end),
                    testing_iterations,
                    scene,
                    render_large,
                    (pipe, background),
                )
                if iteration in saving_iterations:
                    print(f"\n[ITER {iteration}] Saving Gaussians")
                    save_overlap_scene(scene, iteration, dataset)
                if iteration in refilter_iterations:
                    print(f"\n[ITER {iteration}] Refiltering Training Data")
                    gs_dataset = GSDataset(scene.getTrainCameras(), scene, dataset, pipe)

                if iteration < opt.densify_until_iter:
                    gaussians.max_radii2D[visibility_filter] = torch.max(
                        gaussians.max_radii2D[visibility_filter],
                        radii[visibility_filter],
                    )
                    gaussians.add_densification_stats(viewspace_point_tensor, visibility_filter)

                    if iteration > opt.densify_from_iter and iteration % opt.densification_interval == 0:
                        start = time.time()
                        size_threshold = 20 if iteration > opt.opacity_reset_interval else None
                        gaussians.densify_and_prune(opt.densify_grad_threshold, 0.005, scene.cameras_extent, size_threshold)
                        core_mask, overlap_mask, outside_mask = compute_zone_masks(gaussians, dataset)
                        if overlap_mask is not None:
                            log_zone_summary(iteration, core_mask, overlap_mask, outside_mask)
                        end = time.time()
                        ema_time_densify = 0.4 * (end - start) + 0.6 * ema_time_densify

                    if iteration % opt.opacity_reset_interval == 0 or (dataset.white_background and iteration == opt.densify_from_iter):
                        gaussians.reset_opacity()

                if iteration < opt.iterations:
                    gaussians.optimizer.step()
                    gaussians.optimizer.zero_grad(set_to_none=True)

                if iteration in checkpoint_iterations:
                    print(f"\n[ITER {iteration}] Saving Checkpoint")
                    torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")

            iteration += 1
            if iteration >= opt.iterations:
                break


if __name__ == "__main__":
    parser = ArgumentParser(description="Overlap training script parameters")
    parser.add_argument("--config", type=str, required=True, help="train config file path")
    parser.add_argument("--ip", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6009)
    parser.add_argument("--debug_from", type=int, default=-1)
    parser.add_argument("--block_id", type=int, default=-1)
    parser.add_argument("--detect_anomaly", action="store_true", default=False)
    parser.add_argument("--test_iterations", nargs="+", type=int, default=[7000, 30000])
    parser.add_argument("--save_iterations", nargs="+", type=int, default=[7000, 30000])
    parser.add_argument("--refilter_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--checkpoint_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--start_checkpoint", type=str, default=None)
    parser.add_argument("--max_cache_num", type=int, default=512)
    args = parser.parse_args(sys.argv[1:])

    with open(args.config) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        lp, op, pp = parse_cfg(cfg, args)
        args.save_iterations.append(op.iterations)

    print("Optimizing " + lp.model_path)

    safe_state(args.quiet)

    network_gui.init(args.ip, args.port)
    torch.autograd.set_detect_anomaly(args.detect_anomaly)
    training(
        lp,
        op,
        pp,
        args.test_iterations,
        args.save_iterations,
        args.refilter_iterations,
        args.checkpoint_iterations,
        args.start_checkpoint,
        args.max_cache_num,
        args.debug_from,
    )

    print("\nTraining complete.")
