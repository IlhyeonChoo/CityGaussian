import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from utils.overlap_utils import compute_overlap_bounds


def parse_block_dim(raw_value):
    values = [int(value.strip()) for value in raw_value.split(",") if value.strip()]
    if len(values) == 2:
        values.append(1)
    if len(values) != 3:
        raise ValueError("block_dim must have 2 or 3 integers")
    return values


def main():
    parser = argparse.ArgumentParser(description="Visualize block partitions in normalized XY space")
    parser.add_argument("--block_dim", type=str, required=True)
    parser.add_argument("--overlap_ratio", type=float, default=0.0)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    block_dim = parse_block_dim(args.block_dim)
    num_blocks = block_dim[0] * block_dim[1] * block_dim[2]

    fig, ax = plt.subplots(figsize=(8, 8))
    for block_id in range(num_blocks):
        core_bounds, expanded_bounds = compute_overlap_bounds(block_id, block_dim, args.overlap_ratio)
        ax.add_patch(
            plt.Rectangle(
                (float(expanded_bounds[0]), float(expanded_bounds[2])),
                float(expanded_bounds[1] - expanded_bounds[0]),
                float(expanded_bounds[3] - expanded_bounds[2]),
                fill=False,
                edgecolor="#d95f02",
                linewidth=1,
                alpha=0.5,
            )
        )
        ax.add_patch(
            plt.Rectangle(
                (float(core_bounds[0]), float(core_bounds[2])),
                float(core_bounds[1] - core_bounds[0]),
                float(core_bounds[3] - core_bounds[2]),
                fill=False,
                edgecolor="#1b9e77",
                linewidth=1.5,
            )
        )
        center_x = float((core_bounds[0] + core_bounds[1]) / 2.0)
        center_y = float((core_bounds[2] + core_bounds[3]) / 2.0)
        ax.text(center_x, center_y, str(block_id), fontsize=8, ha="center", va="center")

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("equal")
    ax.set_title(f"block_dim={block_dim}, overlap_ratio={args.overlap_ratio}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
