"""Deterministic, content-addressed K-line retrieval for symbolic priors.

This module implements a deliberately non-operative memory layer.  A K-line
can recall the identity of an abstract prior and report why it was relevant,
but it cannot emit an action, coordinates, executable code, or an episode
specific binding.  A later runtime integration must ground a recalled prior
against fresh evidence before using it for planning.

Definitions are immutable and content addressed.  Evidence is represented by
separate records, so accumulating support never changes what a K-line digest
means.  Retrieval uses an exact sparse inverted index followed by bounded,
deterministic coarse and structural ranking.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Iterable, Literal, Self

_SCORE_SCALE = 1_000_000
_HARD_MAX_GENERATOR_IDS_PER_DEFINITION = 64
_HARD_MAX_STRUCTURAL_EXPANSIONS = 1_048_576
_INDEX_SCHEMA = "kline-sparse-round-robin-v2"
_SYMBOL = re.compile(r"^[a-z][a-z0-9]*(?:[-.][a-z0-9]+)*$")
_CONCRETE_IDENTIFIER = re.compile(
    r"(?:^|[-.])(?:action|colour|color|coordinate|game|palette|rgb|x|y)"
    r"-?id(?:[-.:=][0-9a-z]+)?$"
)
_FORBIDDEN_SYMBOLS = frozenset(
    {
        "absolute-coordinate",
        "absolute-position",
        "action-id",
        "color",
        "color-id",
        "colour",
        "colour-id",
        "column-index",
        "coordinate",
        "game-id",
        "palette-index",
        "pixel-coordinate",
        "rgb",
        "row-index",
        "x",
        "y",
    }
)
_HEX = frozenset("0123456789abcdef")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _content_digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _validate_abstract_symbol(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 96
        or _SYMBOL.fullmatch(value) is None
    ):
        raise ValueError(
            f"{field_name} must be a lower-case abstract symbol"
        )
    if value in _FORBIDDEN_SYMBOLS or _CONCRETE_IDENTIFIER.search(value):
        raise ValueError(
            f"{field_name} cannot encode a concrete coordinate, color, "
            "action, palette, or game identifier"
        )


def _validate_digest(value: str, *, field_name: str) -> None:
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise ValueError(f"{field_name} must be a lower-case SHA-256 digest")


class CueNamespace(StrEnum):
    """Closed namespaces spanning perceptual through intentional cues."""

    FORM = "form"
    TOPOLOGY = "topology"
    RELATION = "relation"
    DYNAMICS = "dynamics"
    CONTEXT = "context"
    GOAL = "goal"


@dataclass(frozen=True, order=True, slots=True)
class CueAtom:
    """One canonical, episode-equivariant retrieval cue."""

    namespace: CueNamespace
    feature: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.namespace, CueNamespace):
            raise ValueError("cue namespace must be a CueNamespace")
        _validate_abstract_symbol(self.feature, field_name="cue feature")
        _validate_abstract_symbol(self.value, field_name="cue value")

    @classmethod
    def create(
        cls,
        namespace: CueNamespace | str,
        feature: str,
        value: str,
    ) -> Self:
        return cls(CueNamespace(namespace), feature, value)

    @property
    def key(self) -> str:
        return f"{self.namespace.value}:{self.feature}:{self.value}"

    def to_dict(self) -> dict[str, str]:
        return {
            "namespace": self.namespace.value,
            "feature": self.feature,
            "value": self.value,
        }


def _canonical_atoms(
    atoms: Iterable[CueAtom],
    *,
    field_name: str,
) -> tuple[CueAtom, ...]:
    materialized = tuple(atoms)
    if any(not isinstance(atom, CueAtom) for atom in materialized):
        raise ValueError(f"{field_name} must contain only CueAtom values")
    return tuple(sorted(set(materialized)))


@dataclass(frozen=True, slots=True)
class KLineDefinition:
    """Immutable meaning of one recallable symbolic prior.

    ``cues`` are sparse retrieval keys.  ``preconditions`` must all occur in a
    query before recall is admitted, while any present ``contradictions`` force
    abstention.  None of these fields contains empirical support or an
    executable policy.
    """

    prior: str
    cues: tuple[CueAtom, ...]
    recalled_generator_ids: tuple[str, ...]
    preconditions: tuple[CueAtom, ...] = ()
    contradictions: tuple[CueAtom, ...] = ()
    minimum_cue_matches: int = 1
    minimum_namespace_matches: int = 1

    def __post_init__(self) -> None:
        _validate_abstract_symbol(self.prior, field_name="K-line prior")
        if type(self.recalled_generator_ids) is not tuple:
            raise ValueError(
                "K-line recalled generator IDs must be a tuple"
            )
        if not self.recalled_generator_ids:
            raise ValueError(
                "a K-line requires at least one recalled generator ID"
            )
        if (
            len(self.recalled_generator_ids)
            > _HARD_MAX_GENERATOR_IDS_PER_DEFINITION
        ):
            raise ValueError(
                "K-line recalled generator hard bound exceeded"
            )
        for generator_id in self.recalled_generator_ids:
            _validate_abstract_symbol(
                generator_id,
                field_name="recalled generator ID",
            )
        if self.recalled_generator_ids != tuple(
            sorted(set(self.recalled_generator_ids))
        ):
            raise ValueError(
                "recalled generator IDs must be sorted and duplicate-free"
            )
        for field_name in ("cues", "preconditions", "contradictions"):
            atoms = getattr(self, field_name)
            if type(atoms) is not tuple:
                raise ValueError(f"K-line {field_name} must be a tuple")
            if atoms != _canonical_atoms(atoms, field_name=field_name):
                raise ValueError(
                    f"K-line {field_name} must be sorted and duplicate-free"
                )
        if not self.cues:
            raise ValueError("a K-line requires at least one retrieval cue")
        if set(self.cues) & set(self.preconditions):
            raise ValueError("retrieval cues and preconditions must be disjoint")
        if set(self.contradictions) & (
            set(self.cues) | set(self.preconditions)
        ):
            raise ValueError(
                "contradictions cannot also be cues or preconditions"
            )
        if (
            type(self.minimum_cue_matches) is not int
            or not 1 <= self.minimum_cue_matches <= len(self.cues)
        ):
            raise ValueError("minimum cue matches must fit the cue count")
        namespace_count = len({cue.namespace for cue in self.cues})
        if (
            type(self.minimum_namespace_matches) is not int
            or not 1
            <= self.minimum_namespace_matches
            <= namespace_count
        ):
            raise ValueError(
                "minimum namespace matches must fit the cue namespaces"
            )

    @classmethod
    def create(
        cls,
        *,
        prior: str,
        cues: Iterable[CueAtom],
        recalled_generator_ids: Iterable[str],
        preconditions: Iterable[CueAtom] = (),
        contradictions: Iterable[CueAtom] = (),
        minimum_cue_matches: int = 1,
        minimum_namespace_matches: int = 1,
    ) -> Self:
        return cls(
            prior=prior,
            cues=_canonical_atoms(cues, field_name="cues"),
            recalled_generator_ids=tuple(
                sorted(set(recalled_generator_ids))
            ),
            preconditions=_canonical_atoms(
                preconditions,
                field_name="preconditions",
            ),
            contradictions=_canonical_atoms(
                contradictions,
                field_name="contradictions",
            ),
            minimum_cue_matches=minimum_cue_matches,
            minimum_namespace_matches=minimum_namespace_matches,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "contradictions": [
                atom.to_dict() for atom in self.contradictions
            ],
            "cues": [atom.to_dict() for atom in self.cues],
            "minimum_cue_matches": self.minimum_cue_matches,
            "minimum_namespace_matches": self.minimum_namespace_matches,
            "preconditions": [
                atom.to_dict() for atom in self.preconditions
            ],
            "prior": self.prior,
            "recalled_generator_ids": list(self.recalled_generator_ids),
            "version": "kline-definition-v2",
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def kline_id(self) -> str:
        """Return the full SHA-256 identity of definition content only."""

        return _content_digest(self.to_json())


EvidenceOutcome = Literal["supported", "falsified", "grounded"]


@dataclass(frozen=True, order=True, slots=True)
class KLineEvidence:
    """One external evidence reference that cannot alter definition identity."""

    kline_id: str
    episode_digest: str
    observation_digest: str
    outcome: EvidenceOutcome

    def __post_init__(self) -> None:
        _validate_digest(self.kline_id, field_name="K-line ID")
        _validate_digest(self.episode_digest, field_name="episode digest")
        _validate_digest(
            self.observation_digest,
            field_name="observation digest",
        )
        if self.outcome not in {"supported", "falsified", "grounded"}:
            raise ValueError("unknown K-line evidence outcome")

    @property
    def evidence_id(self) -> str:
        return _content_digest(
            _canonical_json(
                {
                    "episode_digest": self.episode_digest,
                    "kline_id": self.kline_id,
                    "observation_digest": self.observation_digest,
                    "outcome": self.outcome,
                }
            )
        )


@dataclass(frozen=True, slots=True)
class KLineBounds:
    """Hard deterministic construction and retrieval limits."""

    max_definitions: int = 65_536
    max_atoms_per_definition: int = 128
    max_generator_ids_per_definition: int = 16
    max_total_generator_refs: int = 262_144
    max_registered_generator_ids: int = 4_096
    max_total_postings: int = 1_048_576
    max_query_atoms: int = 64
    max_posting_visits: int = 8_192
    max_candidate_pool: int = 64
    max_exact_candidates: int = 16
    max_results: int = 4
    max_structural_expansions: int = 2_048

    def __post_init__(self) -> None:
        hard_caps = {
            "max_definitions": (1, 131_072),
            "max_atoms_per_definition": (1, 256),
            "max_generator_ids_per_definition": (
                1,
                _HARD_MAX_GENERATOR_IDS_PER_DEFINITION,
            ),
            "max_total_generator_refs": (1, 4_194_304),
            "max_registered_generator_ids": (1, 65_536),
            "max_total_postings": (1, 2_097_152),
            "max_query_atoms": (1, 128),
            "max_posting_visits": (1, 65_536),
            "max_candidate_pool": (1, 4_096),
            "max_exact_candidates": (1, 256),
            "max_results": (1, 64),
            "max_structural_expansions": (
                0,
                _HARD_MAX_STRUCTURAL_EXPANSIONS,
            ),
        }
        for field_name, (lower, upper) in hard_caps.items():
            value = getattr(self, field_name)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(
                    f"{field_name} must be between {lower} and {upper}"
                )
        if self.max_exact_candidates > self.max_candidate_pool:
            raise ValueError(
                "exact candidate cap cannot exceed candidate-pool cap"
            )
        if self.max_results > self.max_exact_candidates:
            raise ValueError("result cap cannot exceed exact candidate cap")
        if (
            self.max_generator_ids_per_definition
            > self.max_registered_generator_ids
        ):
            raise ValueError(
                "per-definition generator cap cannot exceed registry cap"
            )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_atoms_per_definition": self.max_atoms_per_definition,
            "max_candidate_pool": self.max_candidate_pool,
            "max_definitions": self.max_definitions,
            "max_exact_candidates": self.max_exact_candidates,
            "max_generator_ids_per_definition": (
                self.max_generator_ids_per_definition
            ),
            "max_posting_visits": self.max_posting_visits,
            "max_query_atoms": self.max_query_atoms,
            "max_registered_generator_ids": (
                self.max_registered_generator_ids
            ),
            "max_results": self.max_results,
            "max_structural_expansions": self.max_structural_expansions,
            "max_total_generator_refs": self.max_total_generator_refs,
            "max_total_postings": self.max_total_postings,
        }


@dataclass(frozen=True, slots=True)
class KLineSnapshot:
    """Canonical definition snapshot with a reproducible content root."""

    definitions: tuple[KLineDefinition, ...]
    root: str

    @classmethod
    def create(
        cls,
        definitions: Iterable[KLineDefinition],
        *,
        bounds: KLineBounds = KLineBounds(),
    ) -> Self:
        by_id: dict[str, KLineDefinition] = {}
        canonical_by_id: dict[str, str] = {}
        for definition in definitions:
            if not isinstance(definition, KLineDefinition):
                raise ValueError(
                    "K-line snapshots contain only KLineDefinition values"
                )
            identifier = definition.kline_id
            canonical = definition.to_json()
            prior = canonical_by_id.get(identifier)
            if prior is not None and prior != canonical:
                raise ValueError(
                    "K-line SHA-256 collision: equal identity has unequal "
                    "canonical content"
                )
            canonical_by_id[identifier] = canonical
            by_id[identifier] = definition
        if len(by_id) > bounds.max_definitions:
            raise ValueError("K-line definition bound exceeded")
        total_generator_refs = 0
        total_postings = 0
        for definition in by_id.values():
            atom_count = (
                len(definition.cues)
                + len(definition.preconditions)
                + len(definition.contradictions)
            )
            if atom_count > bounds.max_atoms_per_definition:
                raise ValueError("K-line atom bound exceeded")
            if (
                len(definition.recalled_generator_ids)
                > bounds.max_generator_ids_per_definition
            ):
                raise ValueError(
                    "K-line per-definition generator bound exceeded"
                )
            total_generator_refs += len(definition.recalled_generator_ids)
            total_postings += len(definition.cues)
        if total_generator_refs > bounds.max_total_generator_refs:
            raise ValueError("K-line total generator-reference bound exceeded")
        if total_postings > bounds.max_total_postings:
            raise ValueError("K-line posting bound exceeded")
        ordered = tuple(by_id[key] for key in sorted(by_id))
        snapshot_json = _canonical_json(
            [
                {
                    "definition": definition.to_dict(),
                    "kline_id": definition.kline_id,
                }
                for definition in ordered
            ]
        )
        return cls(
            definitions=ordered,
            root=_content_digest(snapshot_json),
        )

    def __post_init__(self) -> None:
        _validate_digest(self.root, field_name="K-line snapshot root")
        if any(
            not isinstance(definition, KLineDefinition)
            for definition in self.definitions
        ):
            raise ValueError(
                "snapshot definitions must be KLineDefinition values"
            )
        identifiers = tuple(
            definition.kline_id for definition in self.definitions
        )
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError(
                "snapshot definitions must be hash-sorted and duplicate-free"
            )
        expected_root = _content_digest(
            _canonical_json(
                [
                    {
                        "definition": definition.to_dict(),
                        "kline_id": definition.kline_id,
                    }
                    for definition in self.definitions
                ]
            )
        )
        if self.root != expected_root:
            raise ValueError(
                "K-line snapshot root does not match its definitions"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "definitions": [
                {
                    "definition": definition.to_dict(),
                    "kline_id": definition.kline_id,
                }
                for definition in self.definitions
            ],
            "root": self.root,
            "version": "kline-snapshot-v2",
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class KLineQuery:
    """Canonical set of currently observed abstract cues."""

    cues: tuple[CueAtom, ...] = ()

    def __post_init__(self) -> None:
        if type(self.cues) is not tuple:
            raise ValueError("K-line query cues must be a tuple")
        if self.cues != _canonical_atoms(self.cues, field_name="query cues"):
            raise ValueError(
                "K-line query cues must be sorted and duplicate-free"
            )

    @classmethod
    def create(cls, cues: Iterable[CueAtom] = ()) -> Self:
        return cls(_canonical_atoms(cues, field_name="query cues"))

    def to_dict(self) -> dict[str, object]:
        return {"cues": [cue.to_dict() for cue in self.cues]}


@dataclass(frozen=True, slots=True)
class StructuralCompatibility:
    """Result of a pure exact-stage compatibility check."""

    compatible: bool
    grounded: bool
    score: int
    reason: str
    expansions: int
    grounding_proof_digest: str | None

    def __post_init__(self) -> None:
        if type(self.compatible) is not bool or type(self.grounded) is not bool:
            raise ValueError("compatibility flags must be booleans")
        if type(self.score) is not int or not 0 <= self.score <= _SCORE_SCALE:
            raise ValueError("structural score must be between zero and one")
        _validate_abstract_symbol(
            self.reason,
            field_name="structural compatibility reason",
        )
        if (
            type(self.expansions) is not int
            or not 0 <= self.expansions <= _HARD_MAX_STRUCTURAL_EXPANSIONS
        ):
            raise ValueError(
                "structural expansions exceed the absolute hard bound"
            )
        if self.grounding_proof_digest is not None:
            _validate_digest(
                self.grounding_proof_digest,
                field_name="grounding proof digest",
            )
        if not self.grounded and self.grounding_proof_digest is not None:
            raise ValueError(
                "only a grounded structural result may carry a proof digest"
            )
        if not self.compatible and (self.grounded or self.score):
            raise ValueError(
                "an incompatible structure cannot be grounded or scored"
            )


StructuralMatcher = Callable[
    [KLineDefinition, KLineQuery, int],
    StructuralCompatibility,
]


class ActivationGrade(StrEnum):
    """Non-operative activation states exposed by retrieval."""

    RECALLED = "recalled"
    GROUNDED = "grounded"


@dataclass(frozen=True, slots=True)
class KLineMatch:
    """One ranked memory identity; deliberately contains no action payload."""

    kline_id: str
    prior: str
    recalled_generator_ids: tuple[str, ...]
    activation: ActivationGrade
    matched_cues: tuple[str, ...]
    matched_namespaces: tuple[str, ...]
    matched_features: tuple[str, ...]
    idf_score: int
    containment_score: int
    namespace_score: int
    query_coverage_score: int
    structural_score: int
    structural_reason: str
    structural_expansions: int
    grounding_proof_digest: str | None
    score: int

    def to_dict(self) -> dict[str, object]:
        return {
            "activation": self.activation.value,
            "containment_score": self.containment_score,
            "grounding_proof_digest": self.grounding_proof_digest,
            "idf_score": self.idf_score,
            "kline_id": self.kline_id,
            "matched_cues": list(self.matched_cues),
            "matched_features": list(self.matched_features),
            "matched_namespaces": list(self.matched_namespaces),
            "namespace_score": self.namespace_score,
            "prior": self.prior,
            "query_coverage_score": self.query_coverage_score,
            "recalled_generator_ids": list(self.recalled_generator_ids),
            "score": self.score,
            "structural_expansions": self.structural_expansions,
            "structural_reason": self.structural_reason,
            "structural_score": self.structural_score,
        }


@dataclass(frozen=True, slots=True)
class RetrievalDiagnostics:
    """Deterministic accounting for bounded retrieval and abstention."""

    query_atoms: int
    known_query_atoms: int
    postings_considered: int
    posting_visits: int
    coarse_candidates: int
    exact_evaluated: int
    missing_preconditions: int
    contradictions: int
    structural_rejections: int
    structural_budget_rejections: int
    structural_proof_rejections: int
    structural_expansions: int
    unknown_cues: tuple[str, ...]
    posting_visit_cap_reached: bool
    candidate_cap_reached: bool
    exact_cap_reached: bool
    result_cap_reached: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_cap_reached": self.candidate_cap_reached,
            "coarse_candidates": self.coarse_candidates,
            "contradictions": self.contradictions,
            "exact_cap_reached": self.exact_cap_reached,
            "exact_evaluated": self.exact_evaluated,
            "known_query_atoms": self.known_query_atoms,
            "missing_preconditions": self.missing_preconditions,
            "posting_visit_cap_reached": self.posting_visit_cap_reached,
            "posting_visits": self.posting_visits,
            "postings_considered": self.postings_considered,
            "query_atoms": self.query_atoms,
            "result_cap_reached": self.result_cap_reached,
            "structural_budget_rejections": (
                self.structural_budget_rejections
            ),
            "structural_expansions": self.structural_expansions,
            "structural_proof_rejections": self.structural_proof_rejections,
            "structural_rejections": self.structural_rejections,
            "unknown_cues": list(self.unknown_cues),
        }


@dataclass(frozen=True, slots=True)
class KLineRetrieval:
    """Stable response envelope for one query."""

    snapshot_root: str
    index_root: str
    matches: tuple[KLineMatch, ...]
    diagnostics: RetrievalDiagnostics

    @property
    def kline_ids(self) -> tuple[str, ...]:
        return tuple(match.kline_id for match in self.matches)

    def to_dict(self) -> dict[str, object]:
        return {
            "diagnostics": self.diagnostics.to_dict(),
            "index_root": self.index_root,
            "matches": [match.to_dict() for match in self.matches],
            "snapshot_root": self.snapshot_root,
            "version": "kline-retrieval-v2",
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class _CoarseCandidate:
    definition: KLineDefinition
    matched: tuple[CueAtom, ...]
    idf_score: int
    containment_score: int
    namespace_score: int
    query_coverage_score: int

    @property
    def score(self) -> int:
        return (
            self.idf_score
            + self.containment_score
            + self.namespace_score
            + self.query_coverage_score
        )


class KLineMemory:
    """Immutable-index façade for bounded K-line retrieval."""

    def __init__(
        self,
        snapshot: KLineSnapshot,
        *,
        registered_generator_ids: tuple[str, ...],
        bounds: KLineBounds = KLineBounds(),
    ) -> None:
        if len(snapshot.definitions) > bounds.max_definitions:
            raise ValueError("snapshot exceeds K-line definition bound")
        if type(registered_generator_ids) is not tuple:
            raise ValueError("registered generator IDs must be a tuple")
        if registered_generator_ids != tuple(
            sorted(set(registered_generator_ids))
        ):
            raise ValueError(
                "registered generator IDs must be sorted and duplicate-free"
            )
        if (
            len(registered_generator_ids)
            > bounds.max_registered_generator_ids
        ):
            raise ValueError("registered generator vocabulary bound exceeded")
        for generator_id in registered_generator_ids:
            _validate_abstract_symbol(
                generator_id,
                field_name="registered generator ID",
            )
        self.snapshot = snapshot
        self.bounds = bounds
        self._registered_generator_ids = registered_generator_ids
        self._definitions = {
            definition.kline_id: definition
            for definition in snapshot.definitions
        }
        registered_generator_set = frozenset(registered_generator_ids)
        mutable_postings: dict[CueAtom, list[str]] = defaultdict(list)
        vocabulary: set[CueAtom] = set()
        total_generator_refs = 0
        total_postings = 0
        for definition in snapshot.definitions:
            atom_count = (
                len(definition.cues)
                + len(definition.preconditions)
                + len(definition.contradictions)
            )
            if atom_count > bounds.max_atoms_per_definition:
                raise ValueError("snapshot definition exceeds K-line atom bound")
            if (
                len(definition.recalled_generator_ids)
                > bounds.max_generator_ids_per_definition
            ):
                raise ValueError(
                    "snapshot definition exceeds generator-reference bound"
                )
            total_generator_refs += len(definition.recalled_generator_ids)
            unknown_generators = (
                set(definition.recalled_generator_ids)
                - registered_generator_set
            )
            if unknown_generators:
                raise ValueError(
                    "K-line definition recalls unregistered generators: "
                    f"{sorted(unknown_generators)}"
                )
            vocabulary.update(definition.cues)
            vocabulary.update(definition.preconditions)
            vocabulary.update(definition.contradictions)
            for cue in definition.cues:
                mutable_postings[cue].append(definition.kline_id)
                total_postings += 1
        if total_generator_refs > bounds.max_total_generator_refs:
            raise ValueError(
                "snapshot exceeds total generator-reference bound"
            )
        if total_postings > bounds.max_total_postings:
            raise ValueError("snapshot exceeds K-line posting bound")
        self._vocabulary = frozenset(vocabulary)
        self._postings = {
            cue: tuple(sorted(identifiers))
            for cue, identifiers in mutable_postings.items()
        }
        self.index_root = _content_digest(
            _canonical_json(
                {
                    "bounds": bounds.to_dict(),
                    "index_schema": _INDEX_SCHEMA,
                    "registered_generator_ids": list(
                        registered_generator_ids
                    ),
                    "snapshot_root": snapshot.root,
                }
            )
        )

    @classmethod
    def create(
        cls,
        definitions: Iterable[KLineDefinition] = (),
        *,
        registered_generator_ids: Iterable[str],
        bounds: KLineBounds = KLineBounds(),
    ) -> Self:
        return cls(
            KLineSnapshot.create(definitions, bounds=bounds),
            registered_generator_ids=tuple(
                sorted(set(registered_generator_ids))
            ),
            bounds=bounds,
        )

    def posting(self, cue: CueAtom) -> tuple[str, ...]:
        """Return the exact immutable posting for inspection and auditing."""

        return self._postings.get(cue, ())

    @property
    def registered_generator_ids(self) -> tuple[str, ...]:
        """Return the canonical, immutable generator registry."""

        return self._registered_generator_ids

    def retrieve(
        self,
        query: KLineQuery,
        *,
        structural_matcher: StructuralMatcher | None = None,
    ) -> KLineRetrieval:
        """Recall compatible prior identities within deterministic hard caps."""

        if len(query.cues) > self.bounds.max_query_atoms:
            raise ValueError("K-line query atom bound exceeded")
        if not query.cues or not self._definitions:
            return self._empty_result(query)

        query_set = frozenset(query.cues)
        known = tuple(cue for cue in query.cues if cue in self._vocabulary)
        unknown = tuple(
            cue.key for cue in query.cues if cue not in self._vocabulary
        )
        if not known:
            return self._empty_result(query, unknown_cues=unknown)

        indexed = tuple(cue for cue in known if cue in self._postings)
        ordered_postings = tuple(
            sorted(
                (
                    (len(self._postings[cue]), cue, self._postings[cue])
                    for cue in indexed
                ),
                key=lambda item: (item[0], item[1]),
            )
        )
        candidate_ids: set[str] = set()
        posting_visits = 0
        postings_considered = len(ordered_postings)
        posting_visit_cap_reached = False
        posting_offset = 0
        while posting_visits < self.bounds.max_posting_visits:
            visited_at_offset = False
            for _frequency, _cue, posting in ordered_postings:
                if posting_offset >= len(posting):
                    continue
                if posting_visits >= self.bounds.max_posting_visits:
                    posting_visit_cap_reached = True
                    break
                identifier = posting[posting_offset]
                posting_visits += 1
                candidate_ids.add(identifier)
                visited_at_offset = True
            if not visited_at_offset:
                break
            posting_offset += 1
        if posting_visits >= self.bounds.max_posting_visits and any(
            posting_offset < len(posting)
            for _frequency, _cue, posting in ordered_postings
        ):
            posting_visit_cap_reached = True

        coarse = tuple(
            sorted(
                (
                    candidate
                    for identifier in sorted(candidate_ids)
                    if (
                        candidate := self._coarse_candidate(
                            self._definitions[identifier],
                            query_set,
                            known_query_count=len(indexed),
                        )
                    )
                    is not None
                ),
                key=lambda item: (
                    -item.score,
                    -len(item.matched),
                    item.definition.kline_id,
                ),
            )
        )
        missing_preconditions = 0
        contradictions = 0
        eligible_candidates: list[_CoarseCandidate] = []
        for candidate in coarse:
            definition = candidate.definition
            if any(
                atom not in query_set
                for atom in definition.preconditions
            ):
                missing_preconditions += 1
                continue
            if any(
                atom in query_set
                for atom in definition.contradictions
            ):
                contradictions += 1
                continue
            eligible_candidates.append(candidate)

        candidate_cap_reached = (
            len(eligible_candidates) > self.bounds.max_candidate_pool
        )
        pooled_candidates = eligible_candidates[
            : self.bounds.max_candidate_pool
        ]
        exact_cap_reached = (
            len(pooled_candidates) > self.bounds.max_exact_candidates
        )
        exact_candidates = pooled_candidates[
            : self.bounds.max_exact_candidates
        ]

        matches: list[KLineMatch] = []
        structural_rejections = 0
        structural_budget_rejections = 0
        structural_proof_rejections = 0
        structural_expansions = 0
        remaining_structural_expansions = (
            self.bounds.max_structural_expansions
        )
        exact_evaluated = 0
        for candidate in exact_candidates:
            exact_evaluated += 1
            definition = candidate.definition

            compatibility = self._builtin_compatibility(candidate)
            if structural_matcher is not None:
                compatibility = structural_matcher(
                    definition,
                    query,
                    remaining_structural_expansions,
                )
                if not isinstance(compatibility, StructuralCompatibility):
                    raise TypeError(
                        "structural matcher must return "
                        "StructuralCompatibility"
                    )
            if (
                compatibility.expansions
                > remaining_structural_expansions
            ):
                structural_budget_rejections += 1
                structural_rejections += 1
                remaining_structural_expansions = 0
                continue
            structural_expansions += compatibility.expansions
            remaining_structural_expansions -= compatibility.expansions
            if not compatibility.compatible:
                structural_rejections += 1
                continue
            if (
                compatibility.grounded
                and compatibility.grounding_proof_digest is None
            ):
                structural_proof_rejections += 1
                structural_rejections += 1
                continue

            matched_namespaces = tuple(
                sorted({atom.namespace.value for atom in candidate.matched})
            )
            matched_features = tuple(
                sorted(
                    {
                        f"{atom.namespace.value}:{atom.feature}"
                        for atom in candidate.matched
                    }
                )
            )
            score = (
                candidate.score * (_SCORE_SCALE + compatibility.score)
            ) // _SCORE_SCALE
            matches.append(
                KLineMatch(
                    kline_id=definition.kline_id,
                    prior=definition.prior,
                    recalled_generator_ids=(
                        definition.recalled_generator_ids
                    ),
                    activation=(
                        ActivationGrade.GROUNDED
                        if compatibility.grounded
                        else ActivationGrade.RECALLED
                    ),
                    matched_cues=tuple(atom.key for atom in candidate.matched),
                    matched_namespaces=matched_namespaces,
                    matched_features=matched_features,
                    idf_score=candidate.idf_score,
                    containment_score=candidate.containment_score,
                    namespace_score=candidate.namespace_score,
                    query_coverage_score=candidate.query_coverage_score,
                    structural_score=compatibility.score,
                    structural_reason=compatibility.reason,
                    structural_expansions=compatibility.expansions,
                    grounding_proof_digest=(
                        compatibility.grounding_proof_digest
                    ),
                    score=score,
                )
            )

        ranked = tuple(
            sorted(
                matches,
                key=lambda item: (
                    -item.score,
                    -len(item.matched_cues),
                    item.kline_id,
                ),
            )
        )
        result_cap_reached = len(ranked) > self.bounds.max_results
        results = ranked[: self.bounds.max_results]
        diagnostics = RetrievalDiagnostics(
            query_atoms=len(query.cues),
            known_query_atoms=len(known),
            postings_considered=postings_considered,
            posting_visits=posting_visits,
            coarse_candidates=len(coarse),
            exact_evaluated=exact_evaluated,
            missing_preconditions=missing_preconditions,
            contradictions=contradictions,
            structural_rejections=structural_rejections,
            structural_budget_rejections=structural_budget_rejections,
            structural_proof_rejections=structural_proof_rejections,
            structural_expansions=structural_expansions,
            unknown_cues=unknown,
            posting_visit_cap_reached=posting_visit_cap_reached,
            candidate_cap_reached=candidate_cap_reached,
            exact_cap_reached=exact_cap_reached,
            result_cap_reached=result_cap_reached,
        )
        return KLineRetrieval(
            snapshot_root=self.snapshot.root,
            index_root=self.index_root,
            matches=results,
            diagnostics=diagnostics,
        )

    def _coarse_candidate(
        self,
        definition: KLineDefinition,
        query: frozenset[CueAtom],
        *,
        known_query_count: int,
    ) -> _CoarseCandidate | None:
        matched = tuple(cue for cue in definition.cues if cue in query)
        if len(matched) < definition.minimum_cue_matches:
            return None
        matched_namespaces = {cue.namespace for cue in matched}
        if (
            len(matched_namespaces)
            < definition.minimum_namespace_matches
        ):
            return None
        containment_score = (
            _SCORE_SCALE * len(matched)
        ) // len(definition.cues)
        namespace_score = (
            _SCORE_SCALE * len(matched_namespaces)
        ) // len({cue.namespace for cue in definition.cues})
        query_coverage_score = (
            _SCORE_SCALE * len(matched)
        ) // max(1, known_query_count)
        definition_count = len(self._definitions)
        raw_idf_score = min(
            _SCORE_SCALE,
            sum(
                (
                    _SCORE_SCALE
                    * (
                        definition_count
                        - len(self._postings[cue])
                        + 1
                    )
                )
                // max(1, definition_count)
                for cue in matched
            )
            // len(matched),
        )
        # Rarity is useful for proposing a memory, but it may never outweigh
        # the combined exact containment, namespace, and query-coverage terms.
        idf_score = min(
            raw_idf_score,
            containment_score + namespace_score + query_coverage_score,
        )
        return _CoarseCandidate(
            definition=definition,
            matched=matched,
            idf_score=idf_score,
            containment_score=containment_score,
            namespace_score=namespace_score,
            query_coverage_score=query_coverage_score,
        )

    @staticmethod
    def _builtin_compatibility(
        candidate: _CoarseCandidate,
    ) -> StructuralCompatibility:
        definition = candidate.definition
        score = (
            _SCORE_SCALE * len(candidate.matched)
        ) // len(definition.cues)
        return StructuralCompatibility(
            compatible=True,
            grounded=False,
            score=score,
            reason="cue-recall-requires-structural-grounding",
            expansions=0,
            grounding_proof_digest=None,
        )

    def _empty_result(
        self,
        query: KLineQuery,
        *,
        unknown_cues: tuple[str, ...] | None = None,
    ) -> KLineRetrieval:
        unknown = (
            tuple(cue.key for cue in query.cues)
            if unknown_cues is None and query.cues
            else (unknown_cues or ())
        )
        return KLineRetrieval(
            snapshot_root=self.snapshot.root,
            index_root=self.index_root,
            matches=(),
            diagnostics=RetrievalDiagnostics(
                query_atoms=len(query.cues),
                known_query_atoms=(
                    sum(cue in self._vocabulary for cue in query.cues)
                ),
                postings_considered=0,
                posting_visits=0,
                coarse_candidates=0,
                exact_evaluated=0,
                missing_preconditions=0,
                contradictions=0,
                structural_rejections=0,
                structural_budget_rejections=0,
                structural_proof_rejections=0,
                structural_expansions=0,
                unknown_cues=unknown,
                posting_visit_cap_reached=False,
                candidate_cap_reached=False,
                exact_cap_reached=False,
                result_cap_reached=False,
            ),
        )
