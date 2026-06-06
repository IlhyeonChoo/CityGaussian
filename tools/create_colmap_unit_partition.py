import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scene.colmap_loader import (
    qvec2rotmat,
    read_extrinsics_binary,
    read_extrinsics_text,
    read_next_bytes,
)


def image_sort_key(image_name: str) -> str:
    return PurePosixPath(image_name).name.rsplit(".", 1)[0]


def frame_number_from_name(image_name: str) -> int | None:
    stem = image_sort_key(image_name)
    matches = re.findall(r"\d+", stem)
    if not matches:
        return None
    return int(matches[-1])


def image_match_keys(image_name: str) -> tuple[str, str, str]:
    path_name = PurePosixPath(image_name).name
    stem = path_name.rsplit(".", 1)[0]
    return image_name, path_name, stem


def collect_unit_images(unit_path: Path, images_dir: str) -> dict[str, set[str]]:
    image_root = unit_path / images_dir
    if not image_root.is_dir():
        raise FileNotFoundError(f"Missing unit image directory: {image_root}")

    rel_paths = set()
    names = set()
    stems = set()
    for path in image_root.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(image_root).as_posix()
        rel_paths.add(rel_path)
        names.add(path.name)
        stems.add(path.stem)

    if not rel_paths:
        raise ValueError(f"No images found in unit image directory: {image_root}")
    return {"rel_paths": rel_paths, "names": names, "stems": stems}


def matches_unit(image_name: str, unit_images: dict[str, set[str]]) -> bool:
    rel_name, basename, stem = image_match_keys(image_name)
    return (
        rel_name in unit_images["rel_paths"]
        or basename in unit_images["names"]
        or stem in unit_images["stems"]
    )


def read_combined_images(source_path: Path, sparse_dir: str):
    sparse_path = source_path / sparse_dir
    images_bin = sparse_path / "images.bin"
    images_txt = sparse_path / "images.txt"
    if images_bin.exists():
        return read_extrinsics_binary(str(images_bin)), images_bin
    if images_txt.exists():
        return read_extrinsics_text(str(images_txt)), images_txt
    raise FileNotFoundError(f"Missing COLMAP images.bin/images.txt under {sparse_path}")


