import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from transforms3d.quaternions import mat2quat


TRAIN_BLOCKS = [f"block_{index}" for index in range(1, 11)]
TEST_BLOCKS = ["block_1_test"]


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare MatrixCity small_city aerial for CityGaussianV1")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scale", type=float, default=0.01)
    parser.add_argument("--point-cloud", type=Path, default=None)
    parser.add_argument("--link-mode", choices=["symlink", "copy"], default="symlink")
    return parser.parse_args()


def read_png_size(path: Path) -> tuple[int, int]:
    import struct

    with path.open("rb") as handle:
        signature = handle.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not a PNG file: {path}")
        chunk_len = struct.unpack(">I", handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b"IHDR":
            raise ValueError(f"Invalid PNG header: {path}")
        width, height = struct.unpack(">II", handle.read(8))
        if chunk_len < 13:
            raise ValueError(f"Invalid IHDR length for {path}")
    return width, height


def resolve_point_cloud(raw_dir: Path, point_cloud: Path | None) -> Path:
    if point_cloud is not None:
        if not point_cloud.exists():
            raise FileNotFoundError(point_cloud)
        return point_cloud

    candidates = sorted(raw_dir.glob("*.ply"))
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one point cloud under {raw_dir}, found {len(candidates)}"
        )
    return candidates[0]


def ensure_clean_link(path: Path, source: Path, link_mode: str):
    if path.exists() or path.is_symlink():
        if path.is_symlink() and path.resolve() == source.resolve():
            return
        raise FileExistsError(f"{path} already exists; remove it first if you want to rebuild")

    if link_mode == "symlink":
        path.symlink_to(source)
    else:
        import shutil

        shutil.copy2(source, path)


def write_cameras_txt(path: Path, width: int, height: int, fov_x: float):
    fx = 0.5 * width / math.tan(0.5 * fov_x)
    fy = fx
    cx = width / 2.0
    cy = height / 2.0

    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Camera list with one line of data per camera:\n")
        handle.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        handle.write("# Number of cameras: 1\n")
        handle.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")

    return {
        "w": width,
        "h": height,
        "fl_x": fx,
        "fl_y": fy,
        "cx": cx,
        "cy": cy,
        "camera_angle_x": fov_x,
    }


def convert_rot_mat_to_c2w(rot_mat: list[list[float]], scale: float) -> np.ndarray:
    c2w = np.array(rot_mat, dtype=np.float64)
    c2w[:3, :3] *= 100.0
    c2w[:3, 3] *= scale
    return c2w


def write_images_txt(path: Path, frames: list[dict]):
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Image list with two lines of data per image:\n")
        handle.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        handle.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        handle.write(f"# Number of images: {len(frames)}\n")

        for index, frame in enumerate(frames, start=1):
            c2w = np.array(frame["transform_matrix"], dtype=np.float64)
            c2w[:3, 1:3] *= -1
            w2c = np.linalg.inv(c2w)
            qw, qx, qy, qz = mat2quat(w2c[:3, :3])
            tx, ty, tz = w2c[:3, 3]
            handle.write(
                f"{index} {qw} {qx} {qy} {qz} {tx} {ty} {tz} 1 {frame['image_name']}\n\n"
            )


def write_empty_points3d(path: Path):
    with path.open("w", encoding="utf-8") as handle:
        handle.write("")


