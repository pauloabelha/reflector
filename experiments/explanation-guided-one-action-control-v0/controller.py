"""Explanation-guided, exactly-one-action policy adapter."""

from __future__ import annotations

from dataclasses import asdict
import json
import sys
from typing import Any, Mapping, Sequence


class FastPathAuthority:
    """Grant bounded execution authority to an empirically supported policy.

    The authority is deliberately indifferent to game, verb, action identity,
    and the representation of the preferred order.  It consumes only the
    generic claims emitted by R2 settlement: the expected transition was
    confirmed, protected invariants held, and the successor was preferred.
    """

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        cfg = dict(config or {})
        self.enabled = bool(cfg.get("enabled", True))
        self.minimum_confirmations = max(1, int(cfg.get("minimum_confirmations", 2)))
        self.confidence_threshold = float(cfg.get("confidence_threshold", 0.8))
        self.horizon = max(1, int(cfg.get("max_actions", 4)))
        self.support: dict[str, int] = {}
        self.license: dict[str, Any] | None = None
        self.last_revocation: str | None = None

    @staticmethod
    def _signature(explanation: Mapping[str, Any]) -> str:
        goal = explanation.get("goal", {})
        ports = explanation.get("ports", {})
        roles = ports.get("situated_role_descriptors", {})
        applicability = {
            str(role): {
                "area": descriptor.get("area"),
            }
            for role, descriptor in sorted(roles.items())
            if isinstance(descriptor, Mapping)
        }
        # The policy signature intentionally excludes action ID and situated
        # binding IDs and raw palette values.  A state-conditioned policy may
        # select different legal actions while retaining the same grounded
        # objective and structural applicability conditions.
        return json.dumps({
            "schema": explanation.get("schema_id"),
            "measure": goal.get("measure"),
            "direction": goal.get("direction"),
            "terminal_class": goal.get("terminal_class"),
            "applicability": applicability,
        }, sort_keys=True, separators=(",", ":"))

    @property
    def active(self) -> bool:
        return self.license is not None and int(self.license.get("remaining", 0)) > 0

    def revoke(self, reason: str) -> None:
        self.license = None
        self.last_revocation = str(reason)

    def consider(
        self,
        explanation: Mapping[str, Any] | None,
        settlement: Mapping[str, Any] | None,
    ) -> None:
        if not self.enabled or not explanation or not settlement:
            self.revoke("missing-grounded-policy-or-settlement")
            return
        preferred = settlement.get("preferred_order", {})
        invariants = settlement.get("protected_invariants", {})
        evaluation = explanation.get("epistemic_evaluation", {})
        confidence = float(evaluation.get("mechanism_confidence") or 0.0)
        confirmed = settlement.get("adjudication") == "confirmed"
        valid = (
            confirmed
            and preferred.get("advanced") is True
            and invariants.get("hold") is True
            and confidence >= self.confidence_threshold
            and explanation.get("control_status") == "PROGRESS_ELIGIBLE"
        )
        signature = self._signature(explanation)
        if not valid:
            self.support[signature] = 0
            reason = (
                str(settlement.get("adjudication")) if not confirmed else
                "successor-not-preferred" if preferred.get("advanced") is not True else
                "protected-invariant-violated" if invariants.get("hold") is not True else
                "mechanism-confidence-below-threshold" if confidence < self.confidence_threshold else
                "policy-not-progress-eligible"
            )
            self.revoke(reason)
            return
        confirmations = self.support.get(signature, 0) + 1
        self.support[signature] = confirmations
        if self.active and self.license and self.license.get("signature") == signature:
            self.license["remaining"] = int(self.license["remaining"]) - 1
            self.license["confirmations"] = confirmations
            self.license["confidence"] = confidence
            if int(self.license["remaining"]) <= 0:
                self.revoke("bounded-horizon-exhausted")
            return
        if confirmations >= self.minimum_confirmations:
            self.license = {
                "protocol": "bounded-preferred-policy-v1",
                "signature": signature,
                "remaining": self.horizon,
                "max_actions": self.horizon,
                "max_failures": 0,
                "confirmations": confirmations,
                "confidence": confidence,
                "status": "AUTHORIZED",
            }
            self.last_revocation = None

    def document(self) -> dict[str, Any]:
        if self.active and self.license:
            return dict(self.license)
        return {
            "protocol": "bounded-preferred-policy-v1",
            "status": "INACTIVE",
            "last_revocation": self.last_revocation,
        }


