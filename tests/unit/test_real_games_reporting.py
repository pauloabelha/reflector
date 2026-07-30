import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_REPORT = (
    ROOT
    / "reports"
    / "official-isolated-v65b-public-400.json"
)


def test_human_reports_match_accepted_scorecard() -> None:
    payload = json.loads(ACCEPTED_REPORT.read_text(encoding="utf-8"))
    scorecard = payload["scorecard"]
    environments = scorecard["environments"]

    games_evaluated = len(environments)
    games_beaten = sum(bool(item["completed"]) for item in environments)
    games_with_progress = sum(
        item["levels_completed"] > 0 for item in environments
    )
    levels_solved = sum(item["levels_completed"] for item in environments)
    total_levels = sum(item["level_count"] for item in environments)
    actions = sum(item["actions"] for item in environments)
    score = scorecard["score"]

    canonical = (ROOT / "REAL_GAMES_REPORT.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    expected_fragments = (
        f"**{games_beaten} / {games_evaluated}**",
        f"**{games_with_progress} / {games_evaluated}**",
        f"**{levels_solved} / {total_levels}**",
        f"**{score:.10f} / 100**",
        f"**{games_evaluated} / {games_evaluated} games**",
        f"**{actions:,}**",
    )
    for fragment in expected_fragments:
        assert fragment in canonical

    assert f"beaten **{games_beaten} of {games_evaluated}" in readme
    assert f"**{levels_solved} of {total_levels} levels" in readme
    assert f"**{score} / 100**" in readme
