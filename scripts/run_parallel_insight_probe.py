"""Run and summarize a trace-rich parallel cross-game insight probe."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class GameInsight:
    game: str
    score: float
    levels_completed: int
    total_levels: int
    actions: int
    level_actions: tuple[int, ...]
    longest_level_plateau: int
    actions_after_last_progress: int
    mechanism_advisor_actions: int
    top_decision_reasons: tuple[tuple[str, int], ...]
    causal_predictions: int
    causal_confirmations: int
    causal_conflicts: int
    active_diagnostics: tuple[tuple[str, int], ...]
    triage_signal: str


def _environment_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["id"]).split("-", 1)[0]: item
        for item in report["scorecard"]["environments"]
    }


def _plateaus(levels: list[int]) -> tuple[int, int]:
    if not levels:
        return (0, 0)
    longest = 1
    current = 1
    for previous, value in zip(levels, levels[1:], strict=False):
        if value == previous:
            current += 1
        else:
            longest = max(longest, current)
            current = 1
    longest = max(longest, current)
    final_level = levels[-1]
    last_progress = max(
        (
            index
            for index, value in enumerate(levels)
            if value < final_level
        ),
        default=-1,
    )
    return (longest, len(levels) - last_progress - 1)


def _metric_maxima(
    events: list[dict[str, Any]],
    suffix: str,
) -> int:
    maxima: dict[str, int] = {}
    for event in events:
        exploration = event.get("operative_state", {}).get("exploration", {})
        for key, value in exploration.items():
            if (
                key.endswith(suffix)
                and isinstance(value, int | float)
                and not isinstance(value, bool)
            ):
                maxima[key] = max(maxima.get(key, 0), int(value))
    return sum(maxima.values())


def _diagnostics(
    events: list[dict[str, Any]],
) -> tuple[tuple[str, int], ...]:
    counts: Counter[str] = Counter()
    inactive = {"exact-off", "not-attempted", "stage-complete"}
    for event in events:
        exploration = event.get("operative_state", {}).get("exploration", {})
        for key, value in exploration.items():
            if (
                key.endswith("_diagnostic")
                and isinstance(value, str)
                and value not in inactive
            ):
                counts[f"{key.removesuffix('_diagnostic')}={value}"] += 1
    return tuple(counts.most_common(5))


def _triage_signal(
    *,
    levels_completed: int,
    actions: int,
    actions_after_last_progress: int,
    mechanism_advisor_actions: int,
    predictions: int,
    conflicts: int,
    diagnostics: tuple[tuple[str, int], ...],
) -> str:
    diagnostic_text = " ".join(name for name, _count in diagnostics)
    if conflicts:
        return "falsified causal model; revise transition prior"
    if any(
        marker in diagnostic_text
        for marker in ("quarantined", "ambiguous", "mismatch")
    ):
        return "grounding ambiguity or model mismatch"
    if levels_completed and actions_after_last_progress >= max(2, actions // 2):
        return "post-progress operator or composition gap"
    if not levels_completed and mechanism_advisor_actions == 0:
        return "no grounded advisor; missing representation or affordance prior"
    if not levels_completed and predictions == 0:
        return "mechanism actions lacked prospective transition or goal evidence"
    if not levels_completed:
        return "grounded actions without goal progress; missing goal/operator model"
    return "productive mechanism; inspect next unsolved level"


def analyze_probe(
    report_path: Path,
    cognitive_dir: Path,
) -> tuple[GameInsight, ...]:
    """Summarize cross-game evidence without inspecting environment source."""

    report = json.loads(report_path.read_text(encoding="utf-8"))
    environments = _environment_rows(report)
    output: list[GameInsight] = []
    for game, environment in sorted(environments.items()):
        stream = cognitive_dir / f"{game}.cognitive.jsonl"
        events = (
            [
                json.loads(line)
                for line in stream.read_text(encoding="utf-8").splitlines()
                if line
            ]
            if stream.is_file()
            else []
        )
        run = environment["runs"][0]
        levels = [
            int(event.get("observation", {}).get("levels_completed", 0))
            for event in events
        ]
        plateau, after_progress = _plateaus(levels)
        reasons = Counter(
            str(event.get("decision", {}).get("reason", "unknown"))
            for event in events
        )
        mechanism_actions = sum(
            reason.startswith("epistemic-frontier:")
            and reason
            not in {
                "epistemic-frontier:untried-current-state",
                "epistemic-frontier:navigate-known-state",
                "epistemic-frontier:hierarchical-action-family",
            }
            for reason in reasons.elements()
        )
        diagnostics = _diagnostics(events)
        predictions = _metric_maxima(events, "_predictions")
        confirmations = _metric_maxima(events, "_confirmations")
        conflicts = _metric_maxima(events, "_conflicts")
        levels_completed = int(run["levels_completed"])
        actions = int(run["actions"])
        output.append(
            GameInsight(
                game=game,
                score=float(run["score"]),
                levels_completed=levels_completed,
                total_levels=int(environment["level_count"]),
                actions=actions,
                level_actions=tuple(int(value) for value in run["level_actions"]),
                longest_level_plateau=plateau,
                actions_after_last_progress=after_progress,
                mechanism_advisor_actions=mechanism_actions,
                top_decision_reasons=tuple(reasons.most_common(4)),
                causal_predictions=predictions,
                causal_confirmations=confirmations,
                causal_conflicts=conflicts,
                active_diagnostics=diagnostics,
                triage_signal=_triage_signal(
                    levels_completed=levels_completed,
                    actions=actions,
                    actions_after_last_progress=after_progress,
                    mechanism_advisor_actions=mechanism_actions,
                    predictions=predictions,
                    conflicts=conflicts,
                    diagnostics=diagnostics,
                ),
            )
        )
    return tuple(output)


def render_markdown(insights: tuple[GameInsight, ...]) -> str:
    lines = [
        "# Parallel cross-game insight probe",
        "",
        "| Game | Levels | Actions | Plateau | Mechanism advisor | Causal P/C/X | Triage signal |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in insights:
        lines.append(
            f"| `{item.game}` | {item.levels_completed}/{item.total_levels} "
            f"| {item.actions} | {item.longest_level_plateau} "
            f"| {item.mechanism_advisor_actions} "
            f"| {item.causal_predictions}/{item.causal_confirmations}/"
            f"{item.causal_conflicts} | {item.triage_signal} |"
        )
    lines.extend(
        (
            "",
            "Signals are evidence-ranked triage prompts, not inferred game rules. "
            "Inspect the linked cognitive stream before designing a mechanism.",
            "",
        )
    )
    return "\n".join(lines)


def _run_probe(args: argparse.Namespace, output_dir: Path) -> Path:
    recordings = output_dir / "recordings"
    cognitive = output_dir / "cognitive"
    report = output_dir / "official-report.json"
    recordings.mkdir(parents=True, exist_ok=True)
    cognitive.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "reflector.cli",
        "official-isolated-run",
        *args.games,
        "--environments-dir",
        str(args.environments_dir),
        "--recordings-dir",
        str(recordings),
        "--output",
        str(report),
        "--config",
        str(args.config),
        "--max-workers",
        str(args.workers),
        "--timeout",
        str(args.timeout),
        "--cognitive-stream-dir",
        str(cognitive),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("games", nargs="+")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = (
        output_dir / "official-report.json"
        if args.analyze_only
        else _run_probe(args, output_dir)
    )
    insights = analyze_probe(report, output_dir / "cognitive")
    json_path = output_dir / "insights.json"
    markdown_path = output_dir / "INSIGHTS.md"
    json_path.write_text(
        json.dumps([asdict(item) for item in insights], indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(insights), encoding="utf-8")
    print(report)
    print(json_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
