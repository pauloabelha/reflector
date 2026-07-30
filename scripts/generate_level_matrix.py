"""Render the accepted public-game completion matrix from its scorecard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
SCORECARD = ROOT / "reports" / "official-isolated-v69-public-400.json"
PNG = ROOT / "reports" / "v69-game-level-matrix.png"
SVG = ROOT / "reports" / "v69-game-level-matrix.svg"


@dataclass(frozen=True, slots=True)
class GameLevels:
    game: str
    completed: int
    total: int


def load_game_levels(scorecard: Path = SCORECARD) -> tuple[GameLevels, ...]:
    payload = json.loads(scorecard.read_text(encoding="utf-8"))
    environments = payload["scorecard"]["environments"]
    rows = tuple(
        GameLevels(
            game=str(item["id"]).split("-", 1)[0],
            completed=int(item["levels_completed"]),
            total=int(item["level_count"]),
        )
        for item in environments
    )
    if not rows:
        raise RuntimeError("scorecard has no environments")
    if len({row.game for row in rows}) != len(rows):
        raise RuntimeError("scorecard game names must be unique")
    if any(row.total <= 0 or not 0 <= row.completed <= row.total for row in rows):
        raise RuntimeError("scorecard has an impossible level count")
    return tuple(sorted(rows, key=lambda row: row.game))


def render(rows: tuple[GameLevels, ...]) -> None:
    max_levels = max(row.total for row in rows)
    matrix = [
        [
            1 if level < row.completed else 0 if level < row.total else -1
            for level in range(max_levels)
        ]
        for row in rows
    ]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "svg.hashsalt": "reflector-v69-game-level-matrix",
        }
    )
    figure, axis = plt.subplots(figsize=(12.4, 13.2), dpi=180)
    figure.patch.set_facecolor("#f7f3ea")
    axis.set_facecolor("#f7f3ea")
    colors = ListedColormap(("#d8d5ce", "#111111", "#1f9d55"))
    norm = BoundaryNorm((-1.5, -0.5, 0.5, 1.5), colors.N)
    axis.imshow(matrix, cmap=colors, norm=norm, aspect="auto")

    axis.set_title(
        "Reflector v69 · Public game × level completion",
        fontsize=18,
        color="#24324a",
        pad=22,
    )
    axis.text(
        0.5,
        1.012,
        "30 of 183 levels completed · official local score 10.2554480981 / 100",
        transform=axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=10.5,
        color="#526078",
    )
    axis.set_xlabel("Level", fontsize=12, color="#24324a", labelpad=10)
    axis.set_ylabel("Public-development game", fontsize=12, color="#24324a")
    axis.set_xticks(
        range(max_levels),
        labels=tuple(str(level) for level in range(1, max_levels + 1)),
    )
    axis.set_yticks(
        range(len(rows)),
        labels=(f"{row.game}  ({row.completed}/{row.total})" for row in rows),
    )
    axis.tick_params(axis="both", colors="#34445e", length=0, pad=7)
    axis.set_xticks(
        [index - 0.5 for index in range(1, max_levels)],
        minor=True,
    )
    axis.set_yticks(
        [index - 0.5 for index in range(1, len(rows))],
        minor=True,
    )
    axis.grid(which="minor", color="#f7f3ea", linewidth=2.2)
    axis.tick_params(which="minor", bottom=False, left=False)
    for spine in axis.spines.values():
        spine.set_visible(False)

    legend = axis.legend(
        handles=(
            Patch(facecolor="#1f9d55", label="Completed"),
            Patch(facecolor="#111111", label="Not completed"),
            Patch(facecolor="#d8d5ce", label="No such level"),
        ),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.07),
        ncol=3,
        frameon=False,
        fontsize=10,
    )
    for text in legend.get_texts():
        text.set_color("#34445e")

    figure.tight_layout(rect=(0.02, 0.04, 0.98, 0.97))
    figure.savefig(PNG, dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    figure.savefig(
        SVG,
        format="svg",
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
        metadata={"Date": None},
    )
    plt.close(figure)
    normalized_svg = "\n".join(
        line.rstrip() for line in SVG.read_text(encoding="utf-8").splitlines()
    )
    SVG.write_text(normalized_svg + "\n", encoding="utf-8")


def main() -> None:
    render(load_game_levels())
    print(PNG.relative_to(ROOT))
    print(SVG.relative_to(ROOT))


if __name__ == "__main__":
    main()
