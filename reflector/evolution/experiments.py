"""Reproducible experiment manifests and local SQLite persistence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..runtime.trace import AGENT_VERSION, EpisodeTrace
from .population import Candidate, Fitness, pareto_archive


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    experiment_id: str
    name: str
    seed: int
    trace_hashes: tuple[tuple[str, str], ...]
    holdout_seeds: tuple[int, ...]
    agent_version: str
    created_at: str

    @classmethod
    def create(
        cls,
        name: str,
        seed: int,
        traces: dict[str, EpisodeTrace],
        holdout_seeds: tuple[int, ...] = (101, 211),
    ) -> "ExperimentManifest":
        trace_hashes = tuple(
            (trace_name, hashlib.sha256(trace.to_json().encode()).hexdigest())
            for trace_name, trace in sorted(traces.items())
        )
        identity = {
            "name": name,
            "seed": seed,
            "trace_hashes": trace_hashes,
            "holdout_seeds": holdout_seeds,
            "agent_version": AGENT_VERSION,
        }
        digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode()
        ).hexdigest()[:16]
        return cls(
            experiment_id=f"experiment-{digest}",
            name=name,
            seed=seed,
            trace_hashes=trace_hashes,
            holdout_seeds=holdout_seeds,
            agent_version=AGENT_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["trace_hashes"] = dict(self.trace_hashes)
        return value


class ExperimentStore:
    """Development database. Nothing in the inference package imports it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                manifest_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidates (
                experiment_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                parent_id TEXT,
                candidate_json TEXT NOT NULL,
                PRIMARY KEY (experiment_id, candidate_id),
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            );
            CREATE TABLE IF NOT EXISTS evaluations (
                experiment_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                fitness_json TEXT NOT NULL,
                details_json TEXT NOT NULL,
                PRIMARY KEY (experiment_id, candidate_id),
                FOREIGN KEY (experiment_id, candidate_id)
                    REFERENCES candidates(experiment_id, candidate_id)
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ExperimentStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def save_manifest(self, manifest: ExperimentManifest) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO experiments VALUES (?, ?)",
            (
                manifest.experiment_id,
                json.dumps(manifest.to_dict(), sort_keys=True),
            ),
        )
        self.connection.commit()

    def save_candidate(
        self, experiment_id: str, candidate: Candidate
    ) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO candidates VALUES (?, ?, ?, ?)",
            (
                experiment_id,
                candidate.candidate_id,
                candidate.parent_id,
                json.dumps(candidate.to_dict(), sort_keys=True),
            ),
        )
        self.connection.commit()

    def save_evaluation(
        self,
        experiment_id: str,
        candidate_id: str,
        fitness: Fitness,
        details: dict[str, Any],
    ) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO evaluations VALUES (?, ?, ?, ?)",
            (
                experiment_id,
                candidate_id,
                json.dumps(fitness.to_dict(), sort_keys=True),
                json.dumps(details, sort_keys=True),
            ),
        )
        self.connection.commit()

    def lineage(
        self, experiment_id: str, candidate_id: str
    ) -> tuple[Candidate, ...]:
        rows = self.connection.execute(
            "SELECT candidate_json FROM candidates WHERE experiment_id = ?",
            (experiment_id,),
        )
        candidates = {
            item.candidate_id: item
            for item in (
                Candidate.from_dict(json.loads(row["candidate_json"]))
                for row in rows
            )
        }
        result: list[Candidate] = []
        cursor: str | None = candidate_id
        seen: set[str] = set()
        while cursor is not None:
            if cursor in seen or cursor not in candidates:
                raise ValueError("broken or cyclic candidate lineage")
            seen.add(cursor)
            candidate = candidates[cursor]
            result.append(candidate)
            cursor = candidate.parent_id
        return tuple(reversed(result))

    def evaluated(
        self, experiment_id: str
    ) -> tuple[tuple[Candidate, Fitness], ...]:
        rows = self.connection.execute(
            """
            SELECT c.candidate_json, e.fitness_json
            FROM candidates c JOIN evaluations e
              ON c.experiment_id = e.experiment_id
             AND c.candidate_id = e.candidate_id
            WHERE c.experiment_id = ?
            ORDER BY c.candidate_id
            """,
            (experiment_id,),
        )
        return tuple(
            (
                Candidate.from_dict(json.loads(row["candidate_json"])),
                Fitness.from_dict(json.loads(row["fitness_json"])),
            )
            for row in rows
        )

    def list_experiments(self) -> tuple[dict[str, Any], ...]:
        rows = self.connection.execute(
            """
            SELECT x.manifest_json, COUNT(c.candidate_id) AS candidate_count
            FROM experiments x
            LEFT JOIN candidates c ON x.experiment_id = c.experiment_id
            GROUP BY x.experiment_id
            ORDER BY x.experiment_id
            """
        )
        output = []
        for row in rows:
            manifest = json.loads(row["manifest_json"])
            manifest["candidate_count"] = row["candidate_count"]
            output.append(manifest)
        return tuple(output)

    def experiment_report(self, experiment_id: str) -> dict[str, Any]:
        manifest_row = self.connection.execute(
            "SELECT manifest_json FROM experiments WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
        if manifest_row is None:
            raise KeyError(experiment_id)
        rows = self.connection.execute(
            """
            SELECT c.candidate_json, e.fitness_json, e.details_json
            FROM candidates c
            LEFT JOIN evaluations e
              ON c.experiment_id = e.experiment_id
             AND c.candidate_id = e.candidate_id
            WHERE c.experiment_id = ?
            ORDER BY c.candidate_id
            """,
            (experiment_id,),
        )
        candidates: list[dict[str, Any]] = []
        evaluated: list[tuple[Candidate, Fitness]] = []
        for row in rows:
            candidate = Candidate.from_dict(json.loads(row["candidate_json"]))
            fitness = (
                Fitness.from_dict(json.loads(row["fitness_json"]))
                if row["fitness_json"] is not None
                else None
            )
            if fitness is not None:
                evaluated.append((candidate, fitness))
            candidates.append(
                {
                    "candidate": candidate.to_dict(),
                    "fitness": fitness.to_dict() if fitness is not None else None,
                    "details": (
                        json.loads(row["details_json"])
                        if row["details_json"] is not None
                        else None
                    ),
                }
            )
        archive_ids = {
            candidate.candidate_id
            for candidate, _fitness in pareto_archive(evaluated)
        }
        for item in candidates:
            item["pareto"] = (
                item["candidate"]["candidate_id"] in archive_ids
            )
        by_id = {
            item["candidate"]["candidate_id"]: item for item in candidates
        }
        lower_is_better = {
            "planner_expansions",
            "schema_description_length",
            "genome_description_length",
        }
        for item in candidates:
            parent_id = item["candidate"]["parent_id"]
            parent = by_id.get(parent_id)
            if (
                parent is None
                or parent["fitness"] is None
                or item["fitness"] is None
            ):
                item["parent_improvement"] = None
                continue
            improvement = {}
            for metric, value in item["fitness"].items():
                delta = value - parent["fitness"][metric]
                improvement[metric] = (
                    -delta if metric in lower_is_better else delta
                )
            item["parent_improvement"] = improvement
        return {
            "manifest": json.loads(manifest_row["manifest_json"]),
            "candidates": candidates,
            "lineage_edges": [
                {
                    "source": item["candidate"]["parent_id"],
                    "target": item["candidate"]["candidate_id"],
                }
                for item in candidates
                if item["candidate"]["parent_id"] is not None
            ],
        }
