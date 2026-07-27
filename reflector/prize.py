"""Repeatable ARC Prize 2026 technical and publication readiness audit."""

from __future__ import annotations

import argparse
import base64
import io
import json
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

from .deployment import CONFIG_ENV
from .kaggle import OVERLAY_FILES, ROOT, _notebook, build_overlay
from .mind import MindConfig

OFFICIAL_STARTER = "https://github.com/arcprize/ARC-AGI-3-Agents.git"
INFERENCE_FORBIDDEN = (
    "reflector/evolver.py",
    "reflector/experiments.py",
    "reflector/mutations.py",
    "reflector/population.py",
    "reflector/prize.py",
    "reflector/sandbox.py",
    "reflector/transforms.py",
    "reflector/web_api.py",
)


@dataclass(frozen=True, slots=True)
class AuditCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class PrizeAudit:
    competition: dict[str, Any]
    paper_competition: dict[str, Any]
    checks: tuple[AuditCheck, ...]

    @property
    def technical_ready(self) -> bool:
        return not any(item.status == "fail" for item in self.checks)

    @property
    def prize_ready(self) -> bool:
        return self.technical_ready and all(
            item.status == "pass" for item in self.checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition": self.competition,
            "paper_competition": self.paper_competition,
            "technical_ready": self.technical_ready,
            "prize_ready": self.prize_ready,
            "checks": [asdict(item) for item in self.checks],
        }


def _check(name: str, condition: bool, detail: str) -> AuditCheck:
    return AuditCheck(name, "pass" if condition else "fail", detail)


def _manual(name: str, detail: str) -> AuditCheck:
    return AuditCheck(name, "manual", detail)


def _origin(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def audit(root: Path = ROOT) -> PrizeAudit:
    snapshot_path = root / "competition" / "arc_agi_3_2026.json"
    competition = json.loads(snapshot_path.read_text(encoding="utf-8"))
    paper_path = root / "competition" / "arc_prize_2026_paper.json"
    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    audit_date = date.fromisoformat(competition["audit_date"])
    paper_audit_date = date.fromisoformat(paper["audit_date"])
    snapshot_age = max(
        (date.today() - audit_date).days,
        (date.today() - paper_audit_date).days,
    )
    overlay = build_overlay()
    with zipfile.ZipFile(io.BytesIO(overlay)) as archive:
        names = set(archive.namelist())

    notebook = _notebook(
        base64.b64encode(overlay).decode("ascii"),
        MindConfig(),
    )
    cells = cast(list[dict[str, Any]], notebook["cells"])
    notebook_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in cells
    )
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    origin = _origin(root)
    own_public_remote = bool(
        origin
        and origin != OFFICIAL_STARTER
        and origin.startswith(("https://github.com/", "git@github.com:"))
    )

    checks = (
        _check(
            "rules_freshness",
            0 <= snapshot_age <= 14,
            f"Rules snapshot is {snapshot_age} days old; refresh at least "
            "every 14 days and before every submission.",
        ),
        _check(
            "rules_snapshot",
            competition.get("max_cpu_runtime_minutes") == 540
            and competition.get("internet_enabled") is False
            and competition.get("required_submission_filename")
            == "submission.parquet",
            "The dated machine-readable snapshot records the 9-hour, "
            "offline, notebook-only competition envelope.",
        ),
        _check(
            "paper_track_snapshot",
            paper.get("max_submissions_per_team") == 1
            and paper.get("team_must_match_linked_code_submission") is True
            and paper.get("writeup_word_limit") == 1500
            and paper.get("winner_license") == "CC-BY-4.0",
            "The Paper Track snapshot records its matching-team, one-writeup, "
            "1,500-word, public-notebook, and winner-license gates.",
        ),
        _check(
            "inference_allowlist",
            names == set(OVERLAY_FILES)
            and not names.intersection(INFERENCE_FORBIDDEN),
            "The overlay contains exactly the reviewed inference closure and "
            "no evolver, database, web, or audit module.",
        ),
        _check(
            "gateway_contract",
            "http://gateway:8001/api/games" in notebook_source
            and "three.arcprize.org" not in notebook_source
            and "/kaggle/working" in notebook_source
            and "submission.parquet" in notebook_source,
            "The notebook uses only the required local gateway and writable "
            "Kaggle path.",
        ),
        _check(
            "offline_install",
            "%pip install --no-index --find-links" in notebook_source
            and "arc_agi_3_wheels" in notebook_source,
            "Runtime packages are installed only from competition wheels.",
        ),
        _check(
            "direct_candidate_export",
            CONFIG_ENV in notebook_source
            and "reflector/deployment.py" in names,
            "The complete MindConfig genome is embedded without rewriting "
            "the shared symbolic policy.",
        ),
        _check(
            "artifact_size",
            len(overlay)
            <= int(competition["submission_size_limit_mb"]) * 1024 * 1024,
            f"Overlay is {len(overlay)} bytes; Kaggle limit is "
            f"{competition['submission_size_limit_mb']} MB.",
        ),
        _check(
            "winner_license",
            "MIT No Attribution License (MIT-0)" in license_text
            and "Creative Commons Attribution 4.0 International" in license_text
            and (root / "THIRD_PARTY_NOTICES.md").is_file(),
            "Reflector contributions cover the ARC public-domain preference "
            "and CC-BY-4.0 winner grant; upstream MIT material is separated.",
        ),
        _check(
            "open_source_ai_disclosure",
            (root / "OPEN_SOURCE_AI.md").is_file(),
            "System, model, parameters, data information, and the absence of "
            "neural weights are disclosed.",
        ),
        _manual(
            "public_repository",
            (
                f"Current origin is {origin!r}; publish Reflector from a "
                "participant-owned public repository."
                if not own_public_remote
                else f"Confirm that {origin!r} is publicly readable."
            ),
        ),
        _manual(
            "participant_eligibility",
            "Accept rules, complete Kaggle identity verification, and confirm "
            "age, jurisdiction, sanctions, employer, and tax eligibility.",
        ),
        _manual(
            "kaggle_rerun",
            "Attach competition data, disable internet in notebook settings, "
            "commit a full rerun, and confirm a scored submission.",
        ),
        _manual(
            "public_evaluation",
            "Provide an official ARC API key or accepted Kaggle data access, "
            "run all 25 public environments, and archive held-out RHAE, "
            "completion, runtime, and ablation evidence.",
        ),
        _manual(
            "competition_publication",
            "Publish the exact notebook through Kaggle and share public code "
            "through the competition before private scoring or prize review.",
        ),
        _manual(
            "paper_submission",
            "Keep the Paper Track team identical to the ARC-AGI-3 team and "
            "submit its sole <=1,500-word Writeup with cover media, public "
            "notebook, selected track, and code submission ID.",
        ),
    )
    return PrizeAudit(competition, paper, checks)


def main() -> None:
    parser = argparse.ArgumentParser(prog="reflector-prize-audit")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail while account/publication checks remain manual",
    )
    args = parser.parse_args()
    report = audit()
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for item in report.checks:
            print(f"{item.status.upper():6} {item.name}: {item.detail}")
        print(
            "TECHNICAL_READY="
            f"{str(report.technical_ready).lower()} "
            f"PRIZE_READY={str(report.prize_ready).lower()}"
        )
    if not report.technical_ready or (args.strict and not report.prize_ready):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