def prepare_split(
    raw_dir: Path,
    split_blocks: list[str],
    output_path: Path,
    point_cloud_path: Path,
    scale: float,
    link_mode: str,
):
    images_dir = output_path / "images"
    sparse_dir = output_path / "sparse" / "0"
    input_dir = output_path / "input"
    manifest_path = output_path / "transforms.json"

    images_dir.mkdir(parents=True, exist_ok=True)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        input_dir.symlink_to(images_dir.name)

    fov_x = None
    width = None
    height = None
    manifest_frames = []
    mapping = []
    image_counter = 0

    for block_name in split_blocks:
        block_dir = raw_dir / block_name
        transforms_path = block_dir / "transforms_origin.json"
        with transforms_path.open("r", encoding="utf-8") as handle:
            transforms = json.load(handle)

        if fov_x is None:
            fov_x = transforms["camera_angle_x"]
        elif abs(fov_x - transforms["camera_angle_x"]) > 1e-9:
            raise ValueError(f"Inconsistent FOV in {transforms_path}")

        probe_index = transforms["frames"][0]["frame_index"]
        probe_image = block_dir / "rgb" / f"{probe_index:04d}.png"
        current_width, current_height = read_png_size(probe_image)
        if width is None:
            width, height = current_width, current_height
        elif (width, height) != (current_width, current_height):
            raise ValueError(f"Inconsistent image size in {transforms_path}")

        for frame in transforms["frames"]:
            frame_index = frame["frame_index"]
            source_image = block_dir / "rgb" / f"{frame_index:04d}.png"
            if not source_image.exists():
                raise FileNotFoundError(source_image)

            image_name = f"{image_counter:05d}.png"
            image_path = images_dir / image_name
            ensure_clean_link(image_path, source_image, link_mode)

            c2w = convert_rot_mat_to_c2w(frame["rot_mat"], scale)
            manifest_frames.append(
                {
                    "file_path": f"images/{image_name[:-4]}",
                    "image_name": image_name,
                    "transform_matrix": c2w.tolist(),
                }
            )
            mapping.append(
                {
                    "image_name": image_name,
                    "source_block": block_name,
                    "source_frame_index": frame_index,
                    "source_image": str(source_image),
                }
            )
            image_counter += 1

    intrinsic = write_cameras_txt(sparse_dir / "cameras.txt", width, height, fov_x)
    write_images_txt(sparse_dir / "images.txt", manifest_frames)
    write_empty_points3d(sparse_dir / "points3D.txt")

    point_cloud_link = sparse_dir / "points3D.ply"
    if not point_cloud_link.exists() and not point_cloud_link.is_symlink():
        point_cloud_link.symlink_to(point_cloud_path)

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                **intrinsic,
                "frames": [
                    {
                        "file_path": frame["file_path"],
                        "transform_matrix": frame["transform_matrix"],
                    }
                    for frame in manifest_frames
                ],
            },
            handle,
            indent=2,
        )

    with (output_path / "mapping.json").open("w", encoding="utf-8") as handle:
        json.dump(mapping, handle, indent=2)

    return {
        "image_count": image_counter,
        "width": width,
        "height": height,
        "fov_x": fov_x,
        "point_cloud": str(point_cloud_path),
    }


def main():
    args = parse_args()
    raw_dir = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    point_cloud = resolve_point_cloud(raw_dir, args.point_cloud)

    pose_dir = output_dir / "pose" / "block_all"
    train_dir = output_dir / "train" / "block_all"
    test_dir = output_dir / "test" / "block_all_test"

    pose_dir.mkdir(parents=True, exist_ok=True)

    train_stats = prepare_split(
        raw_dir=raw_dir,
        split_blocks=TRAIN_BLOCKS,
        output_path=train_dir,
        point_cloud_path=point_cloud,
        scale=args.scale,
        link_mode=args.link_mode,
    )
    test_stats = prepare_split(
        raw_dir=raw_dir,
        split_blocks=TEST_BLOCKS,
        output_path=test_dir,
        point_cloud_path=point_cloud,
        scale=args.scale,
        link_mode=args.link_mode,
    )

    with (pose_dir / "transforms_train.json").open("w", encoding="utf-8") as handle:
        json.dump(json.load((train_dir / "transforms.json").open("r", encoding="utf-8")), handle, indent=2)
    with (pose_dir / "transforms_test.json").open("w", encoding="utf-8") as handle:
        json.dump(json.load((test_dir / "transforms.json").open("r", encoding="utf-8")), handle, indent=2)

    summary = {
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "train": train_stats,
        "test": test_stats,
    }
    with (output_dir / "prep_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
