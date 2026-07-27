"""Typed, serializable symbolic language used by the deployed agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence


@dataclass(frozen=True, slots=True)
class Observation:
    """Serializable ARC observation accepted by every Reflector surface."""

    state: str
    available_actions: tuple[int, ...]
    frame: tuple[tuple[int, ...], ...] = ()
    levels_completed: int = 0

    @classmethod
    def create(
        cls,
        *,
        state: str,
        available_actions: Iterable[int],
        frame: Sequence[Sequence[int]] | None = None,
        levels_completed: int = 0,
    ) -> "Observation":
        return cls(
            state=state,
            available_actions=tuple(sorted(set(available_actions))),
            frame=tuple(tuple(int(cell) for cell in row) for row in (frame or ())),
            levels_completed=levels_completed,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "available_actions": list(self.available_actions),
            "frame": [list(row) for row in self.frame],
            "levels_completed": self.levels_completed,
        }


@dataclass(frozen=True, slots=True)
class Decision:
    """A legal ARC action plus optional data and a symbolic explanation."""

    action_id: int
    data: tuple[tuple[str, int], ...] = ()
    reason: str = ""

    def data_dict(self) -> dict[str, int]:
        return dict(self.data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "data": self.data_dict(),
            "reason": self.reason,
        }


@dataclass(frozen=True, order=True, slots=True)
class Atom:
    """A predicate in Reflector's constrained symbolic DSL."""

    predicate: str
    arguments: tuple[str, ...] = ()

    def text(self) -> str:
        return (
            self.predicate
            if not self.arguments
            else f"{self.predicate}({','.join(self.arguments)})"
        )

    @classmethod
    def parse(cls, value: str) -> "Atom":
        if "(" not in value:
            return cls(value)
        predicate, raw = value[:-1].split("(", 1)
        return cls(predicate, tuple(raw.split(",")) if raw else ())


@dataclass(frozen=True, slots=True)
class ObjectState:
    """A connected visual component with an episode-persistent identity."""

    object_id: str
    color: int
    area: int
    bbox: tuple[int, int, int, int]
    centroid: tuple[int, int]
    shape: tuple[tuple[int, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, order=True, slots=True)
class Event:
    """A symbolic change between consecutive scenes."""

    kind: str
    subject: str = "scene"
    arguments: tuple[str, ...] = ()

    def atom(self) -> Atom:
        return Atom(self.kind, (self.subject, *self.arguments))

    def text(self) -> str:
        return self.atom().text()


@dataclass(frozen=True, slots=True)
class Scene:
    """Perceived scene and its derived facts."""

    index: int
    state: str
    levels_completed: int
    available_actions: tuple[int, ...]
    objects: tuple[ObjectState, ...]
    facts: tuple[Atom, ...]
    frame_digest: str

    def context(self) -> tuple[Atom, ...]:
        """Return a compact context suitable for cross-state schema reuse."""

        reusable = {
            atom
            for atom in self.facts
            if atom.predicate
            in {
                "state",
                "object_count",
                "color_present",
                "color",
                "area",
                "centroid",
                "shape_size",
                "action_available",
                "left_of",
                "above",
                "aligned_x",
                "aligned_y",
                "touching",
            }
        }
        return tuple(sorted(reusable))

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "state": self.state,
            "levels_completed": self.levels_completed,
            "available_actions": list(self.available_actions),
            "objects": [item.to_dict() for item in self.objects],
            "facts": [atom.text() for atom in self.facts],
            "frame_digest": self.frame_digest,
        }


@dataclass(frozen=True, slots=True)
class Transition:
    """Observed context + action -> result evidence."""

    before_index: int
    after_index: int
    context: tuple[Atom, ...]
    action_id: int
    action_data: tuple[tuple[str, int], ...]
    result: tuple[Event, ...]

    def result_signature(self) -> tuple[str, ...]:
        return tuple(event.text() for event in self.result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_index": self.before_index,
            "after_index": self.after_index,
            "context": [atom.text() for atom in self.context],
            "action_id": self.action_id,
            "action_data": dict(self.action_data),
            "result": [event.text() for event in self.result],
        }


def canonical_atoms(atoms: Iterable[Atom]) -> tuple[Atom, ...]:
    return tuple(sorted(set(atoms)))
