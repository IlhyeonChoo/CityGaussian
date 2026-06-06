#!/usr/bin/env python3
"""Create a balanced COLMAP custom render subset from frame ranges."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


FRAME_RE = re.compile(r"(\d+)")
RANGE_RE = re.compile(r"(\d+)\s*~\s*(\d+)")


@dataclass(frozen=True)
class ImageEntry:
    image_id: int
    pose_line: str
    points_line: str
    name: str
    frame: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a deterministic balanced COLMAP render subset."
    )
    parser.add_argument("--source-path", required=True, type=Path)
    parser.add_argument("--range-file", required=True, type=Path)
    parser.add_argument("--output-path", required=True, type=Path)
    parser.add_argument("--units", required=True, nargs="+")
    parser.add_argument(
        "--priority-units",
        nargs="+",
        default=None,
        help="Assignment priority for overlapping ranges. Defaults to --units order.",
    )
    parser.add_argument("--per-unit", type=int, default=50)
    parser.add_argument("--sparse-dir", default="sparse/0")
    parser.add_argument("--image-dir-name", default="images")
    return parser.parse_args()


def frame_number_from_name(image_name: str) -> int:
    stem = Path(image_name).stem
    match = FRAME_RE.search(stem)
    if match is None:
        raise ValueError(f"Unable to parse frame number from image name: {image_name}")
    return int(match.group(1))


def parse_images_txt(path: Path) -> tuple[list[str], list[ImageEntry]]:
    header: list[str] = []
    entries: list[ImageEntry] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue
        if line.startswith("#"):
            header.append(line)
            idx += 1
            continue

        pose_line = line
        points_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        parts = pose_line.split()
        if len(parts) < 10:
            raise ValueError(f"Malformed COLMAP image pose line: {pose_line}")
        image_id = int(parts[0])
        name = parts[-1]
        entries.append(
            ImageEntry(
                image_id=image_id,
                pose_line=pose_line,
                points_line=points_line,
                name=name,
                frame=frame_number_from_name(name),
            )
        )
        idx += 2

    return header, entries


def parse_range_file(path: Path) -> dict[str, list[tuple[int, int]]]:
    ranges_by_unit: dict[str, list[tuple[int, int]]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        unit_name, spec = line.split(":", 1)
        ranges = [
            (int(match.group(1)), int(match.group(2)))
            for match in RANGE_RE.finditer(spec)
        ]
        if ranges:
            ranges_by_unit[unit_name.strip()] = ranges
    return ranges_by_unit


def frame_in_ranges(frame: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= frame <= end for start, end in ranges)


def sample_uniform(entries: list[ImageEntry], count: int) -> list[ImageEntry]:
    if len(entries) <= count:
        return entries
    if count <= 0:
        return []
    if count == 1:
        return [entries[len(entries) // 2]]

    last = len(entries) - 1
    selected_indices: list[int] = []
    seen: set[int] = set()
    for sample_idx in range(count):
        raw_idx = round(sample_idx * last / (count - 1))
        idx = min(max(raw_idx, 0), last)
        while idx in seen and idx < last:
            idx += 1
        while idx in seen and idx > 0:
            idx -= 1
        seen.add(idx)
        selected_indices.append(idx)
    return [entries[idx] for idx in sorted(selected_indices)]


def create_relative_symlink(target: Path, link_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    relative_target = Path(
        *Path(shutil.os.path.relpath(target.resolve(), link_path.parent.resolve())).parts
    )
    link_path.symlink_to(relative_target)


def main() -> None:
    args = parse_args()
    source_path = args.source_path
    output_path = args.output_path
    sparse_source = source_path / args.sparse_dir
    sparse_output = output_path / args.sparse_dir
    priority_units = args.priority_units or args.units

    ranges_by_unit = parse_range_file(args.range_file)
    missing_units = [unit for unit in args.units if unit not in ranges_by_unit]
    if missing_units:
        raise ValueError(f"Missing unit ranges: {', '.join(missing_units)}")

    _, entries = parse_images_txt(sparse_source / "images.txt")
    entries_by_name = {entry.name: entry for entry in entries}
    candidates_by_unit: dict[str, list[ImageEntry]] = {unit: [] for unit in args.units}

    for entry in entries:
        assigned_unit = None
        for unit in priority_units:
            if unit in candidates_by_unit and frame_in_ranges(entry.frame, ranges_by_unit[unit]):
                assigned_unit = unit
                break
        if assigned_unit is not None:
            candidates_by_unit[assigned_unit].append(entry)

    selected_by_unit: dict[str, list[ImageEntry]] = {}
    for unit in args.units:
        candidates = sorted(candidates_by_unit[unit], key=lambda item: (item.frame, item.name))
        if len(candidates) < args.per_unit:
            raise ValueError(
                f"Unit {unit} has only {len(candidates)} candidates, "
                f"less than requested {args.per_unit}."
            )
        selected_by_unit[unit] = sample_uniform(candidates, args.per_unit)

    selected_entries: list[ImageEntry] = []
    seen_names: set[str] = set()
    for unit in args.units:
        for entry in selected_by_unit[unit]:
            if entry.name in seen_names:
                raise ValueError(f"Duplicate selected image: {entry.name}")
            seen_names.add(entry.name)
            selected_entries.append(entries_by_name[entry.name])

    selected_entries = sorted(selected_entries, key=lambda item: (item.frame, item.name))

    sparse_output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sparse_source / "cameras.txt", sparse_output / "cameras.txt")
    create_relative_symlink(sparse_source / "points3D.ply", sparse_output / "points3D.ply")
    create_relative_symlink(source_path / args.image_dir_name, output_path / args.image_dir_name)

    image_lines = [
        "# Balanced manual-unit render subset.",
        f"# Source path: {source_path}",
        f"# Range file: {args.range_file}",
        f"# Units: {', '.join(args.units)}",
        f"# Priority units: {', '.join(priority_units)}",
        f"# Per-unit selected images: {args.per_unit}",
        f"# Number of selected images: {len(selected_entries)}",
    ]
    for entry in selected_entries:
        image_lines.append(entry.pose_line)
        image_lines.append(entry.points_line)
    (sparse_output / "images.txt").write_text("\n".join(image_lines) + "\n", encoding="utf-8")

    selected_frames = []
    unit_lookup = {
        entry.name: unit
        for unit, unit_entries in selected_by_unit.items()
        for entry in unit_entries
    }
    for render_index, entry in enumerate(selected_entries):
        selected_frames.append(
            {
                "render_index": render_index,
                "render_file": f"{render_index:05d}.png",
                "unit": unit_lookup[entry.name],
                "frame": entry.frame,
                "image_id": entry.image_id,
                "image_name": entry.name,
            }
        )

    summary = {
        "source_path": str(source_path),
        "range_file": str(args.range_file),
        "output_path": str(output_path),
        "units": args.units,
        "priority_units": priority_units,
        "per_unit": args.per_unit,
        "selected_count": len(selected_frames),
        "candidate_counts": {
            unit: len(candidates_by_unit[unit])
            for unit in args.units
        },
        "selected_counts": {
            unit: len(selected_by_unit[unit])
            for unit in args.units
        },
        "frame_ranges": {
            unit: {
                "min": min(entry.frame for entry in selected_by_unit[unit]),
                "max": max(entry.frame for entry in selected_by_unit[unit]),
            }
            for unit in args.units
        },
    }
    (output_path / "selected_frames.json").write_text(
        json.dumps(selected_frames, indent=2), encoding="utf-8"
    )
    (output_path / "selection_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
