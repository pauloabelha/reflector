"""Prospective, bounded credit for structurally repeated terminal edges.

One terminal observation may propose that an abstract state/action edge is
unsafe, but it cannot authorize avoidance.  Authority requires the same
color- and global-translation-invariant scene form and action role to terminate
from a second distinct concrete predecessor.  A later non-terminal outcome
quarantines the abstraction, preventing an aliased edge from steering policy.
"""

from __future__ import annotations

import hashlib
from collections.abc import Hashable
from dataclasses import dataclass, field

from .action_translation_algebra import Frame, structural_source_signature

type AbstractTerminalEdge = tuple[str, Hashable]

HARD_MAX_TERMINAL_EDGES = 512
HARD_MAX_CONCRETE_SOURCES = 64


@dataclass(frozen=True, slots=True)
class TerminalViabilityBounds:
    """Hard-bounded episode-local evidence limits."""

    max_edges: int = 128
    max_concrete_sources_per_edge: int = 16
    min_distinct_terminal_sources: int = 2

    def __post_init__(self) -> None:
        limits = (
            ("max_edges", self.max_edges, HARD_MAX_TERMINAL_EDGES),
            (
                "max_concrete_sources_per_edge",
                self.max_concrete_sources_per_edge,
                HARD_MAX_CONCRETE_SOURCES,
            ),
            (
                "min_distinct_terminal_sources",
                self.min_distinct_terminal_sources,
                HARD_MAX_CONCRETE_SOURCES,
            ),
        )
        for name, value, hard_limit in limits:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= hard_limit
            ):
                raise ValueError(f"{name} must be in [1, {hard_limit}]")
        if self.min_distinct_terminal_sources > self.max_concrete_sources_per_edge:
            raise ValueError("minimum terminal sources cannot exceed the source cap")


@dataclass(frozen=True, slots=True)
class TerminalViabilityUpdate:
    """One prospective evidence update."""

    diagnostic: str
    authority: bool
    distinct_terminal_sources: int
    quarantined: bool
    cap_failure: str | None = None


@dataclass(slots=True)
class TerminalEdgeViability:
    """Finite version space over undefined structural morphisms."""

    bounds: TerminalViabilityBounds = field(default_factory=TerminalViabilityBounds)
    terminal_sources: dict[AbstractTerminalEdge, set[str]] = field(default_factory=dict)
    quarantined_edges: set[AbstractTerminalEdge] = field(default_factory=set)
    observations: int = 0
    terminal_observations: int = 0
    proposals: int = 0
    predictions: int = 0
    confirmations: int = 0
    contradictions: int = 0
    cap_failure: str | None = None
    last_diagnostic: str = "exact-off"

    def reset_level(self) -> None:
        """Forget level-specific viability while retaining lifetime telemetry."""

        self.terminal_sources.clear()
        self.quarantined_edges.clear()
        self.cap_failure = None
        self.last_diagnostic = "level-reset"

    @staticmethod
    def concrete_source(frame: Frame) -> str:
        """Content-address one exact predecessor without retaining the frame."""

        return hashlib.sha256(repr(frame).encode()).hexdigest()

    def edge(
        self,
        frame: Frame,
        role: Hashable,
    ) -> AbstractTerminalEdge | None:
        """Return the nuisance-quotiented scene/role edge when representable."""

        source = structural_source_signature(frame)
        if source is None:
            return None
        return (source, role)

    def observe(
        self,
        *,
        frame: Frame,
        role: Hashable,
        terminal: bool,
    ) -> TerminalViabilityUpdate:
        """Register a terminal proposal, prospective confirmation, or conflict."""

        self.observations += 1
        if terminal:
            self.terminal_observations += 1
        edge = self.edge(frame, role)
        if edge is None:
            return self._update("unrepresentable-structural-source")
        if self.cap_failure is not None:
            return self._update(
                f"fail-closed:{self.cap_failure}",
                cap_failure=self.cap_failure,
            )
        if edge in self.quarantined_edges:
            return self._update("abstain:quarantined-terminal-edge", edge=edge)

        sources = self.terminal_sources.get(edge)
        if not terminal:
            if sources:
                self.quarantined_edges.add(edge)
                self.terminal_sources.pop(edge, None)
                self.contradictions += 1
                return self._update(
                    "safe-counterexample-quarantined-edge",
                    edge=edge,
                )
            return self._update("nonterminal-without-hypothesis")

        concrete = self.concrete_source(frame)
        if sources is None:
            if len(self.terminal_sources) >= self.bounds.max_edges:
                self.cap_failure = "terminal-edge-cap-exceeded"
                return self._update(
                    "fail-closed:terminal-edge-cap-exceeded",
                    cap_failure=self.cap_failure,
                )
            self.terminal_sources[edge] = {concrete}
            self.proposals += 1
            return self._update("proposed-terminal-edge", edge=edge)
        if concrete in sources:
            return self._update("duplicate-concrete-terminal-source", edge=edge)
        if len(sources) >= self.bounds.max_concrete_sources_per_edge:
            self.cap_failure = "terminal-source-cap-exceeded"
            return self._update(
                "fail-closed:terminal-source-cap-exceeded",
                edge=edge,
                cap_failure=self.cap_failure,
            )
        self.predictions += 1
        sources.add(concrete)
        if len(sources) >= self.bounds.min_distinct_terminal_sources:
            self.confirmations += 1
            return self._update("prospectively-confirmed-terminal-edge", edge=edge)
        return self._update("additional-terminal-source", edge=edge)

    def authoritative(self, frame: Frame, role: Hashable) -> bool:
        """Whether this structural edge is prospectively confirmed terminal."""

        edge = self.edge(frame, role)
        return self.authoritative_edge(edge)

    def authoritative_edge(
        self,
        edge: AbstractTerminalEdge | None,
    ) -> bool:
        """Check a precomputed structural edge without re-parsing its frame."""

        return (
            edge is not None
            and edge not in self.quarantined_edges
            and len(self.terminal_sources.get(edge, ()))
            >= self.bounds.min_distinct_terminal_sources
        )

    def _update(
        self,
        diagnostic: str,
        *,
        edge: AbstractTerminalEdge | None = None,
        cap_failure: str | None = None,
    ) -> TerminalViabilityUpdate:
        self.last_diagnostic = diagnostic
        sources = self.terminal_sources.get(edge, ()) if edge is not None else ()
        return TerminalViabilityUpdate(
            diagnostic,
            (
                edge is not None
                and edge not in self.quarantined_edges
                and len(sources) >= self.bounds.min_distinct_terminal_sources
            ),
            len(sources),
            edge in self.quarantined_edges if edge is not None else False,
            cap_failure,
        )
