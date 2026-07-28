"""Strict inventory for the accepted official public environment suite."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class OfficialEnvironmentArtifact:
    game_id: str
    versioned_game_id: str
    metadata_path: str
    metadata_sha256: str
    date_downloaded: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OfficialEnvironmentInventory:
    root: str
    expected_games: int
    games: tuple[str, ...]
    artifacts: tuple[OfficialEnvironmentArtifact, ...]
    manifest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "expected_games": self.expected_games,
            "games": list(self.games),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "manifest_sha256": self.manifest_sha256,
        }


def inventory_official_environments(
    root: Path,
    *,
    expected_games: int,
) -> OfficialEnvironmentInventory:
    """Discover versioned toolkit metadata and require exact game coverage."""

    resolved = root.resolve()
    if not resolved.is_dir():
        raise ValueError(f"environment directory does not exist: {resolved}")
    artifacts: list[OfficialEnvironmentArtifact] = []
    for metadata_path in sorted(resolved.rglob("metadata.json")):
        raw = metadata_path.read_bytes()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid environment metadata: {metadata_path}"
            ) from error
        if not isinstance(value, dict):
            raise ValueError(
                f"environment metadata must be an object: {metadata_path}"
            )
        versioned = value.get("game_id")
        if not isinstance(versioned, str) or not versioned:
            raise ValueError(
                f"environment metadata has no game_id: {metadata_path}"
            )
        game_id = versioned.split("-", 1)[0]
        downloaded = value.get("date_downloaded", "")
        artifacts.append(
            OfficialEnvironmentArtifact(
                game_id=game_id,
                versioned_game_id=versioned,
                metadata_path=str(metadata_path.relative_to(resolved)),
                metadata_sha256=hashlib.sha256(raw).hexdigest(),
                date_downloaded=(
                    downloaded if isinstance(downloaded, str) else ""
                ),
            )
        )
    games = tuple(sorted({item.game_id for item in artifacts}))
    if len(games) != expected_games:
        raise ValueError(
            "official public suite is incomplete: "
            f"expected {expected_games} unique games, found {len(games)} "
            f"under {resolved}"
        )
    canonical = json.dumps(
        [item.to_dict() for item in artifacts],
        sort_keys=True,
        separators=(",", ":"),
    )
    return OfficialEnvironmentInventory(
        root=str(resolved),
        expected_games=expected_games,
        games=games,
        artifacts=tuple(artifacts),
        manifest_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
    )


def expected_public_game_count(project_root: Path) -> int:
    snapshot = json.loads(
        (
            project_root / "competition" / "arc_agi_3_2026.json"
        ).read_text(encoding="utf-8")
    )
    value = snapshot.get("public_development_games")
    if type(value) is not int or value < 1:
        raise ValueError(
            "rules snapshot has no positive public_development_games count"
        )
    return value
