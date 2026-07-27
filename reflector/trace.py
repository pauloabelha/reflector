"""Deterministic, serializable inference traces and policy replay."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .symbolic import (
    Atom,
    Decision,
    Event,
    ObjectState,
    Observation,
    Scene,
    Transition,
)

TRACE_FORMAT_VERSION = 3
AGENT_VERSION = "reflector-symbolic-v8"


@dataclass(frozen=True, slots=True)
class TraceStep:
    index: int
    observation: Observation
    decision: Decision
    scene: Scene
    incoming_transition: Transition | None
    new_concepts: tuple[str, ...] = ()
    new_hypotheses: tuple[str, ...] = ()
    new_abstractions: tuple[str, ...] = ()
    new_assessments: tuple[str, ...] = ()
    experiment: str | None = None
    plan_actions: tuple[int, ...] = ()
    planner_expansions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "observation": self.observation.to_dict(),
            "decision": self.decision.to_dict(),
            "scene": self.scene.to_dict(),
            "incoming_transition": (
                self.incoming_transition.to_dict()
                if self.incoming_transition is not None
                else None
            ),
            "new_concepts": list(self.new_concepts),
            "new_hypotheses": list(self.new_hypotheses),
            "new_abstractions": list(self.new_abstractions),
            "new_assessments": list(self.new_assessments),
            "experiment": self.experiment,
            "plan_actions": list(self.plan_actions),
            "planner_expansions": self.planner_expansions,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TraceStep":
        raw_observation = value["observation"]
        observation = Observation.create(
            state=raw_observation["state"],
            available_actions=raw_observation["available_actions"],
            frame=raw_observation["frame"],
            levels_completed=raw_observation["levels_completed"],
        )
        raw_decision = value["decision"]
        decision = Decision(
            action_id=raw_decision["action_id"],
            data=tuple(sorted(raw_decision["data"].items())),
            reason=raw_decision["reason"],
        )
        raw_scene = value["scene"]
        scene = Scene(
            index=raw_scene["index"],
            state=raw_scene["state"],
            levels_completed=raw_scene["levels_completed"],
            available_actions=tuple(raw_scene["available_actions"]),
            objects=tuple(
                ObjectState(
                    object_id=item["object_id"],
                    color=item["color"],
                    area=item["area"],
                    bbox=tuple(item["bbox"]),
                    centroid=tuple(item["centroid"]),
                    shape=tuple(
                        tuple(point) for point in item.get("shape", ())
                    ),
                )
                for item in raw_scene["objects"]
            ),
            facts=tuple(Atom.parse(atom) for atom in raw_scene["facts"]),
            frame_digest=raw_scene["frame_digest"],
        )
        raw_transition = value["incoming_transition"]
        transition = None
        if raw_transition is not None:
            result: list[Event] = []
            for raw_event in raw_transition["result"]:
                atom = Atom.parse(raw_event)
                subject = atom.arguments[0] if atom.arguments else "scene"
                result.append(Event(atom.predicate, subject, atom.arguments[1:]))
            transition = Transition(
                before_index=raw_transition["before_index"],
                after_index=raw_transition["after_index"],
                context=tuple(
                    Atom.parse(atom) for atom in raw_transition["context"]
                ),
                action_id=raw_transition["action_id"],
                action_data=tuple(sorted(raw_transition["action_data"].items())),
                result=tuple(result),
            )
        return cls(
            index=value["index"],
            observation=observation,
            decision=decision,
            scene=scene,
            incoming_transition=transition,
            new_concepts=tuple(value["new_concepts"]),
            new_hypotheses=tuple(value.get("new_hypotheses", ())),
            new_abstractions=tuple(value.get("new_abstractions", ())),
            new_assessments=tuple(value.get("new_assessments", ())),
            experiment=value.get("experiment"),
            plan_actions=tuple(value.get("plan_actions", ())),
            planner_expansions=value.get("planner_expansions", 0),
        )


@dataclass(slots=True)
class EpisodeTrace:
    """In-memory trace owned by the symbolic agent; persistence is optional."""

    format_version: int = TRACE_FORMAT_VERSION
    agent_version: str = AGENT_VERSION
    mind_config: dict[str, bool | int | float] = field(default_factory=dict)
    steps: list[TraceStep] = field(default_factory=list)
    terminal_observation: Observation | None = None
    terminal_scene: Scene | None = None
    terminal_transition: Transition | None = None

    def append(self, step: TraceStep) -> None:
        if step.index != len(self.steps):
            raise ValueError("trace steps must be contiguous")
        self.steps.append(step)

    def finish(
        self,
        observation: Observation,
        scene: Scene,
        transition: Transition | None,
    ) -> None:
        self.terminal_observation = observation
        self.terminal_scene = scene
        self.terminal_transition = transition

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "agent_version": self.agent_version,
            "mind_config": self.mind_config,
            "steps": [step.to_dict() for step in self.steps],
            "terminal": (
                {
                    "observation": self.terminal_observation.to_dict(),
                    "scene": self.terminal_scene.to_dict(),
                    "transition": (
                        self.terminal_transition.to_dict()
                        if self.terminal_transition is not None
                        else None
                    ),
                }
                if self.terminal_observation is not None
                and self.terminal_scene is not None
                else None
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EpisodeTrace":
        trace = cls(
            format_version=value["format_version"],
            agent_version=value["agent_version"],
            mind_config=dict(value.get("mind_config", {})),
        )
        for raw_step in value["steps"]:
            trace.append(TraceStep.from_dict(raw_step))
        terminal = value.get("terminal")
        if terminal is not None:
            synthetic = TraceStep.from_dict(
                {
                    "index": len(trace.steps),
                    "observation": terminal["observation"],
                    "decision": {"action_id": 0, "data": {}, "reason": "terminal"},
                    "scene": terminal["scene"],
                    "incoming_transition": terminal["transition"],
                    "new_concepts": [],
                    "new_hypotheses": [],
                    "new_abstractions": [],
                    "experiment": None,
                    "plan_actions": [],
                    "planner_expansions": 0,
                }
            )
            trace.finish(
                synthetic.observation,
                synthetic.scene,
                synthetic.incoming_transition,
            )
        return trace

    @classmethod
    def from_json(cls, value: str) -> "EpisodeTrace":
        raw = json.loads(value)
        if not isinstance(raw, dict):
            raise ValueError("trace root must be an object")
        return cls.from_dict(raw)

    def replay(
        self,
        policy_factory: Callable[[], Any] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Re-run policy decisions over recorded observations.

        The replay is counterfactual-safe: it never advances an environment and
        reports decision mismatches rather than mutating the original trace.
        """

        if policy_factory is None:
            from .mind import MindConfig
            from .policy import SymbolicPolicy

            config = (
                MindConfig.from_dict(self.mind_config)
                if self.mind_config
                else MindConfig()
            )
            policy: Any = SymbolicPolicy(config)
        else:
            policy = policy_factory()
        output: list[dict[str, Any]] = []
        for step in self.steps:
            actual = policy.choose_action(step.observation)
            output.append(
                {
                    "index": step.index,
                    "expected_action": step.decision.action_id,
                    "actual_action": actual.action_id,
                    "matches": actual == step.decision,
                }
            )
        return tuple(output)
