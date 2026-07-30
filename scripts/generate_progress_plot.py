"""Render Reflector's canonical generation-progress chart.

The numerical series is parsed from REAL_GAMES_REPORT.md so the plot cannot
quietly diverge from the human-readable score table.  Experimental, control,
and rejected points remain visible but are not connected into the accepted
champion lineage.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "REAL_GAMES_REPORT.md"
PNG = ROOT / "reports" / "generation-progress.png"
SVG = ROOT / "reports" / "generation-progress.svg"

ACCEPTED_DECISIONS = frozenset(
    {
        "baseline",
        "promoted",
        "accepted parent",
        "historical accepted",
        "current accepted",
    }
)
KNOWN_DECISIONS = ACCEPTED_DECISIONS | {
    "historical threaded result",
    "process-isolated control",
    "experimental; complexity not earned",
    "rejected: one accepted level regressed",
}
MILESTONES = (
    (
        "v14",
        "Stateful intervention graph",
        "first non-zero progress",
    ),
    (
        "v25",
        "Overlapping relation constraints",
        "coordinate repairs become global",
    ),
    (
        "v30",
        "Marker-grounded goals",
        "cyclic transports become composable",
    ),
    (
        "v37",
        "Enclosure-grounded sibling composition",
        "nested container targets become executable",
    ),
    (
        "v42",
        "Topology + information actions",
        "uncertain gates become testable",
    ),
    (
        "v49b",
        "Coupled-object effects",
        "contact-aware planning",
    ),
    (
        "v64b",
        "Perception-compressing graph frontier",
        "speculative graph actions stay gated",
    ),
    (
        "v65b",
        "Unique exhaustive connector graph",
        "+5 levels · largest jump · first full game",
    ),
    (
        "v66",
        "Learned relative lattice effects",
        "exact CSP gives second complete game",
    ),
    (
        "v67",
        "Confirmed segmented permutations",
        "bounded exact transport adds lp85 level 4",
    ),
)


@dataclass(frozen=True, slots=True)
class Generation:
    version: str
    score: float
    levels: int
    games_with_progress: int
    games_beaten: int
    change: str
    decision: str

    @property
    def accepted(self) -> bool:
        return self.decision in ACCEPTED_DECISIONS


def _plain(value: str) -> str:
    return re.sub(r"[*_`]", "", value).strip()


def load_generations(report: Path = REPORT) -> tuple[Generation, ...]:
    text = report.read_text(encoding="utf-8")
    sections = text.split("## Score evolution", 1)
    if len(sections) != 2:
        raise RuntimeError("canonical report has no Score evolution section")
    section = sections[1]
    rows: list[Generation] = []
    table_started = False
    for line_number, line in enumerate(section.splitlines(), start=1):
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [_plain(cell) for cell in line.strip().strip("|").split("|")]
        if not table_started:
            if cells and cells[0] == "Version":
                if len(cells) != 7:
                    raise RuntimeError("Score evolution header must have 7 columns")
                table_started = True
            continue
        if cells and all(
            cell and set(cell).issubset({"-", ":", " "}) for cell in cells
        ):
            continue
        if len(cells) != 7:
            raise RuntimeError(
                f"malformed Score evolution row at section line {line_number}: "
                f"expected 7 columns, got {len(cells)}"
            )
        try:
            generation = Generation(
                version=cells[0],
                score=float(cells[1]),
                levels=int(cells[2]),
                games_with_progress=int(cells[3]),
                games_beaten=int(cells[4]),
                change=cells[5],
                decision=cells[6],
            )
        except ValueError as error:
            raise RuntimeError(
                f"invalid numeric value in Score evolution row "
                f"{cells[0]!r}"
            ) from error
        if generation.decision not in KNOWN_DECISIONS:
            raise RuntimeError(
                f"unknown Score evolution decision for {generation.version}: "
                f"{generation.decision!r}"
            )
        if not math.isfinite(generation.score) or not 0 <= generation.score <= 100:
            raise RuntimeError(
                f"Score evolution score is outside [0, 100] for "
                f"{generation.version}"
            )
        if not 0 <= generation.levels <= 183:
            raise RuntimeError(
                f"Score evolution level count is outside [0, 183] for "
                f"{generation.version}"
            )
        if not 0 <= generation.games_with_progress <= 25:
            raise RuntimeError(
                f"Score evolution progress-game count is outside [0, 25] "
                f"for {generation.version}"
            )
        if not 0 <= generation.games_beaten <= generation.games_with_progress:
            raise RuntimeError(
                f"Score evolution beaten-game count exceeds progress games "
                f"for {generation.version}"
            )
        if generation.games_with_progress > generation.levels:
            raise RuntimeError(
                f"Score evolution progress games exceed solved levels for "
                f"{generation.version}"
            )
        rows.append(generation)
    if not rows:
        raise RuntimeError("no generation rows found in canonical report")
    versions = tuple(item.version for item in rows)
    if len(set(versions)) != len(versions):
        raise RuntimeError("Score evolution versions must be unique")
    current = tuple(
        item for item in rows if item.decision == "current accepted"
    )
    if len(current) != 1:
        raise RuntimeError("Score evolution must have exactly one current accepted")
    return tuple(rows)


def render(generations: tuple[Generation, ...]) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.edgecolor": "#24324a",
            "axes.labelcolor": "#24324a",
            "xtick.color": "#34445e",
            "ytick.color": "#34445e",
            "svg.hashsalt": "reflector-generation-progress",
        }
    )
    figure = plt.figure(figsize=(16, 12.4), dpi=180)
    figure.patch.set_facecolor("#f7f3ea")
    grid = figure.add_gridspec(
        nrows=2,
        ncols=1,
        height_ratios=(3.5, 2.25),
        hspace=0.22,
    )
    score_axis = figure.add_subplot(grid[0])
    insight_axis = figure.add_subplot(grid[1])
    score_axis.set_facecolor("#fffdf8")
    level_axis = score_axis.twinx()

    x_values = list(range(len(generations)))
    accepted_indexes = [
        index for index, item in enumerate(generations) if item.accepted
    ]
    accepted_scores = [generations[index].score for index in accepted_indexes]
    accepted_levels = [generations[index].levels for index in accepted_indexes]

    score_color = "#176b87"
    level_color = "#d56b2d"
    experimental_color = "#8b91a1"
    score_axis.plot(
        accepted_indexes,
        accepted_scores,
        color=score_color,
        linewidth=3.2,
        marker="o",
        markersize=7,
        markeredgecolor="#fffdf8",
        markeredgewidth=1.4,
        zorder=4,
    )
    level_axis.plot(
        accepted_indexes,
        accepted_levels,
        color=level_color,
        linewidth=2.4,
        marker="s",
        markersize=5.5,
        markeredgecolor="#fffdf8",
        markeredgewidth=1.1,
        alpha=0.9,
        zorder=3,
    )

    experimental_indexes = [
        index for index, item in enumerate(generations) if not item.accepted
    ]
    score_axis.scatter(
        experimental_indexes,
        [generations[index].score for index in experimental_indexes],
        s=72,
        facecolors="#fffdf8",
        edgecolors=experimental_color,
        linewidths=1.8,
        marker="D",
        zorder=5,
    )

    current_index = next(
        index
        for index, item in reversed(tuple(enumerate(generations)))
        if item.decision == "current accepted"
    )
    score_axis.scatter(
        [current_index],
        [generations[current_index].score],
        s=290,
        marker="*",
        color="#f2b134",
        edgecolor="#6c4b00",
        linewidth=1.2,
        zorder=7,
    )

    score_axis.axhline(
        20,
        color="#9a3f45",
        linestyle=(0, (6, 5)),
        linewidth=1.8,
        alpha=0.9,
        zorder=1,
    )
    score_axis.text(
        len(generations) - 0.55,
        20.3,
        "active goal: 20 / 100",
        color="#8b3037",
        fontsize=10,
        ha="right",
        va="bottom",
        weight="bold",
    )

    versions = {item.version for item in generations}
    missing_milestones = tuple(
        version for version, _title, _detail in MILESTONES
        if version not in versions
    )
    if missing_milestones:
        raise RuntimeError(
            "canonical score table is missing plotted milestones: "
            + ", ".join(missing_milestones)
        )
    for milestone_number, (version, _title, _detail) in enumerate(
        MILESTONES,
        start=1,
    ):
        index = next(
            (i for i, item in enumerate(generations) if item.version == version),
            None,
        )
        if index is None:
            continue
        score_axis.annotate(
            f"M{milestone_number}",
            xy=(index, generations[index].score),
            xytext=(0, 13),
            textcoords="offset points",
            fontsize=7.8,
            color="#5c4100",
            weight="bold",
            ha="center",
            va="bottom",
            bbox={
                "boxstyle": "circle,pad=0.28",
                "facecolor": "#f5c451",
                "edgecolor": "#6c4b00",
                "alpha": 0.98,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": "#8c6d21",
                "linewidth": 0.9,
                "shrinkA": 1,
                "shrinkB": 5,
            },
            zorder=8,
        )

    score_axis.set_title(
        "Reflector progress across all canonical evaluated checkpoints",
        fontsize=20,
        color="#1d2b42",
        pad=28,
    )
    score_axis.text(
        0.5,
        1.015,
        "Local 25-game public-development evidence · 400 actions/game · "
        "not a Kaggle leaderboard series",
        transform=score_axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=11,
        color="#59677a",
    )
    score_axis.set_ylabel("local score / 100", fontsize=12, color=score_color)
    level_axis.set_ylabel(
        "levels solved / 183",
        fontsize=12,
        color=level_color,
    )
    score_upper = min(
        100.5,
        max(
            21.5,
            math.ceil(max(item.score for item in generations) * 1.08 + 0.5),
        ),
    )
    level_upper = min(
        183.5,
        max(
            32,
            math.ceil(max(item.levels for item in generations) * 1.15),
        ),
    )
    score_axis.set_ylim(-0.5, score_upper)
    level_axis.set_ylim(-1, level_upper)
    score_axis.set_xlim(-0.8, len(generations) - 0.2)
    score_axis.set_xticks(x_values)
    score_axis.set_xticklabels(
        [item.version for item in generations],
        rotation=48,
        ha="right",
        fontsize=9,
    )
    score_axis.grid(axis="y", color="#d9d4ca", linewidth=0.8, alpha=0.75)
    score_axis.grid(axis="x", visible=False)
    score_axis.spines["top"].set_visible(False)
    level_axis.spines["top"].set_visible(False)

    legend = (
        Line2D(
            [0],
            [0],
            color=score_color,
            marker="o",
            linewidth=3,
            label="accepted lineage score",
        ),
        Line2D(
            [0],
            [0],
            color=level_color,
            marker="s",
            linewidth=2,
            label="accepted lineage levels",
        ),
        Line2D(
            [0],
            [0],
            color=experimental_color,
            marker="D",
            markerfacecolor="#fffdf8",
            linewidth=0,
            label="non-promoted score",
        ),
        Line2D(
            [0],
            [0],
            color="#9a3f45",
            linestyle=(0, (6, 5)),
            linewidth=2,
            label="20 / 100 goal",
        ),
    )
    score_axis.legend(
        handles=legend,
        loc="upper left",
        ncol=2,
        frameon=True,
        facecolor="#fffdf8",
        edgecolor="#c9c2b5",
        fontsize=9.5,
    )

    insight_axis.set_facecolor("#f7f3ea")
    insight_axis.axis("off")
    insight_axis.text(
        0.0,
        1.02,
        "What unlocked the accepted gains",
        transform=insight_axis.transAxes,
        fontsize=12,
        color="#1d2b42",
        weight="bold",
        va="bottom",
    )
    insight_axis.text(
        0.995,
        1.02,
        "Milestones describe the general mechanism, not game-specific fixes.",
        transform=insight_axis.transAxes,
        fontsize=8.8,
        color="#657184",
        ha="right",
        va="bottom",
    )
    columns = (0.005, 0.505)
    rows = (0.84, 0.64, 0.44, 0.24, 0.04)
    for milestone_number, (version, title, detail) in enumerate(
        MILESTONES,
        start=1,
    ):
        column = (milestone_number - 1) // 5
        row = (milestone_number - 1) % 5
        insight_axis.text(
            columns[column],
            rows[row],
            f"M{milestone_number} · {version}  {title}\n"
            f"               {detail}",
            transform=insight_axis.transAxes,
            fontsize=8.4,
            color="#26364e",
            ha="left",
            va="top",
            linespacing=1.2,
            bbox={
                "boxstyle": "round,pad=0.38",
                "facecolor": "#fffdf8",
                "edgecolor": "#d2cabc",
                "alpha": 0.98,
            },
        )

    figure.text(
        0.012,
        0.018,
        f"All {len(generations)} rows in the canonical Score evolution table "
        "are shown. "
        "Connected lines include only promoted/accepted checkpoints; hollow "
        "diamonds preserve non-promoted scores without implying lineage.",
        fontsize=9,
        color="#5a6575",
    )
    figure.subplots_adjust(
        left=0.075,
        right=0.925,
        top=0.91,
        bottom=0.065,
        hspace=0.24,
    )
    PNG.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(PNG, bbox_inches="tight", facecolor=figure.get_facecolor())
    figure.savefig(
        SVG,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
        metadata={"Date": None},
    )
    plt.close(figure)
    svg_text = SVG.read_text(encoding="utf-8")
    SVG.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    generations = load_generations()
    render(generations)
    print(PNG.relative_to(ROOT))
    print(SVG.relative_to(ROOT))


if __name__ == "__main__":
    main()
