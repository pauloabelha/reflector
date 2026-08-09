"""Evidence-gated options over a broad fallback policy.

The fallback policy is authoritative until a workspace option earns a bounded
control lease from direct environmental evidence.  Semantic workers can raise
attention and nominate probes; they cannot write support or silently replace
the fallback.  The module is deliberately structural so it can wrap the frozen
Reflector policy without importing a game, an action vocabulary, or Qwen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping, Protocol


class BridgeError(ValueError):
    pass


def _hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("ascii")).hexdigest()


def _grid(value: Any) -> tuple[tuple[int, ...], ...]:
    rows = tuple(tuple(int(cell) for cell in row) for row in value)
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise BridgeError("frame must be a nonempty rectangular grid")
    return rows


def _rle(values: tuple[int, ...]) -> list[list[int]]:
    output: list[list[int]] = []
    for value in values:
        if output and output[-1][0] == value:
            output[-1][1] += 1
        else:
            output.append([value, 1])
    return output


def decode_frame(blobs: Mapping[str, Mapping[str, Any]], frame_ref: str) -> tuple[tuple[int, ...], ...]:
    """Exactly reconstruct a frame from a full checkpoint and sparse deltas."""
    chain: list[Mapping[str, Any]] = []
    cursor = frame_ref
    while True:
        blob = blobs.get(cursor)
        if blob is None:
            raise BridgeError("frame blob is unavailable")
        chain.append(blob)
        if blob["codec"] == "rle-v1":
            break
        if blob["codec"] != "delta-v1" or not isinstance(blob.get("parent"), str):
            raise BridgeError("unknown frame codec")
        cursor = blob["parent"]
    base = chain.pop()
    height, width = map(int, base["shape"])
    flat: list[int] = []
    for value, count in base["runs"]:
        flat.extend([int(value)] * int(count))
    if len(flat) != height * width:
        raise BridgeError("corrupt RLE frame")
    while chain:
        delta = chain.pop()
        if tuple(map(int, delta["shape"])) != (height, width):
            raise BridgeError("delta shape mismatch")
        for index, value in delta["changes"]:
            flat[int(index)] = int(value)
    return tuple(tuple(flat[row * width:(row + 1) * width]) for row in range(height))


class DecisionLike(Protocol):
    action_id: int

    def data_dict(self) -> Mapping[str, int]: ...


class BroadPolicy(Protocol):
    def choose_action(self, observation: Any) -> DecisionLike: ...

    def cognitive_event(self, observation: Any, decision: DecisionLike) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class OptionProposal:
    candidate_id: str
    schema_id: str
    action_id: int
    data: tuple[tuple[str, int], ...]
    mode: str
    potential_before: int
    predicted_after: int
    basis_ids: tuple[str, ...]
    proposer: str
    attention: int = 0

    @classmethod
    def create(
        cls,
        *,
        schema_id: str,
        action_id: int,
        mode: str,
        potential_before: int,
        predicted_after: int,
        basis_ids: tuple[str, ...],
        proposer: str,
        data: Mapping[str, int] | None = None,
        attention: int = 0,
    ) -> "OptionProposal":
        if mode not in {"probe", "control"}:
            raise BridgeError("option mode must be probe or control")
        if proposer not in {"r2", "qwen", "kernel"}:
            raise BridgeError("unknown cognitive worker")
        if not basis_ids:
            raise BridgeError("an option must cite observable workspace objects")
        payload = {
            "schema_id": schema_id,
            "action_id": int(action_id),
            "data": sorted((data or {}).items()),
            "predicted_delta": int(predicted_after) - int(potential_before),
        }
        return cls(
            candidate_id="option:" + _hash(payload)[:24],
            schema_id=str(schema_id),
            action_id=int(action_id),
            data=tuple(sorted((str(key), int(value)) for key, value in (data or {}).items())),
            mode=mode,
            potential_before=int(potential_before),
            predicted_after=int(predicted_after),
            basis_ids=tuple(sorted(set(map(str, basis_ids)))),
            proposer=proposer,
            attention=int(attention),
        )


@dataclass(frozen=True, slots=True)
class EnvironmentOutcome:
    candidate_id: str
    transition_id: str
    observed_before: int | None
    observed_after: int | None
    direct: bool
    actor: str = "environment"

    def __post_init__(self) -> None:
        if self.actor != "environment":
            raise BridgeError("only the environment may adjudicate an option")


@dataclass(slots=True)
class Lease:
    confirmations: int = 0
    refutations: int = 0
    unresolved: int = 0
    transition_ids: list[str] = field(default_factory=list)

    @property
    def control_eligible(self) -> bool:
        return self.confirmations >= 2 and self.refutations == 0


@dataclass(frozen=True, slots=True)
class HybridDecision:
    action_id: int
    data: tuple[tuple[str, int], ...]
    mode: str
    fallback_action_id: int
    fallback_data: tuple[tuple[str, int], ...]
    candidate_id: str | None
    reason: str


class SharedBroadPolicy:
    """Wrap a broad policy with conservative, replayable option arbitration."""

    def __init__(
        self,
        baseline: BroadPolicy,
        *,
        stagnation_threshold: int = 8,
        max_option_probes: int = 8,
    ) -> None:
        if stagnation_threshold < 0 or max_option_probes < 0:
            raise BridgeError("budgets must be nonnegative")
        self.baseline = baseline
        self.stagnation_threshold = int(stagnation_threshold)
        self.max_option_probes = int(max_option_probes)
        self.probes_used = 0
        self.leases: dict[str, Lease] = {}
        self.proposals: dict[str, OptionProposal] = {}
        self.probe_counts: dict[str, int] = {}
        self.events: list[dict[str, Any]] = []
        self.frame_blobs: dict[str, dict[str, Any]] = {}
        self._last_frame_ref: str | None = None
        self._frames_since_checkpoint = 0

    def _store_frame(self, value: Any) -> str:
        frame = _grid(value)
        frame_ref = "frame:" + _hash(frame)
        if frame_ref in self.frame_blobs:
            self._last_frame_ref = frame_ref
            return frame_ref
        height, width = len(frame), len(frame[0]);flat = tuple(cell for row in frame for cell in row)
        parent = self._last_frame_ref
        checkpoint = parent is None or self._frames_since_checkpoint >= 31
        if not checkpoint:
            previous = decode_frame(self.frame_blobs, parent)
            if (len(previous), len(previous[0])) != (height, width):
                checkpoint = True
        if checkpoint:
            blob = {"codec": "rle-v1", "shape": [height, width], "runs": _rle(flat)}
            self._frames_since_checkpoint = 0
        else:
            old = tuple(cell for row in previous for cell in row)
            changes = [[index, value] for index, (before, value) in enumerate(zip(old, flat)) if before != value]
            full = {"codec": "rle-v1", "shape": [height, width], "runs": _rle(flat)}
            delta = {"codec": "delta-v1", "shape": [height, width], "parent": parent, "changes": changes}
            if len(json.dumps(delta, separators=(",", ":"))) < len(json.dumps(full, separators=(",", ":"))):
                blob = delta;self._frames_since_checkpoint += 1
            else:
                blob = full;self._frames_since_checkpoint = 0
        self.frame_blobs[frame_ref] = blob;self._last_frame_ref = frame_ref
        return frame_ref

    @staticmethod
    def _decision_data(decision: DecisionLike) -> tuple[tuple[str, int], ...]:
        raw = decision.data_dict()
        return tuple(sorted((str(key), int(value)) for key, value in raw.items()))

    @staticmethod
    def _stagnation(event: Mapping[str, Any]) -> int:
        state = event.get("operative_state", {})
        return int(state.get("consecutive_without_progress", 0)) if isinstance(state, Mapping) else 0

    def choose_action(self, observation: Any, proposal: OptionProposal | None = None) -> HybridDecision:
        serialize = getattr(observation, "to_dict", None)
        if callable(serialize):
            raw_observation = serialize()
            if not isinstance(raw_observation, Mapping):
                raise BridgeError("serialized observation must be a mapping")
            payload = dict(raw_observation)
            if "frame" in payload:
                payload["frame_ref"] = self._store_frame(payload.pop("frame"))
            self.events.append({
                "kind": "world_observation",
                "creator": "environment",
                "payload": payload,
            })
        fallback = self.baseline.choose_action(observation)
        fallback_data = self._decision_data(fallback)
        cognitive = dict(self.baseline.cognitive_event(observation, fallback))
        self.events.append({"kind": "broad_cognitive_event", "payload": cognitive})
        if proposal is None:
            return HybridDecision(fallback.action_id, fallback_data, "fallback", fallback.action_id, fallback_data, None, "no-live-option")

        self.proposals[proposal.candidate_id] = proposal
        self.leases.setdefault(proposal.candidate_id, Lease())
        self.events.append({
            "kind": "option_proposed",
            "creator": proposal.proposer,
            "object_id": proposal.candidate_id,
            "support": 0,
            "attention": proposal.attention,
            "dependencies": list(proposal.basis_ids),
        })
        improving = proposal.predicted_after < proposal.potential_before
        lease = self.leases[proposal.candidate_id]
        if proposal.mode == "control" and improving and lease.control_eligible:
            mode, reason = "control", "environment-confirmed-option"
        elif (
            proposal.mode == "probe"
            and improving
            and self.probes_used < self.max_option_probes
            and self._stagnation(cognitive) >= self.stagnation_threshold
        ):
            self.probes_used += 1
            mode, reason = "probe", "stagnation-triggered-falsification"
        else:
            return HybridDecision(fallback.action_id, fallback_data, "fallback", fallback.action_id, fallback_data, proposal.candidate_id, "option-not-licensed")
        chosen = HybridDecision(proposal.action_id, proposal.data, mode, fallback.action_id, fallback_data, proposal.candidate_id, reason)
        self.events.append({
            "kind": "hybrid_decision",
            "mode": mode,
            "candidate_id": proposal.candidate_id,
            "same_state_fallback": {"action_id": fallback.action_id, "data": dict(fallback_data)},
            "chosen": {"action_id": proposal.action_id, "data": dict(proposal.data)},
        })
        return chosen

    def choose_from_frontier(
        self,
        observation: Any,
        proposals: tuple[OptionProposal, ...],
    ) -> HybridDecision:
        """Select one option without letting salience impersonate support.

        Confirmed controls are ranked first.  Before confirmation, examination
        rotates toward the least-tested viable option and uses attention only as
        a tie-breaker.  This prevents one salient but unresolved family from
        monopolizing the bounded probe budget.
        """
        unique = {row.candidate_id: row for row in proposals}
        for row in unique.values():
            self.proposals[row.candidate_id] = row
            self.leases.setdefault(row.candidate_id, Lease())
        controls = [
            row for row in unique.values()
            if row.mode == "control"
            and row.predicted_after < row.potential_before
            and self.leases[row.candidate_id].control_eligible
        ]
        if controls:
            selected = min(controls, key=lambda row: (-row.attention, row.candidate_id))
        else:
            probes = [
                row for row in unique.values()
                if row.mode == "probe"
                and row.predicted_after < row.potential_before
                and self.leases[row.candidate_id].refutations == 0
            ]
            selected = min(
                probes,
                key=lambda row: (
                    self.probe_counts.get(row.candidate_id, 0),
                    -row.attention,
                    row.candidate_id,
                ),
            ) if probes else None
        decision = self.choose_action(observation, selected)
        if selected is not None and decision.mode == "probe":
            self.probe_counts[selected.candidate_id] = self.probe_counts.get(selected.candidate_id, 0) + 1
        return decision

    def adjudicate(self, outcome: EnvironmentOutcome) -> str:
        proposal = self.proposals.get(outcome.candidate_id)
        if proposal is None:
            raise BridgeError("outcome targets an unknown option")
        lease = self.leases[outcome.candidate_id]
        if not outcome.direct or outcome.observed_before is None or outcome.observed_after is None:
            lease.unresolved += 1
            verdict = "unresolved"
        else:
            observed_delta = outcome.observed_after - outcome.observed_before
            predicted_delta = proposal.predicted_after - proposal.potential_before
            if observed_delta == predicted_delta:
                lease.confirmations += 1
                verdict = "supports"
            else:
                lease.refutations += 1
                verdict = "refutes"
        lease.transition_ids.append(outcome.transition_id)
        self.events.append({
            "kind": "environment_evidence",
            "creator": "environment",
            "candidate_id": outcome.candidate_id,
            "transition_id": outcome.transition_id,
            "verdict": verdict,
            "observed_before": outcome.observed_before,
            "observed_after": outcome.observed_after,
        })
        return verdict

    def workspace_document(self) -> dict[str, Any]:
        return {
            "protocol": "shared-broad-policy-v0",
            "authority": "environment-evidence-only",
            "probe_budget": {"used": self.probes_used, "limit": self.max_option_probes},
            "probe_counts": dict(sorted(self.probe_counts.items())),
            "frame_blobs": dict(sorted(self.frame_blobs.items())),
            "leases": {
                key: {
                    "confirmations": value.confirmations,
                    "refutations": value.refutations,
                    "unresolved": value.unresolved,
                    "control_eligible": value.control_eligible,
                    "transition_ids": list(value.transition_ids),
                }
                for key, value in sorted(self.leases.items())
            },
            "events": list(self.events),
        }


__all__ = [
    "BridgeError",
    "EnvironmentOutcome",
    "HybridDecision",
    "OptionProposal",
    "SharedBroadPolicy",
    "decode_frame",
]
