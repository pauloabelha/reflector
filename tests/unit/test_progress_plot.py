from pathlib import Path

import pytest

from scripts.generate_progress_plot import load_generations


def _score_report(row: str) -> str:
    return "\n".join(
        (
            "# Test report",
            "",
            "## Score evolution",
            "",
            "| Version | Local score / 100 | Levels solved | "
            "Games with progress | Games beaten | Main change | Decision |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- |",
            row,
            "",
            "## Next section",
        )
    )


def test_progress_plot_loads_every_canonical_score_row() -> None:
    generations = load_generations()

    assert len(generations) == 26
    assert len({item.version for item in generations}) == len(generations)
    assert tuple(
        item.version for item in generations if not item.accepted
    ) == ("v21", "v25 ablation", "v26d", "v28")
    assert tuple(
        item.version
        for item in generations
        if item.decision == "current accepted"
    ) == ("v69",)


def test_progress_plot_rejects_a_malformed_score_row(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text(
        _score_report("| v1 | bad | 1 | 1 | 0 | change | baseline |"),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="invalid numeric"):
        load_generations(report)


def test_progress_plot_rejects_an_unknown_decision(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text(
        _score_report("| v1 | 1.0 | 1 | 1 | 0 | change | maybe |"),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="unknown Score evolution decision"):
        load_generations(report)


@pytest.mark.parametrize(
    ("row", "message"),
    (
        (
            "| v1 | nan | 1 | 1 | 0 | change | current accepted |",
            "score is outside",
        ),
        (
            "| v1 | 1.0 | 184 | 1 | 0 | change | current accepted |",
            "level count is outside",
        ),
        (
            "| v1 | 1.0 | 2 | 1 | 2 | change | current accepted |",
            "beaten-game count exceeds",
        ),
        (
            "| v1 | 1.0 | 1 | 2 | 0 | change | current accepted |",
            "progress games exceed solved levels",
        ),
    ),
)
def test_progress_plot_rejects_impossible_metrics(
    tmp_path: Path,
    row: str,
    message: str,
) -> None:
    report = tmp_path / "report.md"
    report.write_text(_score_report(row), encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        load_generations(report)