def _components(grid: Any) -> list[tuple[int, int, int, int, int, int]]:
    """Color components as (color, area, min_y, min_x, cy2, cx2)."""
    rows = [list(row) for row in grid]
    if not rows:
        return []
    counts: dict[int, int] = {}
    for row in rows:
        for value in row: counts[int(value)] = counts.get(int(value), 0) + 1
    background = max(counts, key=counts.get)
    seen: set[tuple[int, int]] = set(); output = []
    for y, row in enumerate(rows):
        for x, value in enumerate(row):
            if int(value) == background or (y, x) in seen: continue
            stack = [(y, x)]; seen.add((y, x)); cells = []
            while stack:
                cy, cx = stack.pop(); cells.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < len(rows) and 0 <= nx < len(rows[ny]) and (ny, nx) not in seen and int(rows[ny][nx]) == int(value):
                        seen.add((ny, nx)); stack.append((ny, nx))
            output.append((int(value), len(cells), min(p[0] for p in cells), min(p[1] for p in cells), sum(p[0] for p in cells) * 2 // len(cells), sum(p[1] for p in cells) * 2 // len(cells)))
    return sorted(output, key=lambda item: (item[2], item[3], item[0]))


def action_trace(action: int, before: Any, after: Any) -> str:
    if before == after:
        return f"Action {action} → no visible change."
    before_items, after_items, messages = _components(before), _components(after), []
    used: set[int] = set()
    for index, item in enumerate(before_items):
        candidates = [(abs(item[4] - other[4]) + abs(item[5] - other[5]), pos, other) for pos, other in enumerate(after_items) if pos not in used and other[:2] == item[:2]]
        if not candidates: continue
        _distance, pos, other = min(candidates); used.add(pos)
        dy, dx = (other[4] - item[4]) // 2, (other[5] - item[5]) // 2
        parts = []
        if dy: parts.append(f"{'down' if dy > 0 else 'up'} {abs(dy)}")
        if dx: parts.append(f"{'right' if dx > 0 else 'left'} {abs(dx)}")
        if parts: messages.append(f"f{index:02d} moved {' and '.join(parts)}")
    return f"Action {action} → " + ("; ".join(messages) if messages else "visible configuration changed; object correspondence unresolved.")


def controller_class(
    live_controller: Any,
    runtime: Any | None = None,
    fast_path_config: Mapping[str, Any] | None = None,
    action_commands: Any | None = None,
) -> type:
    base = live_controller.ProspectiveWorkspaceController

    class OneActionController(base):
        """Choose one intervention for progress, information, or both."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.no_change_attempts: dict[tuple[str, int], int] = {}
            self.current_observation_digest = ""
            self.last_contract: dict[str, Any] | None = None
            # Set only after the selected native R2.1 prediction is durably
            # materialized by the integration layer.  The next environment
            # observation consumes it exactly once.
            self.pending_r2_prediction_id: str | None = None
            self.settlements: list[dict[str, Any]] = []
            self.fast_path = FastPathAuthority(fast_path_config)
            self.last_command: Any | None = None
            self.command_uses: dict[str, int] = {}
            self.command_no_change: dict[tuple[str, str], int] = {}

        @property
        def fast_path_active(self) -> bool:
            return self.fast_path.active

        def plan(self, legal_actions: Sequence[int], *, observation_digest: str, basis_revision: int) -> tuple[Any, Any]:
            self.current_observation_digest = str(observation_digest)
            decision, plan = super().plan(
                legal_actions,
                observation_digest=observation_digest,
                basis_revision=basis_revision,
            )
            legal = tuple(sorted(set(int(item) for item in legal_actions)))
            schema_observer = getattr(runtime, "schema_observer", None) if runtime is not None else None
            commands = (
                tuple(action_commands.commands_for_frame(legal, schema_observer))
                if action_commands is not None and schema_observer is not None else ()
            )
            by_action = {
                action: tuple(item for item in commands if int(item.action_id) == action)
                for action in legal
            }
            default_commands = by_action.get(int(decision.action_id), ())
            if not default_commands and commands:
                replacement_command = min(
                    commands,
                    key=lambda item: (
                        self.command_no_change.get((str(observation_digest), item.command_id), 0),
                        self.command_uses.get(item.command_id, 0), item.command_id,
                    ),
                )
                decision = type(decision)(
                    action_id=int(replacement_command.action_id),
                    fallback_action_id=int(decision.fallback_action_id),
                    reason="parameterized-action-has-grounded-payload",
                    template_hash=None, residual_before=None,
                    predicted_residual_after=None, prior_used=False,
                )
                plan = live_controller.PC.fallback_plan(
                    plan, action_id=int(replacement_command.action_id), reason=decision.reason,
                )
                self.last_plan = plan
                default_commands = (replacement_command,)
            self.last_command = (
                min(
                    default_commands,
                    key=lambda item: (
                        self.command_no_change.get((str(observation_digest), item.command_id), 0),
                        self.command_uses.get(item.command_id, 0), item.command_id,
                    ),
                )
                if default_commands else
                action_commands.ActionCommand.create(int(decision.action_id))
                if action_commands is not None
                and not action_commands.requires_payload(int(decision.action_id))
                else None
            )
            repeated_no_change = self.no_change_attempts.get((str(observation_digest), int(decision.action_id)), 0)
            if repeated_no_change:
                alternatives = [
                    action for action in legal
                    if self.no_change_attempts.get((str(observation_digest), action), 0) == 0
                ]
                if alternatives:
                    replacement = min(alternatives, key=lambda action: (self.action_uses.get(action, 0), action))
                    decision = type(decision)(
                        action_id=replacement,
                        fallback_action_id=decision.fallback_action_id,
                        reason="information-after-no-change",
                        template_hash=None,
                        residual_before=None,
                        predicted_residual_after=None,
                        prior_used=False,
                    )
                    plan = live_controller.PC.fallback_plan(plan, action_id=replacement, reason="same-state-no-change-excluded")
                    self.last_plan = plan

            r2_1 = None
            rank_actions = getattr(schema_observer, "rank_actions", None)
            rank_authorized = getattr(schema_observer, "rank_authorized_policy", None)
            if self.fast_path.active and callable(rank_authorized):
                r2_1 = rank_authorized(legal, authorization=self.fast_path.document())
                if not r2_1:
                    self.fast_path.revoke("no-preferred-legal-successor")
            if r2_1 is None and callable(rank_actions):
                runtime_snapshot = getattr(runtime, "snapshot", {})
                latest_note = runtime_snapshot.get("scratchpad")
                semantic_explanation = (
                    latest_note if isinstance(latest_note, Mapping)
                    else runtime_snapshot.get("current_explanation") or {}
                )
                r2_1 = rank_actions(
                    legal,
                    fallback_action=int(decision.action_id),
                    action_commands=commands,
                    semantic_goal=(
                        semantic_explanation.get("goal_proposals")
                        or semantic_explanation.get("goal_proposal")
                    ),
                    semantic_abductions=semantic_explanation.get("abductive_compositions") or (),
                    same_frame_no_change={
                        item.command_id: self.command_no_change.get(
                            (str(observation_digest), item.command_id), 0,
                        )
                        for item in commands
                    },
                )
            if r2_1 is not None:
                semantic_projection = getattr(schema_observer, "semantic_projection", None)
                scratchpad = sys.modules.get("one_action_scratchpad")
                publish_projection = getattr(scratchpad, "record_r2_semantic_projection", None)
                if callable(semantic_projection) and callable(publish_projection):
                    projection = semantic_projection(ranking=r2_1)
                    projection = publish_projection(projection) or projection
                    publish_runtime = getattr(runtime, "set_r2_semantic_projection", None)
                    if callable(publish_runtime):
                        publish_runtime(projection)
                r2_action = int(r2_1["selected_action"])
                selected_command_id = str(
                    (r2_1.get("selected_command") or {}).get("command_id", "")
                )
                selected_command = next(
                    (item for item in commands if item.command_id == selected_command_id),
                    None,
                )
                fast_mode = (r2_1.get("control_proposal") or {}).get("mode") == "FAST_PATH"
                if (
                    r2_1.get("execution_authorized", r2_1.get("control_override", False))
                    and (
                        r2_action != int(decision.action_id) or fast_mode
                        or selected_command is not None
                        and (
                            self.last_command is None
                            or selected_command.command_id != self.last_command.command_id
                        )
                    )
                ):
                    explanation = r2_1.get("current_explanation") or {}
                    prediction = explanation.get("prediction", {})
                    control_status = str(explanation.get("control_status", ""))
                    decision = type(decision)(
                        action_id=r2_action,
                        fallback_action_id=int(decision.fallback_action_id),
                        reason=(
                            "r2.1-bounded-fast-path"
                            if fast_mode else "r2.1-control-v0-progress"
                            if control_status == "PROGRESS_ELIGIBLE"
                            or (not control_status and prediction.get("expected_progress", 0) and prediction["expected_progress"] > 0)
                            else "r2.1-control-v0-probe"
                        ),
                        template_hash=None,
                        residual_before=prediction.get("residual_before"),
                        predicted_residual_after=prediction.get("residual_after"),
                        prior_used=prediction.get("actor_delta") is not None,
                    )
                    plan = live_controller.PC.fallback_plan(plan, action_id=r2_action, reason=decision.reason)
                    self.last_plan = plan
                    if selected_command is not None:
                        self.last_command = selected_command

            selected = [
                prediction for prediction in plan.predictions
                if prediction.prediction_id in plan.selected_prediction_ids
            ]
            improvements = [
                prediction.current_residual - prediction.predicted_residual
                for prediction in selected if prediction.predicted_residual is not None
            ]
            if plan.mode == "control":
                role = "goal-progress"
            elif plan.probe_basis == "single-binding-confirmation" and any(value > 0 for value in improvements):
                role = "progress-and-information"
            else:
                role = "information"
            active = self._active_records()
            situated_explanations = [
                {
                    "kind": "situated-control-explanation",
                    "schema_object_id": item.schema_object_id,
                    "binding_object_id": item.graph_binding_id,
                    "operator": item.operator,
                    "effect_pair": list(item.effect_pair),
                    "control_eligible": item.control_eligible,
                    "confirmations": item.prospective_confirmations,
                    "refutations": item.prospective_refutations,
                }
                for item in active
            ]
            if r2_1 and r2_1.get("explanations"):
                situated_explanations = list(r2_1["explanations"])
            winning_family = {
                "kind": "winning-explanation-family",
                "status": "exists-unidentified",
                "nonempty": True,
                "candidate_first_interventions": len(legal),
                "completeness_assumption": (
                    "the environment is solvable and the open transition-model family "
                    "contains its true dynamics"
                ),
                "grounded_from": "current-frame",
            }
            ranked_actions = [int(decision.action_id), *(
                action for action in sorted(
                    (item for item in legal if item != int(decision.action_id)),
                    key=lambda action: (
                        self.no_change_attempts.get((str(observation_digest), action), 0),
                        self.action_uses.get(action, 0),
                        action,
                    ),
                )
            )]
            top_actions = [
                {
                    "rank": rank,
                    "action": action,
                    "selected": rank == 1,
                    "role": role if rank == 1 else "next-alternative",
                    "prior_uses": self.action_uses.get(action, 0),
                    "same-frame_no_change": self.no_change_attempts.get((str(observation_digest), action), 0),
                }
                for rank, action in enumerate(ranked_actions[:3], start=1)
            ]
            r2_execution_authorized = bool(
                r2_1 and r2_1.get(
                    "execution_authorized", r2_1.get("control_override", False),
                )
            )
            advisory_top_actions = []
            if r2_1 and r2_1.get("top_actions") and r2_execution_authorized:
                top_actions = list(r2_1["top_actions"])
                role = str(top_actions[0]["role"])
            elif r2_1 and r2_1.get("top_actions"):
                advisory_top_actions = list(r2_1["top_actions"])
            salient_schemas = [
                {
                    "schema_object_id": item.schema_object_id,
                    "operator": item.operator,
                    "effect_pair": list(item.effect_pair),
                    "control_eligible": item.control_eligible,
                    "confirmations": item.prospective_confirmations,
                    "refutations": item.prospective_refutations,
                }
                for item in active[:5]
            ]
            self.last_contract = {
                "protocol": "one-action-decision-v0",
                "basis_revision": int(basis_revision),
                "observation_digest": str(observation_digest),
                "objective": {
                    "kind": "relational-residual-objective",
                    "direction": "decrease",
                    "terminal_condition": "environment level increment",
                },
                "winning_explanation_set": winning_family,
                "explanations": [winning_family, *situated_explanations],
                "current_explanation": r2_1.get("current_explanation") if r2_1 and r2_1.get("current_explanation") else (situated_explanations[0] if situated_explanations else winning_family),
                "top_actions": top_actions,
                "advisory_top_actions": advisory_top_actions,
                "salient_schemas": salient_schemas,
                "candidate_count": len(legal),
                "selected_action": int(decision.action_id),
                "selected_command": (
                    self.last_command.document() if self.last_command is not None else None
                ),
                "selection_role": role,
                "selection_rule": r2_1.get("selection_rule") if r2_1 else "lexicographic(progress, decision-relevant-information, support, novelty, stable-id)",
                "predictions": [asdict(item) for item in selected],
                "r2_1_explanation_control": r2_1,
                "repeated_identical_no_change_excluded": bool(repeated_no_change),
                "one_external_action_only": True,
            }
            return decision, plan

        def selected_action_command(self, decision: Any) -> Any:
            """Return the exact payload-bearing command authorized for commit."""
            if self.last_command is None or int(self.last_command.action_id) != int(decision.action_id):
                if action_commands is None:
                    return None
                if action_commands.requires_payload(int(decision.action_id)):
                    raise RuntimeError("parameterized action has no evidence-grounded payload candidate")
                return action_commands.ActionCommand.create(int(decision.action_id))
            return self.last_command

        def observe(self, action: int, before_grid: Any, after_grid: Any) -> dict[str, Any]:
            learning = super().observe(action, before_grid, after_grid)
            r2_1_settlement = None
            schema_observer = getattr(runtime, "schema_observer", None) if runtime is not None else None
            settle_action = getattr(schema_observer, "settle_action", None)
            if callable(settle_action):
                r2_1_settlement = settle_action(
                    self.last_command if self.last_command is not None else int(action),
                    before_grid, after_grid,
                )
                semantic_projection = getattr(schema_observer, "semantic_projection", None)
                scratchpad = sys.modules.get("one_action_scratchpad")
                publish_projection = getattr(scratchpad, "record_r2_semantic_projection", None)
                ranking = (self.last_contract or {}).get("r2_1_explanation_control")
                if callable(semantic_projection) and callable(publish_projection):
                    projection = semantic_projection(ranking=ranking, settlement=r2_1_settlement)
                    projection = publish_projection(projection) or projection
                    publish_runtime = getattr(runtime, "set_r2_semantic_projection", None)
                    if callable(publish_runtime):
                        publish_runtime(projection)
            pending_prediction_id = self.pending_r2_prediction_id
            self.pending_r2_prediction_id = None
            adjudication_status = (
                r2_1_settlement.get("adjudication")
                if isinstance(r2_1_settlement, Mapping) else None
            )
            if pending_prediction_id is not None and adjudication_status in {"confirmed", "refuted"}:
                inherited = learning.get("prospective_adjudication")
                merged = dict(inherited) if isinstance(inherited, Mapping) else {
                    "protocol": "prospective-adjudication-v1",
                    "judgments": [],
                }
                merged["judgments"] = [
                    *list(merged.get("judgments", ())),
                    {
                        "prediction_id": pending_prediction_id,
                        "status": "supports" if adjudication_status == "confirmed" else "refutes",
                        "source": "r2.1-explanation-settlement",
                    },
                ]
                learning = {**learning, "prospective_adjudication": merged}
            changed = before_grid != after_grid
            command_id = (
                self.last_command.command_id if self.last_command is not None
                else f"legacy-action:{int(action)}"
            )
            self.command_uses[command_id] = self.command_uses.get(command_id, 0) + 1
            if not changed:
                key = (self.current_observation_digest, int(action))
                self.no_change_attempts[key] = self.no_change_attempts.get(key, 0) + 1
                command_key = (self.current_observation_digest, command_id)
                self.command_no_change[command_key] = self.command_no_change.get(command_key, 0) + 1
            settlement = {
                "action": int(action),
                "command": (
                    self.last_command.document() if self.last_command is not None else None
                ),
                "predecessor_digest": self.current_observation_digest,
                "observation_changed": bool(changed),
                "outcome": "changed" if changed else "no-visible-change",
                "prospective_adjudication": learning.get("prospective_adjudication"),
                "r2_1_explanation_adjudication": r2_1_settlement,
            }
            self.settlements.append(settlement)
            executed_explanation = (self.last_contract or {}).get("current_explanation")
            self.fast_path.consider(executed_explanation, r2_1_settlement)
            if runtime is not None:
                trace = action_trace(int(action), before_grid, after_grid)
                runtime.record_r2_action_trace(trace)
                scratchpad = sys.modules.get("one_action_scratchpad")
                record = getattr(scratchpad, "record_r2_action_trace", None)
                if callable(record):
                    record(trace)
                record_transition = getattr(scratchpad, "record_r2_transition_observation", None)
                if callable(record_transition):
                    record_transition(
                        action=int(action), observation_changed=bool(changed),
                        outcome=settlement["outcome"], trace=trace,
                        settlement=r2_1_settlement,
                    )
                runtime.update(settlement=settlement)
            return {**learning, "one_action_settlement": settlement}

        def observe_level_transition(self, action: int, before_grid: Any, after_grid: Any) -> dict[str, Any]:
            """Settle a win without fitting correspondences across level boards."""
            self.action_uses[int(action)] += 1
            settlement = {
                "action": int(action),
                "predecessor_digest": self.current_observation_digest,
                "observation_changed": True,
                "outcome": "level-completed",
                "prospective_adjudication": None,
                "r2_1_explanation_adjudication": None,
            }
            self.settlements.append(settlement)

            # These objects are grounded in the completed level.  Action-use
            # statistics and R2.1's empirical action effects remain game-scoped.
            self.inner = live_controller.Q0.PairPotentialController((), "externally-proposed")
            self.inner.uses.update(self.action_uses)
            self.action_uses = self.inner.uses
            self.records.clear()
            self.active_schema_ids.clear()
            self.probe_decisions = 0
            self.control_decisions = 0
            self.last_plan = None
            self.last_plan_records.clear()
            self.no_change_attempts.clear()
            self.command_no_change.clear()
            self.current_observation_digest = ""
            self.last_contract = None
            self.last_command = None
            self.fast_path.revoke("level-transition")

            if runtime is not None:
                runtime.update(settlement=settlement)
            return {
                "prospective_adjudication": None,
                "one_action_settlement": settlement,
                "level_transition": True,
            }

        def observe_game_over_retry(
            self, before_grid: Any, after_grid: Any, successor: Any | None = None
        ) -> dict[str, Any]:
            """Settle RESET as a retry boundary, never as action-0 mechanics."""
            settlement = {
                "action": 0,
                "predecessor_digest": self.current_observation_digest,
                "observation_changed": before_grid != after_grid,
                "outcome": "game-over-retry-reset",
                "prospective_adjudication": None,
                "r2_1_explanation_adjudication": None,
            }
            self.settlements.append(settlement)

            # Preserve game-scoped mechanics, but discard every failed-attempt
            # controller object and pending prediction.
            self.inner = live_controller.Q0.PairPotentialController((), "externally-proposed")
            self.inner.uses.update(self.action_uses)
            self.action_uses = self.inner.uses
            self.records.clear()
            self.active_schema_ids.clear()
            self.probe_decisions = 0
            self.control_decisions = 0
            self.last_plan = None
            self.last_plan_records.clear()
            self.no_change_attempts.clear()
            self.command_no_change.clear()
            self.current_observation_digest = ""
            self.last_contract = None
            self.last_command = None
            self.pending_r2_prediction_id = None
            self.fast_path.revoke("game-over-retry-reset")

            if runtime is not None:
                after_retry = getattr(runtime, "after_retry_reset", None)
                if callable(after_retry) and successor is not None:
                    after_retry(successor, self)
                else:
                    rebuild_retry = getattr(runtime, "rebuild_retry_boundary", None)
                    if callable(rebuild_retry):
                        rebuild_retry(settlement)
                    else:
                        runtime.update(settlement=settlement)
            return {
                "prospective_adjudication": None,
                "one_action_settlement": settlement,
                "retry_boundary": True,
            }

        def report(self) -> dict[str, Any]:
            return {
                **super().report(),
                "decision_contract": self.last_contract,
                "no_change_attempt_count": sum(self.no_change_attempts.values()),
                "command_no_change_attempt_count": sum(self.command_no_change.values()),
                "latest_settlement": self.settlements[-1] if self.settlements else None,
            }

    OneActionController.__name__ = "OneActionController"
    return OneActionController
