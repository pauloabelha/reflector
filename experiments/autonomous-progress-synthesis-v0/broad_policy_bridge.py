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


class OnlineOptionSource(Protocol):
    def option_proposals(
        self, *, control_candidate_ids: frozenset[str] = frozenset()
    ) -> tuple["OptionProposal", ...]: ...

    def observe_option_transition(
        self,
        *,
        opaque_action: int,
        after: Any,
        transition_id: str,
        executed_candidate_id: str | None = None,
        direct: bool = True,
    ) -> "EnvironmentOutcome | None": ...


@dataclass(frozen=True, slots=True)
class OptionProposal:
    candidate_id: str
    schema_id: str
    lineage_id: str
    effect_variable: str
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
        lineage_id: str = "",
        effect_variable: str = "",
    ) -> "OptionProposal":
        if mode not in {"probe", "control"}:
            raise BridgeError("option mode must be probe or control")
        if proposer not in {"r2", "qwen", "kernel"}:
            raise BridgeError("unknown cognitive worker")
        if not basis_ids:
            raise BridgeError("an option must cite observable workspace objects")
        payload = {
            "schema_id": schema_id,
            "lineage_id": str(lineage_id),
            "effect_variable": str(effect_variable),
            "action_id": int(action_id),
            "data": sorted((data or {}).items()),
            "predicted_delta": int(predicted_after) - int(potential_before),
        }
        return cls(
            candidate_id="option:" + _hash(payload)[:24],
            schema_id=str(schema_id),
            lineage_id=str(lineage_id),
            effect_variable=str(effect_variable),
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
        max_divergent_probes: int | None = None,
    ) -> None:
        if stagnation_threshold < 0 or max_option_probes < 0:
            raise BridgeError("budgets must be nonnegative")
        self.baseline = baseline
        self.stagnation_threshold = int(stagnation_threshold)
        self.max_option_probes = int(max_option_probes)
        self.max_divergent_probes = int(
            max_option_probes if max_divergent_probes is None else max_divergent_probes
        )
        if self.max_divergent_probes < 0:
            raise BridgeError("budgets must be nonnegative")
        self.probes_used = 0
        self.divergent_probes_used = 0
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

    def _finalize(self, observation: Any, decision: HybridDecision) -> HybridDecision:
        commit = getattr(self.baseline, "commit_decision", None)
        if callable(commit):commit(observation, decision)
        return decision

    def _begin_choice(
        self, observation: Any, *, allow_committed_fallback: bool
    ) -> tuple[DecisionLike, tuple[tuple[str, int], ...], Mapping[str, Any], bool]:
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
        direct = getattr(self.baseline, "choose_action_committed", None)
        precommitted = allow_committed_fallback and callable(direct)
        fallback = direct(observation) if precommitted else self.baseline.choose_action(observation)
        fallback_data = self._decision_data(fallback)
        cognitive = dict(self.baseline.cognitive_event(observation, fallback))
        self.events.append({"kind": "broad_cognitive_event", "payload": cognitive})
        return fallback, fallback_data, cognitive, precommitted

    def _finish_choice(
        self,
        observation: Any,
        fallback: DecisionLike,
        fallback_data: tuple[tuple[str, int], ...],
        cognitive: Mapping[str, Any],
        proposal: OptionProposal | None,
        *,
        precommitted: bool = False,
    ) -> HybridDecision:
        if proposal is None:
            decision=HybridDecision(fallback.action_id, fallback_data, "fallback", fallback.action_id, fallback_data, None, "no-live-option")
            return decision if precommitted else self._finalize(observation,decision)

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
        matches_fallback = (
            proposal.action_id == fallback.action_id and proposal.data == fallback_data
        )
        if proposal.mode == "control" and improving and lease.control_eligible:
            mode, reason = "control", "environment-confirmed-option"
        elif proposal.mode == "probe" and improving and matches_fallback:
            # This is a real prospective test: the prediction existed before
            # the transition, but R2 independently selected the same action.
            # It changes no behavior and spends no divergent-probe budget.
            mode, reason = "passive_probe", "baseline-selected-prospective-test"
        elif (
            proposal.mode == "probe"
            and improving
            and self.probes_used < self.max_option_probes
            and self.divergent_probes_used < self.max_divergent_probes
            and self._stagnation(cognitive) >= self.stagnation_threshold
        ):
            self.probes_used += 1
            self.divergent_probes_used += 1
            mode, reason = "probe", "stagnation-triggered-falsification"
        else:
            return self._finalize(observation,HybridDecision(fallback.action_id, fallback_data, "fallback", fallback.action_id, fallback_data, proposal.candidate_id, "option-not-licensed"))
        chosen = HybridDecision(proposal.action_id, proposal.data, mode, fallback.action_id, fallback_data, proposal.candidate_id, reason)
        self.events.append({
            "kind": "hybrid_decision",
            "mode": mode,
            "candidate_id": proposal.candidate_id,
            "same_state_fallback": {"action_id": fallback.action_id, "data": dict(fallback_data)},
            "chosen": {"action_id": proposal.action_id, "data": dict(proposal.data)},
        })
        return self._finalize(observation,chosen)

    def choose_action(self, observation: Any, proposal: OptionProposal | None = None) -> HybridDecision:
        fallback, fallback_data, cognitive, precommitted = self._begin_choice(
            observation, allow_committed_fallback=proposal is None
        )
        return self._finish_choice(
            observation,
            fallback,
            fallback_data,
            cognitive,
            proposal,
            precommitted=precommitted,
        )

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
            return self.choose_action(observation, selected)

        probes = [
                row for row in unique.values()
                if row.mode == "probe"
                and row.predicted_after < row.potential_before
                and self.leases[row.candidate_id].refutations == 0
        ]
        if not probes:
            return self.choose_action(observation, None)

        # Preview R2 exactly once, then prefer a prediction for the action R2
        # already chose.  Such evidence is free of behavioral intervention.
        fallback, fallback_data, cognitive, _ = self._begin_choice(
            observation, allow_committed_fallback=False
        )
        matching = [
            row for row in probes
            if row.action_id == fallback.action_id and row.data == fallback_data
        ]
        pool = matching or (
            probes
            if self.probes_used < self.max_option_probes
            and self.divergent_probes_used < self.max_divergent_probes
            else []
        )
        selected = min(
            pool,
            key=lambda row: (
                self.probe_counts.get(row.candidate_id, 0),
                -row.attention,
                row.candidate_id,
            ),
        ) if pool else None
        decision = self._finish_choice(
            observation, fallback, fallback_data, cognitive, selected
        )
        if selected is not None and decision.mode in {"probe", "passive_probe"}:
            self.probe_counts[selected.candidate_id] = self.probe_counts.get(selected.candidate_id, 0) + 1
        return decision

    def choose_from_inducer(
        self,
        observation: Any,
        inducer: OnlineOptionSource,
    ) -> HybridDecision:
        """Read an online option frontier using this bridge's evidence leases."""

        controls = frozenset(
            candidate_id
            for candidate_id, lease in self.leases.items()
            if lease.control_eligible
        )
        return self.choose_from_frontier(
            observation,
            inducer.option_proposals(control_candidate_ids=controls),
        )

    def observe_inducer_transition(
        self,
        inducer: OnlineOptionSource,
        decision: HybridDecision,
        *,
        after: Any,
        transition_id: str,
        direct: bool = True,
    ) -> str | None:
        """Update the inducer and, when addressed, this bridge's lease."""

        outcome = inducer.observe_option_transition(
            opaque_action=decision.action_id,
            after=after,
            transition_id=transition_id,
            executed_candidate_id=(decision.candidate_id if decision.mode in {"probe","passive_probe","control"} else None),
            direct=direct,
        )
        return None if outcome is None else self.adjudicate(outcome)

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
            "divergent_probe_budget": {
                "used": self.divergent_probes_used,
                "limit": self.max_divergent_probes,
            },
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

    def working_context(self, *, max_events: int = 32, max_historical_frames: int = 2) -> dict[str, Any]:
        """Return a bounded, explicitly lossy attention cut for Qwen.

        The cut is a cache over :meth:`workspace_document`, never authority.
        Stable frame references make every omitted observation addressable.
        """
        if max_events < 1 or max_historical_frames < 0:
            raise BridgeError("working-context bounds are invalid")
        world = [event for event in self.events if event.get("kind") == "world_observation"]
        refs = [event["payload"].get("frame_ref") for event in world]
        refs = [value for value in refs if isinstance(value, str)]
        current_ref = refs[-1] if refs else None
        historical = []
        for value in reversed(refs[:-1]):
            if value not in historical:
                historical.append(value)
            if len(historical) >= max_historical_frames:
                break
        active = []
        for candidate_id, proposal in sorted(self.proposals.items()):
            lease = self.leases[candidate_id]
            active.append({
                "candidate_id": candidate_id,
                "schema_id": proposal.schema_id,
                "lineage_id": proposal.lineage_id,
                "effect_variable": proposal.effect_variable,
                "proposer": proposal.proposer,
                "attention": proposal.attention,
                "empirical": {
                    "confirmations": lease.confirmations,
                    "refutations": lease.refutations,
                    "unresolved": lease.unresolved,
                    "control_eligible": lease.control_eligible,
                },
                "basis_ids": list(proposal.basis_ids),
            })
        start = max(0, len(self.events) - max_events)
        return {
            "protocol": "shared-broad-policy-working-context-v0",
            "authoritative_workspace_event_count": len(self.events),
            "delta_cursor_start": start,
            "omitted_event_count": start,
            "omission_fidelity": "small-lossy-dormant-history; exact objects remain externally addressable",
            "current_frame_ref": current_ref,
            "current_frame": [list(row) for row in decode_frame(self.frame_blobs, current_ref)] if current_ref else None,
            "historical_frame_refs": historical,
            "active_options": active,
            "recent_events": self.events[start:],
        }


__all__ = [
    "BridgeError",
    "EnvironmentOutcome",
    "HybridDecision",
    "OptionProposal",
    "OnlineOptionSource",
    "SharedBroadPolicy",
    "decode_frame",
]
