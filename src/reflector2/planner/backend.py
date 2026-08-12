"""Pluggable planner backend boundary.

Backends depend only on the planner's generic problem/result contracts.  A
controller may adapt its own situated state into a ``ControlProblem``; no
controller implementation is part of this API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .factorization import ControlProblem, PlannerConfig, SearchResult
from .search import search as bounded_best_first_search


@runtime_checkable
class PlannerBackend(Protocol):
    """Minimal interface for interchangeable control-factorization search."""

    name: str

    def search(self, problem: ControlProblem, config: PlannerConfig) -> SearchResult:
        """Return a bounded result without mutating the supplied problem."""


@dataclass(frozen=True, slots=True)
class BoundedBestFirstPlanner:
    """Default deterministic backend shipped with the planner package."""

    name: str = "bounded-best-first-v0"

    def search(self, problem: ControlProblem, config: PlannerConfig) -> SearchResult:
        return bounded_best_first_search(problem, config)


@dataclass(frozen=True, slots=True)
class NoPlanPlanner:
    """Backend that cleanly delegates every decision to the host controller."""

    name: str = "fallback-only-v0"

    def search(self, problem: ControlProblem, config: PlannerConfig) -> SearchResult:
        del problem
        return SearchResult(
            status="NO_PLAN",
            factorization=None,
            expansions=0,
            generated=0,
            frontier_peak=0,
            maximum_depth_reached=0,
            elapsed_ms=0.0,
            config=config,
            reason="delegated-to-host-controller",
        )


def backend_from_name(name: str | None) -> PlannerBackend:
    """Construct a built-in backend from stable configuration names."""

    normalized = str(name or "bounded-best-first-v0").strip().lower()
    if normalized in {"bounded-best-first", "bounded-best-first-v0", "factorization"}:
        return BoundedBestFirstPlanner()
    if normalized in {"fallback-only", "fallback-only-v0", "none", "original", "one-step"}:
        return NoPlanPlanner()
    raise ValueError(f"unknown planner backend: {name!r}")


def require_backend(value: PlannerBackend | None) -> PlannerBackend:
    """Resolve the default and fail early on malformed injected backends."""

    backend = value or BoundedBestFirstPlanner()
    if not isinstance(backend, PlannerBackend):
        raise TypeError("planner backend must expose a name and search(problem, config)")
    return backend
