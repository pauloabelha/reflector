import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_REPORT = (
    ROOT
    / "reports"
    / "official-isolated-v68-frozen-public-400.json"
)
ACCEPTED_CANDIDATE = (
    ROOT
    / "candidates"
    / "v68-path-cycle-transport-400.json"
)
TARGET_REPORTS = (
    ROOT / "reports" / "official-isolated-v68-frozen-lp85-r1-400.json",
    ROOT / "reports" / "official-isolated-v68-frozen-lp85-r2-400.json",
)
PRESERVATION_REPORT = (
    ROOT
    / "reports"
    / "official-isolated-v68-frozen-progress-gate-400.json"
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


def test_canonical_report_binds_the_frozen_v68_evidence() -> None:
    canonical = (ROOT / "REAL_GAMES_REPORT.md").read_text(encoding="utf-8")
    scorecard = json.loads(ACCEPTED_REPORT.read_text(encoding="utf-8"))
    candidate = json.loads(ACCEPTED_CANDIDATE.read_text(encoding="utf-8"))

    assert scorecard["source_commit"] in canonical
    assert candidate["candidate_id"] in canonical
    assert candidate["inference_fingerprint"] in canonical
    assert candidate["parent_id"] == "candidate-a1ccbdb17d674b78"
    for artifact in (
        ACCEPTED_CANDIDATE,
        ACCEPTED_REPORT,
        *TARGET_REPORTS,
        PRESERVATION_REPORT,
    ):
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert digest in canonical


def test_canonical_report_local_links_resolve() -> None:
    report = ROOT / "REAL_GAMES_REPORT.md"
    canonical = report.read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", canonical)
    local_targets = (
        target.split("#", 1)[0]
        for target in targets
        if "://" not in target
    )

    missing = tuple(
        target
        for target in local_targets
        if target and not (report.parent / target).exists()
    )
    assert missing == ()
