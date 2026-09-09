# Copyright 2026 UBC Quantum Software and Algorithms Research Lab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Shared plotting utility for performance_tests CSVs.

Usage:
    python3 plot_results.py <results.csv> [<results2.csv> ...] [--outdir DIR]
"""
import argparse
import csv
import os
import re
import statistics
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_EXECUTION = "#6d5fc8"
COLOR_PROCESSING = "#eb6834"
COLOR_OVERHEAD = "#898781"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_TEXT = "#0b0b0b"
COLOR_MUTED = "#52514e"
SURFACE = "#fcfcfb"

FONT_TITLE = 16
FONT_LABEL = 13
FONT_TICK = 11
FONT_LEGEND = 11

TITLES = {
    "breakpoint_distance": (
        "Scaling of Response Time with Breakpoint Distance",
        "Response Time Composition Across Breakpoint Distances",
    ),
    "depth": (
        "Scaling of Response Time with Circuit Depth",
        "Response Time Composition Across Circuit Depths",
    ),
    "gate_migration": (
        "Scaling of Response Time with Gate Placement",
        "Response Time Composition by Gate Placement",
    ),
    "gate_migration_single_helper": (
        "Scaling of Response Time with Gate Placement (Single Subroutine)",
        "Response Time Composition by Gate Placement (Single Subroutine)",
    ),
    "gate_migration_midcircuit": (
        "Scaling of Response Time with Mid-Circuit Measurement Placement",
        "Response Time Composition by Mid-Circuit Measurement Placement",
    ),
    "midcircuit_measurements": (
        "Scaling of Response Time with Mid-Circuit Measurement Count",
        "Response Time Composition Across Mid-Circuit Measurement Counts",
    ),
    "nestedness": (
        "Scaling of Response Time with Subroutine Nesting Depth",
        "Response Time Composition Across Subroutine Nesting Depths",
    ),
    "num_lines_of_code": (
        "Scaling of Response Time with Code Length",
        "Response Time Composition Across Code Lengths",
    ),
    "num_qubits": (
        "Scaling of Response Time with Qubit Count",
        "Response Time Composition Across Qubit Counts",
    ),
    "num_subroutine_calls": (
        "Scaling of Response Time with Subroutine Call Count",
        "Response Time Composition Across Subroutine Call Counts",
    ),
}

AXIS_LABELS = {
    "depth": "Circuit Depth",
    "num_qubits": "Number of Qubits",
    "num_lines_of_code": "Number of Code Lines",
    "gates_outside": "Gates Outside of QNode",
    "units_outside": "Mid-Circuit Measurements Outside QNode",
    "num_mid_measurements": "Number of Mid-Circuit Measurement Gates",
    "nestedness": "Nesting Depth",
    "num_subroutine_calls": "Number of Subroutine Calls",
    "breakpoint_distance": "Breakpoint Distance",
}


def titles_for(base):
    """Look up the (scaling_title, breakdown_title) pair for a benchmark,
    falling back to a title-cased version of the base name for any script
    added later without an entry above."""
    fallback = base.replace("_", " ").title()
    return TITLES.get(base, (fallback, fallback))


def _axis_label(resource_name):
    return AXIS_LABELS.get(resource_name, resource_name)


def _style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_AXIS)
    ax.spines["bottom"].set_color(COLOR_AXIS)
    ax.tick_params(colors=COLOR_MUTED, labelsize=FONT_TICK)
    ax.yaxis.grid(True, color=COLOR_GRID, linewidth=1)
    ax.set_axisbelow(True)


def _thin_levels(levels, max_ticks=15):
    """Return a subsequence of `levels` to use as x-tick positions,
    thinned to at most `max_ticks` entries (always keeping the final
    level) so labels stay readable when there are many sampled levels."""
    n = len(levels)
    if n <= max_ticks:
        return list(levels)
    step = (n + max_ticks - 1) // max_ticks
    thinned = list(levels[::step])
    if thinned[-1] != levels[-1]:
        thinned.append(levels[-1])
    return thinned


def _set_level_xticks(ax, levels, max_ticks=15):
    """Pin x-axis ticks to the actual sampled resource levels instead of
    matplotlib's automatic locator, which can place ticks at positions
    with no corresponding data point."""
    ticks = _thin_levels(levels, max_ticks=max_ticks)
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [str(int(t)) if float(t).is_integer() else str(t) for t in ticks],
        fontsize=FONT_TICK, color=COLOR_MUTED,
    )


def _legend_loc(series_start, series_end):
    """Pick an upper corner for the legend based on whether the series
    starts higher than it ends, so the legend avoids the data."""
    return "upper right" if series_start > series_end else "upper left"


def load_grouped(csv_path):
    """Group a benchmark CSV's rows by resource level.

    Args:
        csv_path (str): path to a `<resource>,total_time,processing_time,
            execution_time` CSV produced by one of the performance_tests
            scripts.

    Returns:
        tuple(str, dict[float, dict[str, list[float]]]): the resource
        column's header name, and a mapping of resource value -> lists of
        total/processing/execution samples across reruns.
    """
    grouped = defaultdict(lambda: {"total": [], "processing": [], "execution": []})
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        resource_name = header[0]
        for row in reader:
            if not row:
                continue
            resource_value = float(row[0])
            grouped[resource_value]["total"].append(float(row[1]))
            grouped[resource_value]["processing"].append(float(row[2]))
            grouped[resource_value]["execution"].append(float(row[3]))
    return resource_name, dict(sorted(grouped.items()))


def _mean_std(values):
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def plot_scaling(resource_name, grouped, out_path, title):
    """Line chart: resource level vs. mean total/processing/execution time."""
    levels = list(grouped.keys())
    total_mean, total_std = zip(*(_mean_std(grouped[lv]["total"]) for lv in levels))
    proc_mean, proc_std = zip(*(_mean_std(grouped[lv]["processing"]) for lv in levels))
    exec_mean, exec_std = zip(*(_mean_std(grouped[lv]["execution"]) for lv in levels))

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style_axes(ax)

    total_handle = ax.errorbar(
        levels, total_mean, yerr=total_std, label="Total time", color=COLOR_OVERHEAD,
        linestyle="--", linewidth=2, marker="o", markersize=5, capsize=3,
    )
    proc_handle = ax.errorbar(
        levels, proc_mean, yerr=proc_std, label="Processing time (CircInspect)",
        color=COLOR_PROCESSING, linewidth=2, marker="o", markersize=5, capsize=3,
    )
    exec_handle = ax.errorbar(
        levels, exec_mean, yerr=exec_std, label="Execution time (PennyLane)",
        color=COLOR_EXECUTION, linewidth=2, marker="o", markersize=5, capsize=3,
    )

    ax.set_xlabel(_axis_label(resource_name), color=COLOR_TEXT, fontsize=FONT_LABEL)
    ax.set_ylabel("Time (s)", color=COLOR_TEXT, fontsize=FONT_LABEL)
    ax.set_title(title, color=COLOR_TEXT, fontsize=FONT_TITLE)

    # Overall std dev (across all levels) per series, shown as extra
    # legend rows via invisible handles rather than in the axis labels,
    # since per-level std is already drawn as error bars.
    all_total = [v for lv in levels for v in grouped[lv]["total"]]
    all_proc = [v for lv in levels for v in grouped[lv]["processing"]]
    all_exec = [v for lv in levels for v in grouped[lv]["execution"]]
    (sigma_total_handle,) = ax.plot([], [], alpha=0)
    (sigma_proc_handle,) = ax.plot([], [], alpha=0)
    (sigma_exec_handle,) = ax.plot([], [], alpha=0)

    edge = max(1, len(total_mean) // 5)
    loc = _legend_loc(statistics.mean(total_mean[:edge]), statistics.mean(total_mean[-edge:]))
    legend = ax.legend(
        [total_handle, proc_handle, exec_handle, sigma_total_handle, sigma_proc_handle, sigma_exec_handle],
        [
            "Total time", "Processing time (CircInspect)", "Execution time (PennyLane)",
            f"Overall σ (total) = ±{statistics.stdev(all_total):.3f}",
            f"Overall σ (processing) = ±{statistics.stdev(all_proc):.3f}",
            f"Overall σ (execution) = ±{statistics.stdev(all_exec):.3f}",
        ],
        frameon=False, labelcolor=COLOR_TEXT, loc=loc, fontsize=FONT_LEGEND,
    )
    for text, color in zip(legend.get_texts()[3:], [COLOR_OVERHEAD, COLOR_PROCESSING, COLOR_EXECUTION]):
        text.set_color(color)
    # Headroom above the tallest error bar for the now-taller legend to sit in.
    ymax = max(m + s for m, s in zip(total_mean, total_std))
    ymin = min(0, min(exec_mean) - max(exec_std))
    ax.set_ylim(ymin, ymax * 1.55)
    _set_level_xticks(ax, levels)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)


def plot_breakdown(resource_name, grouped, out_path, title):
    """Stacked bar chart: one bar per resource level, split into mean
    execution / processing time. The bar height (and the "total" used for
    legend placement / y-axis headroom) is exactly processing + execution,
    not the separately measured wall-clock total."""
    levels = list(grouped.keys())
    proc_mean = [_mean_std(grouped[lv]["processing"])[0] for lv in levels]
    exec_mean = [_mean_std(grouped[lv]["execution"])[0] for lv in levels]
    total_mean = [p + e for p, e in zip(proc_mean, exec_mean)]

    fig, ax = plt.subplots(figsize=(max(10, len(levels) * 0.4), 5.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style_axes(ax)

    x = range(len(levels))
    ax.bar(x, exec_mean, color=COLOR_EXECUTION, edgecolor=SURFACE, linewidth=1, label="Execution time (PennyLane)")
    ax.bar(x, proc_mean, bottom=exec_mean, color=COLOR_PROCESSING, edgecolor=SURFACE, linewidth=1, label="Processing time (CircInspect)")

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [str(int(lv)) if float(lv).is_integer() else str(lv) for lv in levels],
        rotation=45, ha="right", color=COLOR_MUTED, fontsize=FONT_TICK,
    )
    ax.set_xlabel(_axis_label(resource_name), color=COLOR_TEXT, fontsize=FONT_LABEL)
    ax.set_ylabel("Time (s)", color=COLOR_TEXT, fontsize=FONT_LABEL)
    ax.set_title(title, color=COLOR_TEXT, fontsize=FONT_TITLE)

    edge = max(1, len(total_mean) // 5)
    loc = _legend_loc(statistics.mean(total_mean[:edge]), statistics.mean(total_mean[-edge:]))
    ax.legend(frameon=False, labelcolor=COLOR_TEXT, loc=loc, fontsize=FONT_LEGEND)
    ax.set_ylim(0, max(total_mean) * 1.3)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)


def clean_base_name(csv_path):
    """Derive a human-readable base name from a benchmark CSV path by
    stripping the trailing `_results_<timestamp>` suffix the test scripts
    append (e.g. `depth_results_1786054401.2994149.csv` -> `depth`)."""
    stem = os.path.splitext(os.path.basename(csv_path))[0]
    return re.sub(r"_results_\d+(?:\.\d+)?$", "", stem)


def plot_csv(csv_path, out_dir=None):
    base = clean_base_name(csv_path)
    target_dir = out_dir or os.path.dirname(csv_path) or "."
    os.makedirs(target_dir, exist_ok=True)

    resource_name, grouped = load_grouped(csv_path)
    if not grouped:
        print(f"No data rows found in {csv_path}, skipping.")
        return
    scaling_title, breakdown_title = titles_for(base)
    scaling_path = os.path.join(target_dir, f"{base}_scaling.png")
    breakdown_path = os.path.join(target_dir, f"{base}_breakdown.png")
    plot_scaling(resource_name, grouped, scaling_path, scaling_title)
    plot_breakdown(resource_name, grouped, breakdown_path, breakdown_title)
    print(f"Wrote {scaling_path} and {breakdown_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot performance_tests benchmark CSVs.")
    parser.add_argument("csvs", nargs="+", help="Benchmark CSV file(s) to plot.")
    parser.add_argument(
        "--outdir", default=None,
        help="Directory to write PNGs into (default: next to each input CSV).",
    )
    args = parser.parse_args()
    for path in args.csvs:
        plot_csv(path, out_dir=args.outdir)
