import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_metrics(results_dir, group_name):
    group_dir = Path(results_dir) / group_name
    results_path = group_dir / "results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"Missing results.json for {group_name}")

    with open(results_path) as fp:
        results = json.load(fp)
    method_name = next(iter(results.keys()))
    metrics = dict(results[method_name])

    boundary_path = None
    for candidate in [
        group_dir / "test" / method_name / "boundary_lpips.json",
        group_dir / "val" / method_name / "boundary_lpips.json",
    ]:
        if candidate.exists():
            boundary_path = candidate
            break
    if boundary_path is not None:
        with open(boundary_path) as fp:
            boundary_metrics = json.load(fp)
        metrics["Boundary LPIPS"] = boundary_metrics["mean_boundary_lpips"]

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Plot metrics across experiment groups")
    parser.add_argument("--results_dir", type=str, required=True)
    parser.add_argument("--groups", nargs="+", required=True)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    all_metrics = {group: load_metrics(args.results_dir, group) for group in args.groups}
    metric_names = sorted({metric for metrics in all_metrics.values() for metric in metrics.keys()})

    fig, axes = plt.subplots(len(metric_names), 1, figsize=(10, 3 * len(metric_names)))
    if len(metric_names) == 1:
        axes = [axes]

    for ax, metric_name in zip(axes, metric_names):
        values = [all_metrics[group].get(metric_name, float("nan")) for group in args.groups]
        ax.bar(args.groups, values, color="#4c72b0")
        ax.set_title(metric_name)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(args.results_dir) / "comparison_metrics.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
