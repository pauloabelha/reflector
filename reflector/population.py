"""Constrained symbolic genomes, lineage, and multi-objective selection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .mind import MindConfig


def _stable_id(prefix: str, value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    config: MindConfig
    parent_id: str | None = None
    generation: int = 0
    rationale: str = "root"

    @classmethod
    def create(
        cls,
        config: MindConfig,
        parent_id: str | None = None,
        generation: int = 0,
        rationale: str = "root",
    ) -> "Candidate":
        identity = {
            "config": config.to_dict(),
            "parent_id": parent_id,
            "generation": generation,
            "rationale": rationale,
        }
        return cls(
            _stable_id("candidate", identity),
            config,
            parent_id,
            generation,
            rationale,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "config": self.config.to_dict(),
            "parent_id": self.parent_id,
            "generation": self.generation,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Candidate":
        return cls(
            candidate_id=value["candidate_id"],
            config=MindConfig.from_dict(value["config"]),
            parent_id=value.get("parent_id"),
            generation=value["generation"],
            rationale=value["rationale"],
        )


@dataclass(frozen=True, slots=True)
class Fitness:
    """Objectives derived from trace replay; higher is better except costs."""

    levels_advanced: int
    deterministic_replay_rate: float
    mean_schema_reliability: float
    planner_expansions: int
    schema_description_length: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Fitness":
        return cls(**value)

    def dominates(self, other: "Fitness") -> bool:
        mine = (
            self.levels_advanced,
            self.deterministic_replay_rate,
            self.mean_schema_reliability,
            -self.planner_expansions,
            -self.schema_description_length,
        )
        theirs = (
            other.levels_advanced,
            other.deterministic_replay_rate,
            other.mean_schema_reliability,
            -other.planner_expansions,
            -other.schema_description_length,
        )
        return all(left >= right for left, right in zip(mine, theirs)) and any(
            left > right for left, right in zip(mine, theirs)
        )


def pareto_archive(
    evaluated: Iterable[tuple[Candidate, Fitness]],
) -> tuple[tuple[Candidate, Fitness], ...]:
    entries = tuple(evaluated)
    archive = [
        entry
        for index, entry in enumerate(entries)
        if not any(
            other_fitness.dominates(entry[1])
            for other_index, (_, other_fitness) in enumerate(entries)
            if other_index != index
        )
    ]
    return tuple(sorted(archive, key=lambda item: item[0].candidate_id))