def count_points3d_text(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                count += 1
    return count


def iter_points3d_binary(path: Path):
    with path.open("rb") as handle:
        point_count = read_next_bytes(handle, 8, "Q")[0]
        for point_index in range(point_count):
            point_props = read_next_bytes(handle, 43, "QdddBBBd")
            xyz = np.asarray(point_props[1:4], dtype=np.float64)
            track_length = read_next_bytes(handle, 8, "Q")[0]
            if track_length > 0:
                track = read_next_bytes(handle, 8 * track_length, "ii" * track_length)
                image_ids = np.asarray(track[0::2], dtype=np.int64)
            else:
                image_ids = np.empty((0,), dtype=np.int64)
            yield point_index, xyz, image_ids


def iter_points3d_text(path: Path):
    point_index = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            elems = line.split()
            xyz = np.asarray(tuple(map(float, elems[1:4])), dtype=np.float64)
            image_ids = np.asarray(tuple(map(int, elems[8::2])), dtype=np.int64)
            yield point_index, xyz, image_ids
            point_index += 1


def load_point_iterator(source_path: Path, sparse_dir: str):
    sparse_path = source_path / sparse_dir
    points_bin = sparse_path / "points3D.bin"
    points_txt = sparse_path / "points3D.txt"
    if points_bin.exists():
        with points_bin.open("rb") as handle:
            point_count = read_next_bytes(handle, 8, "Q")[0]
        return point_count, iter_points3d_binary(points_bin), points_bin
    if points_txt.exists():
        return count_points3d_text(points_txt), iter_points3d_text(points_txt), points_txt
    raise FileNotFoundError(f"Missing COLMAP points3D.bin/points3D.txt under {sparse_path}")


def count_ply_vertices(path: Path) -> int:
    from plyfile import PlyData

    return len(PlyData.read(path)["vertex"])


def output_paths(source_path: Path, partition_name: str) -> dict[str, Path]:
    partition_dir = source_path / "data_partitions"
    return {
        "dir": partition_dir,
        "camera": partition_dir / f"{partition_name}.npy",
        "points": partition_dir / f"{partition_name}_points.npy",
        "core_points": partition_dir / f"{partition_name}_core_points.npy",
        "bounds": partition_dir / f"{partition_name}_bounds.npy",
        "rows": partition_dir / f"{partition_name}_rows.json",
        "units": partition_dir / f"{partition_name}_units.json",
        "summary": partition_dir / f"{partition_name}_summary.json",
    }


def assert_outputs_available(paths: dict[str, Path], write_points: bool, overwrite: bool) -> None:
    targets = [paths["camera"], paths["bounds"], paths["rows"], paths["units"], paths["summary"]]
    if write_points:
        targets.extend([paths["points"], paths["core_points"]])
    existing = [path for path in targets if path.exists()]
    if existing and not overwrite:
        joined = "\n".join(str(path) for path in existing)
        raise FileExistsError(f"Refusing to overwrite existing partition artifacts:\n{joined}")


def build_camera_partition(images, unit_image_sets):
    sorted_images = sorted(images.values(), key=lambda image: image_sort_key(image.name))
    camera_mask = np.zeros((len(sorted_images), len(unit_image_sets)), dtype=np.bool_)
    image_rows = []

    for row, image in enumerate(sorted_images):
        _, basename, sort_key = image_match_keys(image.name)
        for unit_id, unit_images in enumerate(unit_image_sets):
            camera_mask[row, unit_id] = matches_unit(image.name, unit_images)
        unit_ids = np.flatnonzero(camera_mask[row]).astype(int).tolist()
        image_rows.append({
            "row": row,
            "image_id": int(image.id),
            "raw_name": image.name,
            "basename": basename,
            "sort_key": sort_key,
            "source_unit_ids": unit_ids,
            "unit_ids": unit_ids,
        })

    return camera_mask, image_rows


def build_image_id_to_units(camera_mask: np.ndarray, image_rows: list[dict]) -> dict[int, np.ndarray]:
    return {row["image_id"]: camera_mask[row["row"]].copy() for row in image_rows}


def parse_range_file(range_file: Path) -> dict[str, list[tuple[int, int]]]:
    ranges_by_name: dict[str, list[tuple[int, int]]] = {}
    for line_number, line in enumerate(range_file.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            raise ValueError(f"Invalid range line {line_number}: {line}")
        name, spec = stripped.split(":", 1)
        unit_name = name.strip()
        ranges = []
        for start, end in re.findall(r"(\d+)\s*~\s*(\d+)", spec):
            start_num = int(start)
            end_num = int(end)
            if end_num < start_num:
                raise ValueError(f"Invalid descending range on line {line_number}: {start} ~ {end}")
            ranges.append((start_num, end_num))
        if not ranges:
            raise ValueError(f"No frame ranges found on line {line_number}: {line}")
        ranges_by_name[unit_name] = ranges
    return ranges_by_name


def frame_in_ranges(frame_number: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= frame_number <= end for start, end in ranges)


def is_passage_unit(unit_name: str) -> bool:
    return unit_name.lower().startswith("passage")


def build_range_camera_partition(
    images,
    range_specs: dict[str, list[tuple[int, int]]],
    unit_names: list[str],
    overlap_policy: str,
) -> tuple[np.ndarray, list[dict], dict]:
    missing_units = [unit_name for unit_name in unit_names if unit_name not in range_specs]
    if missing_units:
        raise ValueError(f"Range file is missing requested units: {missing_units}")
    if overlap_policy != "single_owner":
        raise ValueError(f"Unknown range overlap policy: {overlap_policy}")

    sorted_images = sorted(images.values(), key=lambda image: image_sort_key(image.name))
    candidate_mask = np.zeros((len(sorted_images), len(unit_names)), dtype=np.bool_)
    image_rows = []
    missing_frame_numbers = []

    for row, image in enumerate(sorted_images):
        _, basename, sort_key = image_match_keys(image.name)
        frame_number = frame_number_from_name(image.name)
        if frame_number is None:
            missing_frame_numbers.append(basename)
            candidate_ids: list[int] = []
        else:
            for unit_id, unit_name in enumerate(unit_names):
                candidate_mask[row, unit_id] = frame_in_ranges(frame_number, range_specs[unit_name])
            candidate_ids = np.flatnonzero(candidate_mask[row]).astype(int).tolist()
        image_rows.append({
            "row": row,
            "image_id": int(image.id),
            "raw_name": image.name,
            "basename": basename,
            "sort_key": sort_key,
            "frame_number": frame_number,
            "source_unit_ids": candidate_ids,
            "range_candidate_unit_ids": candidate_ids,
            "unit_ids": candidate_ids,
        })

    centers, _ = compute_camera_centers(images, image_rows)
    medians = np.zeros((len(unit_names), 3), dtype=np.float64)
    for unit_id in range(len(unit_names)):
        row_indices = np.flatnonzero(candidate_mask[:, unit_id])
        if row_indices.size == 0:
            raise ValueError(f"No cameras matched range unit {unit_names[unit_id]}")
        medians[unit_id] = np.median(centers[row_indices], axis=0)

    final_mask = np.zeros_like(candidate_mask)
    overlap_rows = []
    passage_priority_count = 0
    nearest_median_count = 0

    for row in image_rows:
        row_index = row["row"]
        candidate_ids = np.flatnonzero(candidate_mask[row_index]).astype(int).tolist()
        if not candidate_ids:
            row["unit_ids"] = []
            continue
        if len(candidate_ids) == 1:
            owner_id = candidate_ids[0]
            row["unit_ids"] = [owner_id]
            final_mask[row_index, owner_id] = True
            continue

        passage_ids = [unit_id for unit_id in candidate_ids if is_passage_unit(unit_names[unit_id])]
        reduced_ids = passage_ids or candidate_ids
        if passage_ids:
            passage_priority_count += 1
        if len(reduced_ids) == 1:
            owner_id = reduced_ids[0]
            reason = "passage_priority" if passage_ids else "single_candidate_after_priority"
        else:
            distances = [
                (float(np.linalg.norm(centers[row_index] - medians[unit_id])), unit_id)
                for unit_id in reduced_ids
            ]
            distances.sort(key=lambda item: (item[0], item[1]))
            owner_id = distances[0][1]
            nearest_median_count += 1
            reason = "nearest_passage_median" if passage_ids else "nearest_unit_median"

        row["unit_ids"] = [owner_id]
        row["range_overlap_resolution"] = {
            "candidate_unit_ids": candidate_ids,
            "candidate_unit_names": [unit_names[unit_id] for unit_id in candidate_ids],
            "reduced_unit_ids": reduced_ids,
            "assigned_unit_id": int(owner_id),
            "assigned_unit_name": unit_names[owner_id],
            "reason": reason,
        }
        overlap_rows.append(row["range_overlap_resolution"])
        final_mask[row_index, owner_id] = True

    stats = {
        "range_unit_names": unit_names,
        "range_specs": {
            unit_name: [[int(start), int(end)] for start, end in range_specs[unit_name]]
            for unit_name in unit_names
        },
        "range_file_labels": sorted(range_specs.keys()),
        "excluded_range_labels": sorted(set(range_specs.keys()) - set(unit_names)),
        "missing_frame_number_count": len(missing_frame_numbers),
        "missing_frame_number_samples": missing_frame_numbers[:10],
        "candidate_multi_unit_camera_count": int(np.count_nonzero(candidate_mask.sum(axis=1) > 1)),
        "candidate_camera_overlap_histogram": {
            str(count): int(np.count_nonzero(candidate_mask.sum(axis=1) == count))
            for count in range(int(candidate_mask.sum(axis=1).max(initial=0)) + 1)
        },
        "overlap_resolution_count": len(overlap_rows),
        "passage_priority_resolution_count": int(passage_priority_count),
        "nearest_median_resolution_count": int(nearest_median_count),
        "overlap_resolution_samples": overlap_rows[:20],
        "unit_center_medians": medians.tolist(),
    }
    return final_mask, image_rows, stats


def apply_shared_camera_policy(
    camera_mask: np.ndarray,
    image_rows: list[dict],
    shared_camera_policy: str,
    passage_splits: int,
    passage_prefix: str,
) -> tuple[np.ndarray, list[str]]:
    membership_counts = camera_mask.sum(axis=1)
    shared_rows = np.flatnonzero(membership_counts > 1)

    if shared_camera_policy == "keep":
        for row in image_rows:
            row["unit_ids"] = np.flatnonzero(camera_mask[row["row"]]).astype(int).tolist()
        return camera_mask, []

    if shared_camera_policy == "drop":
        final_mask = camera_mask.copy()
        final_mask[shared_rows] = False
        for row in image_rows:
            row["unit_ids"] = np.flatnonzero(final_mask[row["row"]]).astype(int).tolist()
        return final_mask, []

    if shared_camera_policy != "split":
        raise ValueError(f"Unknown shared_camera_policy: {shared_camera_policy}")

    if passage_splits <= 0:
        raise ValueError("--passage-splits must be positive when shared cameras are split.")
    if shared_rows.size < passage_splits:
        raise ValueError(
            f"Cannot split {shared_rows.size} shared cameras into {passage_splits} non-empty passage units."
        )

    source_unit_count = camera_mask.shape[1]
    final_mask = np.zeros((camera_mask.shape[0], source_unit_count + passage_splits), dtype=np.bool_)
    single_rows = membership_counts == 1
    final_mask[single_rows, :source_unit_count] = camera_mask[single_rows]

    for passage_id, row_indices in enumerate(np.array_split(shared_rows, passage_splits)):
        final_mask[row_indices, source_unit_count + passage_id] = True

    for row in image_rows:
        row["unit_ids"] = np.flatnonzero(final_mask[row["row"]]).astype(int).tolist()

    passage_names = [f"{passage_prefix}{idx + 1}" for idx in range(passage_splits)]
    return final_mask, passage_names


def compute_camera_centers(images, image_rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    centers = []
    observations = []
    for row in image_rows:
        image = images[row["image_id"]]
        rotation = qvec2rotmat(image.qvec)
        centers.append(-rotation.T @ image.tvec)
        observations.append(int(np.count_nonzero(np.asarray(image.point3D_ids) >= 0)))
    return np.asarray(centers, dtype=np.float64), np.asarray(observations, dtype=np.int64)


def filter_camera_outliers(
    images,
    camera_mask: np.ndarray,
    image_rows: list[dict],
    z_threshold: float,
    min_distance: float,
    distance_ratio: float,
) -> tuple[np.ndarray, list[dict]]:
    centers, observations = compute_camera_centers(images, image_rows)
    filtered_mask = camera_mask.copy()
    excluded = []

    for unit_id in range(filtered_mask.shape[1]):
        row_indices = np.flatnonzero(filtered_mask[:, unit_id])
        if row_indices.size < 50:
            continue

        unit_centers = centers[row_indices]
        unit_median = np.median(unit_centers, axis=0)
        distances = np.linalg.norm(unit_centers - unit_median, axis=1)
        median_distance = float(np.median(distances))
        mad = float(np.median(np.abs(distances - median_distance)))
        robust_scale = max(1.4826 * mad, 1e-6)
        robust_z = (distances - median_distance) / robust_scale
        distance_floor = max(float(min_distance), median_distance * float(distance_ratio))
        outlier_locals = np.flatnonzero((robust_z > z_threshold) & (distances > distance_floor))

        for local_idx in outlier_locals:
            row_index = int(row_indices[local_idx])
            row = image_rows[row_index]
            filtered_mask[row_index, unit_id] = False
            row.setdefault("excluded_unit_ids", []).append(int(unit_id))
            excluded.append(
                {
                    "row": row_index,
                    "image_id": int(row["image_id"]),
                    "raw_name": row["raw_name"],
                    "unit_id": int(unit_id),
                    "center": centers[row_index].tolist(),
                    "distance": float(distances[local_idx]),
                    "robust_z": float(robust_z[local_idx]),
                    "observations": int(observations[row_index]),
                }
            )

    for row in image_rows:
        row["unit_ids"] = np.flatnonzero(filtered_mask[row["row"]]).astype(int).tolist()

    return filtered_mask, excluded


def compute_bounds_from_points(unit_xyz: list[list[np.ndarray]], percentile: float):
    bounds = np.zeros((len(unit_xyz), 6), dtype=np.float32)
    raw_bounds = np.zeros((len(unit_xyz), 6), dtype=np.float32)
    for unit_id, xyz_values in enumerate(unit_xyz):
        if not xyz_values:
            raise ValueError(f"No core COLMAP points matched unit {unit_id}.")
        xyz = np.asarray(xyz_values, dtype=np.float64)
        raw_min = xyz.min(axis=0)
        raw_max = xyz.max(axis=0)
        if percentile > 0.0:
            bounds_min = np.percentile(xyz, percentile, axis=0)
            bounds_max = np.percentile(xyz, 100.0 - percentile, axis=0)
        else:
            bounds_min = raw_min
            bounds_max = raw_max
        bounds[unit_id] = np.concatenate([bounds_min, bounds_max]).astype(np.float32)
        raw_bounds[unit_id] = np.concatenate([raw_min, raw_max]).astype(np.float32)
    return bounds, raw_bounds


def build_point_partition(
    source_path: Path,
    sparse_dir: str,
    image_id_to_units,
    unit_count: int,
    bounds_percentile: float,
    point_filter_box: list[float] | None,
    core_point_policy: str,
):
    if core_point_policy not in {"per_observation", "single_owner"}:
        raise ValueError(f"Unknown core point policy: {core_point_policy}")

    point_count, point_iter, point_source = load_point_iterator(source_path, sparse_dir)
    point_membership = np.zeros((point_count, unit_count), dtype=np.bool_)
    core_point_membership = np.zeros((point_count, unit_count), dtype=np.bool_)
    point_filter_mask = np.ones((point_count,), dtype=np.bool_)
    core_xyz = [[] for _ in range(unit_count)]

    for point_index, xyz, image_ids in point_iter:
        if point_filter_box is not None:
            point_filter_mask[point_index] = (
                point_filter_box[0] <= xyz[0] <= point_filter_box[3]
                and point_filter_box[1] <= xyz[1] <= point_filter_box[4]
                and point_filter_box[2] <= xyz[2] <= point_filter_box[5]
            )
            if not point_filter_mask[point_index]:
                continue

        unit_mask = np.zeros((unit_count,), dtype=np.bool_)
        core_unit_mask = np.zeros((unit_count,), dtype=np.bool_)
        for image_id in image_ids:
            image_units = image_id_to_units.get(int(image_id))
            if image_units is not None:
                unit_mask |= image_units
                if core_point_policy == "per_observation" and image_units.sum() == 1:
                    core_unit_mask |= image_units
        if core_point_policy == "single_owner" and unit_mask.sum() == 1:
            core_unit_mask = unit_mask.copy()
        point_membership[point_index] = unit_mask
        core_point_membership[point_index] = core_unit_mask
        for unit_id in np.flatnonzero(core_unit_mask):
            core_xyz[unit_id].append(xyz)

    if point_filter_box is not None:
        point_membership = point_membership[point_filter_mask]
        core_point_membership = core_point_membership[point_filter_mask]

    core_counts = core_point_membership.sum(axis=0)
    empty_units = np.where(core_counts == 0)[0]
    if empty_units.size > 0:
        raise ValueError(f"No core COLMAP points matched units: {empty_units.tolist()}")

    bounds, raw_core_bounds = compute_bounds_from_points(core_xyz, bounds_percentile)
    return (
        point_membership,
        core_point_membership,
        bounds,
        raw_core_bounds,
        point_source,
        point_count,
        int(point_filter_mask.sum()),
    )


def summarize(
    source_path: Path,
    sparse_source: Path,
    partition_name: str,
    assignment_source: str,
    unit_names: list[str],
    unit_types: list[str],
    unit_paths: list[Path],
    unit_image_sets: list[dict[str, set[str]]],
    shared_camera_policy: str,
    range_file: Path | None,
    range_overlap_policy: str,
    range_stats: dict | None,
    excluded_camera_outliers: list[dict],
    camera_mask: np.ndarray,
    image_rows: list[dict],
    point_membership: np.ndarray | None,
    core_point_membership: np.ndarray | None,
    point_source: Path | None,
    original_point_count: int | None,
    filtered_point_count: int | None,
    point_filter_box: list[float] | None,
    bounds: np.ndarray,
    raw_core_bounds: np.ndarray | None,
    bounds_percentile: float,
    core_point_policy: str,
) -> dict:
    camera_memberships = camera_mask.sum(axis=1)
    source_memberships = np.asarray([len(row["source_unit_ids"]) for row in image_rows], dtype=np.int64)
    combined_basenames = {row["basename"] for row in image_rows}
    duplicate_basenames = len(combined_basenames) != len(image_rows)
    combined_sort_keys = [row["sort_key"] for row in image_rows]
    duplicate_sort_key_count = len(combined_sort_keys) - len(set(combined_sort_keys))
    overlap_histogram = {
        str(count): int(np.count_nonzero(camera_memberships == count))
        for count in range(int(camera_memberships.max(initial=0)) + 1)
    }
    source_overlap_histogram = {
        str(count): int(np.count_nonzero(source_memberships == count))
        for count in range(int(source_memberships.max(initial=0)) + 1)
    }
    summary = {
        "partition_type": "colmap_unit",
        "partition_name": partition_name,
        "source_path": str(source_path),
        "sparse_images_source": str(sparse_source),
        "sparse_points_source": str(point_source) if point_source else None,
        "assignment_source": assignment_source,
        "row_order": "COLMAP images sorted by basename stem, matching scene.dataset_readers.readColmapSceneInfo",
        "camera_count": int(camera_mask.shape[0]),
        "unit_count": int(camera_mask.shape[1]),
        "source_unit_count": int(sum(unit_type == "source_unit" for unit_type in unit_types)),
        "passage_unit_count": int(sum(is_passage_unit(unit_name) for unit_name in unit_names)),
        "shared_camera_policy": shared_camera_policy,
        "range_file": str(range_file) if range_file else None,
        "range_overlap_policy": range_overlap_policy,
        "range_stats": range_stats,
        "excluded_camera_outlier_count": int(len(excluded_camera_outliers)),
        "excluded_camera_outliers": excluded_camera_outliers,
        "source_multi_unit_camera_count": int(np.count_nonzero(source_memberships > 1)),
        "source_camera_overlap_histogram": source_overlap_histogram,
        "unassigned_camera_count": int(np.count_nonzero(camera_memberships == 0)),
        "multi_unit_camera_count": int(np.count_nonzero(camera_memberships > 1)),
        "camera_overlap_histogram": overlap_histogram,
        "duplicate_combined_basename": duplicate_basenames,
        "duplicate_combined_sort_key_count": int(duplicate_sort_key_count),
        "camera_pair_overlap": (camera_mask.astype(np.int64).T @ camera_mask.astype(np.int64)).tolist(),
        "bounds_source": "core_points_percentile",
        "bounds_percentile": float(bounds_percentile),
        "point_filter_box": point_filter_box,
        "core_point_policy": core_point_policy,
        "units": [],
        "image_rows_head": image_rows[:10],
        "image_rows_tail": image_rows[-10:],
        "bounds": bounds.tolist(),
    }
    if point_membership is not None:
        point_memberships = point_membership.sum(axis=1)
        summary.update({
            "point_count": int(point_membership.shape[0]),
            "original_point_count": int(original_point_count) if original_point_count is not None else None,
            "filtered_point_count": int(filtered_point_count) if filtered_point_count is not None else None,
            "unassigned_point_count": int(np.count_nonzero(point_memberships == 0)),
            "multi_unit_point_count": int(np.count_nonzero(point_memberships > 1)),
            "point_pair_overlap": (point_membership.astype(np.int64).T @ point_membership.astype(np.int64)).tolist(),
        })
    if core_point_membership is not None:
        core_memberships = core_point_membership.sum(axis=1)
        summary.update({
            "core_point_count": int(core_point_membership.shape[0]),
            "unassigned_core_point_count": int(np.count_nonzero(core_memberships == 0)),
            "multi_unit_core_point_count": int(np.count_nonzero(core_memberships > 1)),
            "raw_core_bounds": raw_core_bounds.tolist() if raw_core_bounds is not None else None,
        })

    range_specs = range_stats.get("range_specs", {}) if range_stats else {}
    for unit_id, unit_name in enumerate(unit_names):
        unit_path = unit_paths[unit_id] if unit_id < len(unit_paths) else None
        unit_images = unit_image_sets[unit_id] if unit_id < len(unit_image_sets) else None
        if unit_images is not None:
            missing_from_combined = sorted(unit_images["names"] - combined_basenames)
            unit_image_count = len(unit_images["names"])
        else:
            missing_from_combined = []
            unit_image_count = int(camera_mask[:, unit_id].sum())
        unit_summary = {
            "id": unit_id,
            "name": unit_name,
            "type": unit_types[unit_id],
            "path": str(unit_path) if unit_path else None,
            "camera_count": int(camera_mask[:, unit_id].sum()),
            "unit_image_count": int(unit_image_count),
            "combined_missing_image_count": int(len(missing_from_combined)),
            "combined_missing_image_samples": missing_from_combined[:10],
            "bounds": bounds[unit_id].tolist(),
        }
        if unit_name in range_specs:
            unit_summary["frame_ranges"] = range_specs[unit_name]
        if point_membership is not None:
            unit_summary["point_count"] = int(point_membership[:, unit_id].sum())
        if core_point_membership is not None:
            unit_summary["core_point_count"] = int(core_point_membership[:, unit_id].sum())
            unit_summary["raw_core_bounds"] = raw_core_bounds[unit_id].tolist()
        summary["units"].append(unit_summary)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a CityGaussian partition from original COLMAP unit image folders."
    )
    parser.add_argument("--source-path", required=True, type=Path, help="Combined COLMAP scene path.")
    parser.add_argument("--partition-name", required=True, help="Output partition artifact basename.")
    parser.add_argument("--unit-paths", nargs="*", type=Path, default=[], help="Original room/passage COLMAP unit paths.")
    parser.add_argument("--images-dir", default="images", help="Image directory name under source and unit paths.")
    parser.add_argument("--sparse-dir", default="sparse/0", help="COLMAP sparse model directory under source path.")
    parser.add_argument("--shared-camera-policy", choices=("keep", "drop", "split"), default="keep")
    parser.add_argument("--passage-splits", type=int, default=0)
    parser.add_argument("--passage-prefix", default="passage")
    parser.add_argument("--range-file", type=Path, default=None, help="Optional frame range file such as sub.txt.")
    parser.add_argument(
        "--range-unit-names",
        nargs="+",
        default=[],
        help="Unit names to materialize from --range-file, in block id order.",
    )
    parser.add_argument("--range-overlap-policy", choices=("single_owner",), default="single_owner")
    parser.add_argument("--camera-outlier-filter", choices=("none", "robust"), default="none")
    parser.add_argument("--camera-outlier-z-threshold", type=float, default=8.0)
    parser.add_argument("--camera-outlier-min-distance", type=float, default=5.0)
    parser.add_argument("--camera-outlier-distance-ratio", type=float, default=4.0)
    parser.add_argument(
        "--point-source-path",
        type=Path,
        default=None,
        help=(
            "Optional COLMAP scene path used only for points3D tracks. "
            "Use this when --source-path is a filtered scene with only points3D.ply."
        ),
    )
    parser.add_argument(
        "--point-filter-box",
        type=float,
        nargs=6,
        default=None,
        metavar=("MIN_X", "MIN_Y", "MIN_Z", "MAX_X", "MAX_Y", "MAX_Z"),
        help="Optional xyz box applied to the point-source tracks before writing point membership.",
    )
    parser.add_argument(
        "--validate-point-cloud-length",
        action="store_true",
        help="Validate that written point membership length matches source sparse/0/points3D.ply vertex count.",
    )
    parser.add_argument("--skip-points", action="store_true", help="Only write camera partition and camera-derived summary.")
    parser.add_argument("--bounds-percentile", type=float, default=0.5)
    parser.add_argument(
        "--core-point-policy",
        choices=("per_observation", "single_owner"),
        default="per_observation",
        help="How to choose core points for bounds and unit initialization.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing partition artifacts.")
    args = parser.parse_args()

    paths = output_paths(args.source_path, args.partition_name)
    assert_outputs_available(paths, write_points=not args.skip_points, overwrite=args.overwrite)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    images, sparse_source = read_combined_images(args.source_path, args.sparse_dir)
    range_stats = None
    if args.range_file is not None:
        if not args.range_unit_names:
            raise ValueError("--range-unit-names is required when --range-file is used.")
        range_specs = parse_range_file(args.range_file)
        camera_mask, image_rows, range_stats = build_range_camera_partition(
            images,
            range_specs,
            args.range_unit_names,
            args.range_overlap_policy,
        )
        assignment_source = "range_file"
        unit_names = list(args.range_unit_names)
        unit_types = ["range_passage" if is_passage_unit(unit_name) else "range_room" for unit_name in unit_names]
        unit_paths = []
        unit_image_sets = []
        shared_camera_policy = "range_single_owner"
    else:
        if not args.unit_paths:
            raise ValueError("--unit-paths is required unless --range-file is used.")
        unit_image_sets = [collect_unit_images(unit_path, args.images_dir) for unit_path in args.unit_paths]
        source_camera_mask, image_rows = build_camera_partition(images, unit_image_sets)
        camera_mask, passage_unit_names = apply_shared_camera_policy(
            source_camera_mask,
            image_rows,
            args.shared_camera_policy,
            args.passage_splits,
            args.passage_prefix,
        )
        assignment_source = "unit_paths"
        unit_names = [unit_path.name for unit_path in args.unit_paths] + passage_unit_names
        unit_types = ["source_unit" for _ in args.unit_paths] + [
            "shared_passage_split" for _ in passage_unit_names
        ]
        unit_paths = list(args.unit_paths)
        shared_camera_policy = args.shared_camera_policy

    excluded_camera_outliers = []
    if args.camera_outlier_filter == "robust":
        camera_mask, excluded_camera_outliers = filter_camera_outliers(
            images,
            camera_mask,
            image_rows,
            args.camera_outlier_z_threshold,
            args.camera_outlier_min_distance,
            args.camera_outlier_distance_ratio,
        )

    image_id_to_units = build_image_id_to_units(camera_mask, image_rows)

    if np.any(camera_mask.sum(axis=0) == 0):
        empty_units = np.where(camera_mask.sum(axis=0) == 0)[0]
        raise ValueError(f"No cameras matched units: {empty_units.tolist()}")
    if np.any(camera_mask.sum(axis=1) == 0):
        print(f"Warning: {np.count_nonzero(camera_mask.sum(axis=1) == 0)} cameras did not match any unit.")

    point_membership = None
    core_point_membership = None
    point_source = None
    original_point_count = None
    filtered_point_count = None
    raw_core_bounds = None
    if args.skip_points:
        bounds = np.zeros((camera_mask.shape[1], 6), dtype=np.float32)
    else:
        point_source_path = args.point_source_path or args.source_path
        (
            point_membership,
            core_point_membership,
            bounds,
            raw_core_bounds,
            point_source,
            original_point_count,
            filtered_point_count,
        ) = build_point_partition(
            point_source_path,
            args.sparse_dir,
            image_id_to_units,
            camera_mask.shape[1],
            args.bounds_percentile,
            args.point_filter_box,
            args.core_point_policy,
        )
        if args.validate_point_cloud_length:
            ply_path = args.source_path / args.sparse_dir / "points3D.ply"
            if not ply_path.exists():
                raise FileNotFoundError(f"Missing validation point cloud: {ply_path}")
            ply_point_count = count_ply_vertices(ply_path)
            if point_membership.shape[0] != ply_point_count:
                raise ValueError(
                    "Point membership length does not match source points3D.ply: "
                    f"{point_membership.shape[0]} vs {ply_point_count}"
                )
        np.save(paths["points"], point_membership)
        np.save(paths["core_points"], core_point_membership)

    np.save(paths["camera"], camera_mask)
    np.save(paths["bounds"], bounds)

    summary = summarize(
        args.source_path,
        sparse_source,
        args.partition_name,
        assignment_source,
        unit_names,
        unit_types,
        unit_paths,
        unit_image_sets,
        shared_camera_policy,
        args.range_file,
        args.range_overlap_policy,
        range_stats,
        excluded_camera_outliers,
        camera_mask,
        image_rows,
        point_membership,
        core_point_membership,
        point_source,
        original_point_count,
        filtered_point_count,
        args.point_filter_box,
        bounds,
        raw_core_bounds,
        args.bounds_percentile,
        args.core_point_policy,
    )
    with paths["rows"].open("w", encoding="utf-8") as handle:
        json.dump(image_rows, handle, indent=2)

    units_manifest = []
    range_specs = range_stats.get("range_specs", {}) if range_stats else {}
    for unit_id, unit_name in enumerate(unit_names):
        unit_path = unit_paths[unit_id] if unit_id < len(unit_paths) else None
        unit_entry = {
            "id": unit_id,
            "name": unit_name,
            "type": unit_types[unit_id],
            "path": str(unit_path) if unit_path else None,
            "camera_count": int(camera_mask[:, unit_id].sum()),
            "bounds": bounds[unit_id].tolist(),
        }
        if unit_name in range_specs:
            unit_entry["frame_ranges"] = range_specs[unit_name]
        units_manifest.append(unit_entry)

    with paths["units"].open("w", encoding="utf-8") as handle:
        json.dump(units_manifest, handle, indent=2)
    with paths["summary"].open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
