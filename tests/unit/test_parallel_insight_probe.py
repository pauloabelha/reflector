import json
from pathlib import Path

from scripts.run_parallel_insight_probe import analyze_probe, render_markdown


def test_parallel_probe_surfaces_cross_game_mechanism_gaps(tmp_path: Path) -> None:
    report = tmp_path / "official-report.json"
    cognitive = tmp_path / "cognitive"
    cognitive.mkdir()
    report.write_text(
        json.dumps(
            {
                "scorecard": {
                    "environments": [
                        {
                            "id": "alpha-deadbeef",
                            "level_count": 3,
                            "runs": [
                                {
                                    "score": 5.0,
                                    "levels_completed": 1,
                                    "actions": 6,
                                    "level_actions": [2, 4, 0],
                                }
                            ],
                        },
                        {
                            "id": "beta-feedface",
                            "level_count": 2,
                            "runs": [
                                {
                                    "score": 0.0,
                                    "levels_completed": 0,
                                    "actions": 4,
                                    "level_actions": [4, 0],
                                }
                            ],
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    alpha = [
        {
            "observation": {"levels_completed": level},
            "decision": {"reason": "epistemic-frontier:colored-stencil-primary"},
            "operative_state": {
                "exploration": {
                    "colored_stencil_predictions": index,
                    "colored_stencil_confirmations": index,
                    "colored_stencil_conflicts": 0,
                    "colored_stencil_diagnostic": "executing-plan",
                }
            },
        }
        for index, level in enumerate((0, 0, 1, 1, 1, 1))
    ]
    beta = [
        {
            "observation": {"levels_completed": 0},
            "decision": {"reason": "epistemic-frontier:untried-current-state"},
            "operative_state": {"exploration": {}},
        }
        for _index in range(4)
    ]
    for game, events in (("alpha", alpha), ("beta", beta)):
        (cognitive / f"{game}.cognitive.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events) + "\n",
            encoding="utf-8",
        )

    insights = analyze_probe(report, cognitive)

    assert [item.game for item in insights] == ["alpha", "beta"]
    assert insights[0].causal_predictions == 5
    assert insights[0].causal_confirmations == 5
    assert insights[0].mechanism_advisor_actions == 6
    assert "post-progress" in insights[0].triage_signal
    assert "no grounded advisor" in insights[1].triage_signal
    markdown = render_markdown(insights)
    assert "`alpha`" in markdown
    assert "Causal P/C/X" in markdown
