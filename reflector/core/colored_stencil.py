"""Grounded primary-stencil composition over visible relational roles.

The planner represents a scene as two same-sized dense grids, a congruent
palette, and one outlined movable template.  It never stores a game name,
absolute coordinate, color identity, or action identifier.  Cardinal and
diagonal primary masks are normalized half-plane predicates; controls are
bound from rendered pose changes.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Literal

type Frame = tuple[tuple[int, ...], ...]
type Grid = tuple[tuple[int, ...], ...]
type Mask = tuple[tuple[bool, ...], ...]
type Point = tuple[int, int]
type Pose = Literal["n", "ne", "e", "se", "s", "sw", "w", "nw"]
type PendingKind = Literal[
    "movement",
    "palette",
    "primary",
    "secondary-proposal",
    "secondary-confirmation",
    "secondary-c4-confirmation",
    "secondary-plan",
]

POSE_COORDINATES: dict[Pose, Point] = {
    "n": (0, -1),
    "ne": (1, -1),
    "e": (1, 0),
    "se": (1, 1),
    "s": (0, 1),
    "sw": (-1, 1),
    "w": (-1, 0),
    "nw": (-1, -1),
}
COORDINATE_POSES = {value: key for key, value in POSE_COORDINATES.items()}


@dataclass(frozen=True, order=True, slots=True)
class StencilToken:
    action_id: int
    data: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class SecondaryStencil:
    """One visible payload component projected into a construction edge."""

    mask: Mask
    token: StencilToken
    radial_rank: int


@dataclass(frozen=True, slots=True)
class _Component:
    color: int
    points: tuple[Point, ...]
    bbox: tuple[int, int, int, int]
    centroid: Point

    @property
    def area(self) -> int:
        return len(self.points)


@dataclass(frozen=True, slots=True)
class StencilScene:
    reference: Grid
    construction: Grid
    reference_bbox: tuple[int, int, int, int]
    construction_bbox: tuple[int, int, int, int]
    palette: tuple[tuple[int, StencilToken], ...]
    selected_color: int
    pose: Pose
    secondary: tuple[SecondaryStencil, ...] = ()


@dataclass(frozen=True, slots=True)
class _StencilStroke:
    kind: Literal["primary", "secondary"]
    pose: Pose
    color: int
    mask: Mask


@dataclass(slots=True)
class PrimaryStencilPlanner:
    """Learn controller bindings and search exact primary-stencil programs."""

    enabled: bool = False
    secondary_enabled: bool = False
    complex_action: int = 6
    reset_action: int = 0
    max_levels: int = 2
    max_search_states: int = 50_000
    max_plan_depth: int = 16
    current_level: int | None = None
    pending_token: StencilToken | None = None
    pending_scene: StencilScene | None = None
    pending_kind: PendingKind | None = None
    pending_secondary_mask: Mask | None = None
    pending_secondary_context: bool = False
    pending_secondary_plan_action: bool = False
    action_directions: dict[int, Point] = field(default_factory=dict)
    no_effect_poses: dict[int, set[Pose]] = field(default_factory=dict)
    movement_confirmations: Counter[int] = field(default_factory=Counter)
    palette_predictions: int = 0
    palette_confirmations: int = 0
    palette_conflicts: int = 0
    apply_predictions: int = 0
    apply_confirmations: int = 0
    apply_conflicts: int = 0
    secondary_proposals: int = 0
    secondary_predictions: int = 0
    secondary_confirmations: int = 0
    secondary_progress_confirmations: int = 0
    secondary_conflicts: int = 0
    secondary_c4_predictions: int = 0
    secondary_c4_confirmations: int = 0
    secondary_search_states: int = 0
    secondary_search_diagnostic: str = "not-attempted"
    secondary_plan_actions_issued: int = 0
    secondary_plan_steps: int = 0
    secondary_plan_action_conflicts: int = 0
    secondary_proposal_attempts: int = 0
    secondary_pose_inspections: int = 0
    secondary_ambiguous_pose_observations: int = 0
    secondary_probe_exhaustions: int = 0
    secondary_candidate_ambiguities: int = 0
    secondary_regrounding_failures: int = 0
    secondary_causal_validation_failures: int = 0
    secondary_authority_resets: int = 0
    plan_steps: int = 0
    search_states: int = 0
    submit_action: int | None = None
    quarantined: bool = False
    diagnostic: str = "exact-off"
    last_scene: StencilScene | None = None
    last_plan_length: int = 0
    last_target_pose: Pose | None = None
    last_reference_mismatches: int = 0
    secondary_proposed_mask: Mask | None = None
    secondary_proposed_color: int | None = None
    secondary_canonical_mask: Mask | None = None
    secondary_confirmed_poses: set[Pose] = field(default_factory=set)
    secondary_c4_confirmed: bool = False
    secondary_probe_target: Pose | None = None
    secondary_inspected_poses: set[Pose] = field(default_factory=set)
    secondary_c4_rejected_poses: set[Pose] = field(default_factory=set)
    secondary_probe_exhausted: bool = False
    secondary_last_candidate_matches: int = 0
    secondary_last_stroke_count: int = 0

    def observe(self, frame: Frame, levels_completed: int) -> StencilScene | None:
        """Ground the current scene and validate the previously issued action."""

        scene = infer_stencil_scene(frame, complex_action=self.complex_action)
        if not self.enabled:
            self.diagnostic = "exact-off"
            self.last_scene = scene
            return scene
        if self.current_level is None:
            self.current_level = levels_completed
        elif levels_completed > self.current_level:
            if self.pending_secondary_context:
                self.secondary_progress_confirmations += 1
                if self.pending_kind == "secondary-c4-confirmation":
                    self.secondary_c4_confirmations += 1
                if self.pending_secondary_plan_action:
                    self.secondary_plan_steps += 1
            self.current_level = levels_completed
            self._clear_pending()
            self.no_effect_poses.clear()
            self.submit_action = None
            self.quarantined = False
            self._reset_secondary_authority()
            self.diagnostic = "level-advanced"
        if (
            self.pending_token is not None
            and self.pending_scene is not None
            and levels_completed == self.current_level
        ):
            if scene is None:
                accepted = (
                    self._reject_current_pending("pending-scene-ungrounded")
                    if (
                        self.secondary_enabled
                        or self.pending_secondary_context
                    )
                    else False
                )
            else:
                accepted = self._validate_pending(
                    self.pending_scene,
                    scene,
                    self.pending_token,
                )
            if self.pending_secondary_plan_action:
                if accepted:
                    self.secondary_plan_steps += 1
                else:
                    self.secondary_plan_action_conflicts += 1
        self._clear_pending()
        self.last_scene = scene
        if scene is None and not self.quarantined:
            self.diagnostic = "no-unique-stencil-scene"
        return scene

    def select(
        self,
        frame: Frame,
        levels_completed: int,
        legal_actions: tuple[int, ...],
    ) -> StencilToken | None:
        """Return one grounded probe or exact plan step, otherwise abstain."""

        if not self.enabled:
            self.diagnostic = "exact-off"
            return None
        if levels_completed >= self.max_levels and not self.secondary_enabled:
            self.diagnostic = "stage-complete"
            return None
        if self.quarantined:
            self.diagnostic = "quarantined"
            return None
        scene = self.last_scene or infer_stencil_scene(
            frame,
            complex_action=self.complex_action,
        )
        if scene is None:
            self.diagnostic = "no-unique-stencil-scene"
            return None
        plain_actions = tuple(
            action
            for action in legal_actions
            if action not in {self.reset_action, self.complex_action}
        )
        if len(plain_actions) < 5:
            self.diagnostic = "insufficient-plain-controls"
            return None

        if len(self.action_directions) < 4:
            token = self._movement_probe(scene.pose, plain_actions)
            if token is None:
                self.diagnostic = "movement-binding-stalled"
                return None
            self.diagnostic = "probing-pose-controller"
            return self._register(token, scene)

        remaining = tuple(
            action for action in plain_actions if action not in self.action_directions
        )
        if len(remaining) != 1:
            self.diagnostic = "ambiguous-submit-control"
            return None
        self.submit_action = remaining[0]
        plan = self._plan(scene)
        if plan:
            self.last_plan_length = len(plan)
            self.plan_steps += 1
            self.diagnostic = "executing-primary-stencil-plan"
            return self._register(plan[0], scene)
        self.last_plan_length = 0
        if not self.secondary_enabled:
            self.diagnostic = "no-primary-stencil-plan"
            return None
        return self._select_secondary(scene)

    def _clear_pending(self) -> None:
        self.pending_token = None
        self.pending_scene = None
        self.pending_kind = None
        self.pending_secondary_mask = None
        self.pending_secondary_context = False
        self.pending_secondary_plan_action = False

    def _reset_secondary_authority(self) -> None:
        """Require each new level to re-establish rendered operator authority."""

        if self.secondary_enabled:
            self.secondary_authority_resets += 1
        self.secondary_proposed_mask = None
        self.secondary_proposed_color = None
        self.secondary_canonical_mask = None
        self.secondary_confirmed_poses.clear()
        self.secondary_c4_confirmed = False
        self.secondary_probe_target = None
        self.secondary_inspected_poses.clear()
        self.secondary_c4_rejected_poses.clear()
        self.secondary_probe_exhausted = False
        self.secondary_last_candidate_matches = 0
        self.secondary_last_stroke_count = 0
        self.secondary_search_diagnostic = "not-attempted"

    def _movement_probe(
        self,
        pose: Pose,
        plain_actions: tuple[int, ...],
    ) -> StencilToken | None:
        unresolved = tuple(
            action for action in plain_actions if action not in self.action_directions
        )
        for action in unresolved:
            if pose not in self.no_effect_poses.get(action, set()):
                return StencilToken(action)

        targets = {
            candidate_pose
            for candidate_pose in POSE_COORDINATES
            if any(
                candidate_pose not in self.no_effect_poses.get(action, set())
                for action in unresolved
            )
        }
        return self._first_navigation_step(pose, targets)

    def _plan(self, scene: StencilScene) -> tuple[StencilToken, ...]:
        assert self.submit_action is not None
        start = (scene.construction, scene.selected_color, scene.pose)
        queue: deque[
            tuple[tuple[Grid, int, Pose], tuple[StencilToken, ...]]
        ] = deque(((start, ()),))
        visited = {start}
        self.search_states = 0
        while queue and self.search_states < self.max_search_states:
            (construction, color, pose), path = queue.popleft()
            self.search_states += 1
            mismatches = _grid_mismatches(construction, scene.reference)
            if not path:
                self.last_reference_mismatches = mismatches
            if len(path) >= self.max_plan_depth:
                continue
            for action, direction in sorted(self.action_directions.items()):
                next_pose = move_pose(pose, direction)
                if next_pose == pose:
                    continue
                next_state = (construction, color, next_pose)
                if next_state in visited:
                    continue
                visited.add(next_state)
                queue.append((next_state, path + (StencilToken(action),)))
            for next_color, token in scene.palette:
                if next_color == color:
                    continue
                next_state = (construction, next_color, pose)
                if next_state in visited:
                    continue
                visited.add(next_state)
                queue.append((next_state, path + (token,)))
            committed = apply_primary_stencil(construction, pose, color)
            if committed == scene.reference:
                self.last_target_pose = pose
                return path + (StencilToken(self.submit_action),)
            next_state = (committed, color, pose)
            if next_state not in visited:
                visited.add(next_state)
                queue.append(
                    (
                        next_state,
                        path + (StencilToken(self.submit_action),),
                    )
                )
        return ()

    def _select_secondary(self, scene: StencilScene) -> StencilToken | None:
        """Induce, confirm, and use a rendered secondary edge component."""

        if self.submit_action is None:
            self.diagnostic = "secondary-submit-control-missing"
            return None
        if self.secondary_canonical_mask is None:
            return self._secondary_induction_step(scene)

        confirmed_masks = {
            pose: oriented_secondary_mask(self.secondary_canonical_mask, pose)
            for pose in sorted(self.secondary_confirmed_poses)
        }
        if self.secondary_c4_confirmed:
            confirmed_masks = {
                pose: oriented_secondary_mask(self.secondary_canonical_mask, pose)
                for pose in _cardinal_poses()
            }
        strokes, search_states = synthesize_stencil_strokes(
            scene.construction,
            scene.reference,
            palette_colors=tuple(color for color, _token in scene.palette),
            secondary_masks=confirmed_masks,
            max_depth=self.max_plan_depth,
            max_states=self.max_search_states,
        )
        self.secondary_search_states = search_states
        if strokes:
            self.secondary_search_diagnostic = "confirmed-plan-found"
            self.secondary_last_stroke_count = len(strokes)
            return self._select_stroke_step(scene, strokes)
        self.secondary_search_diagnostic = (
            "confirmed-state-cap-reached"
            if search_states >= self.max_search_states
            else "no-confirmed-exact-plan"
        )

        if self.secondary_c4_confirmed:
            self.secondary_last_stroke_count = 0
            self.diagnostic = "no-secondary-stencil-plan"
            return None

        tentative_masks = {
            pose: oriented_secondary_mask(self.secondary_canonical_mask, pose)
            for pose in _cardinal_poses()
        }
        tentative, search_states = synthesize_stencil_strokes(
            scene.construction,
            scene.reference,
            palette_colors=tuple(color for color, _token in scene.palette),
            secondary_masks=tentative_masks,
            max_depth=self.max_plan_depth,
            max_states=self.max_search_states,
        )
        self.secondary_search_states = search_states
        self.secondary_search_diagnostic = (
            "prospective-plan-found"
            if tentative
            else "prospective-state-cap-reached"
            if search_states >= self.max_search_states
            else "no-prospective-exact-plan"
        )
        target = next(
            (
                stroke.pose
                for stroke in tentative
                if stroke.kind == "secondary"
                and stroke.pose not in self.secondary_confirmed_poses
                and stroke.pose not in self.secondary_c4_rejected_poses
            ),
            None,
        )
        if target is None:
            self.diagnostic = "no-prospective-secondary-c4-plan"
            return None
        self.secondary_probe_target = target
        return self._secondary_c4_probe_step(scene, target)

    def _secondary_induction_step(
        self,
        scene: StencilScene,
    ) -> StencilToken | None:
        cardinal_poses = set(_cardinal_poses())
        candidate_count = len(scene.secondary) if scene.pose in cardinal_poses else 0
        self.secondary_last_candidate_matches = candidate_count
        if self.secondary_proposed_mask is not None and (
            scene.pose not in cardinal_poses or candidate_count != 1
        ):
            self.secondary_regrounding_failures += 1
            self.secondary_conflicts += 1
            self.quarantined = True
            self.diagnostic = "secondary-proposal-component-not-unique"
            return None
        if scene.pose not in cardinal_poses or candidate_count != 1:
            if scene.pose in cardinal_poses and scene.pose not in (
                self.secondary_inspected_poses
            ):
                self.secondary_inspected_poses.add(scene.pose)
                self.secondary_pose_inspections += 1
                if candidate_count > 1:
                    self.secondary_ambiguous_pose_observations += 1
                    self.secondary_candidate_ambiguities += 1
            uninspected = cardinal_poses - self.secondary_inspected_poses
            if not uninspected:
                if not self.secondary_probe_exhausted:
                    self.secondary_probe_exhausted = True
                    self.secondary_probe_exhaustions += 1
                self.diagnostic = "secondary-pose-probes-exhausted"
                return None
            navigation = self._first_navigation_step(
                scene.pose,
                uninspected,
            )
            if navigation is None:
                self.diagnostic = "secondary-pose-probe-navigation-stalled"
                return None
            self.diagnostic = "navigating-to-secondary-component"
            return self._register(
                navigation,
                scene,
                secondary_context=True,
            )
        component = scene.secondary[0]
        if self.secondary_proposed_mask is None:
            contrast = self._fully_visible_palette_color(
                scene,
                component.mask,
            )
            if contrast is None:
                self.diagnostic = "no-visible-secondary-probe-color"
                return None
            if scene.selected_color != contrast:
                token = _palette_token(scene, contrast)
                if token is None:
                    self.diagnostic = "secondary-probe-palette-unrepresented"
                    return None
                self.diagnostic = "selecting-secondary-proposal-color"
                return self._register(
                    token,
                    scene,
                    kind="palette",
                    secondary_context=True,
                )
            self.diagnostic = "probing-secondary-edge-component"
            return self._register(
                component.token,
                scene,
                kind="secondary-proposal",
                secondary_mask=component.mask,
                secondary_context=True,
            )

        if (
            canonical_secondary_mask(component.mask, scene.pose)
            != canonical_secondary_mask(
                self.secondary_proposed_mask,
                scene.pose,
            )
        ):
            self.secondary_regrounding_failures += 1
            self.secondary_conflicts += 1
            self.quarantined = True
            self.diagnostic = "secondary-component-identity-drift"
            return None
        confirmation_color = self._fully_visible_palette_color(
            scene,
            component.mask,
            exclude={self.secondary_proposed_color},
        )
        if confirmation_color is None:
            self.diagnostic = "no-independent-secondary-confirmation-color"
            return None
        if scene.selected_color != confirmation_color:
            token = _palette_token(scene, confirmation_color)
            if token is None:
                self.diagnostic = "secondary-confirmation-palette-unrepresented"
                return None
            self.diagnostic = "selecting-secondary-confirmation-color"
            return self._register(
                token,
                scene,
                kind="palette",
                secondary_context=True,
            )
        self.diagnostic = "confirming-secondary-overwrite"
        return self._register(
            component.token,
            scene,
            kind="secondary-confirmation",
            secondary_mask=component.mask,
            secondary_context=True,
        )

    def _secondary_c4_probe_step(
        self,
        scene: StencilScene,
        target: Pose,
    ) -> StencilToken | None:
        if scene.pose != target:
            navigation = self._first_navigation_step(scene.pose, {target})
            if navigation is None:
                self.diagnostic = "secondary-c4-navigation-stalled"
                return None
            self.diagnostic = "navigating-to-secondary-c4-probe"
            return self._register(
                navigation,
                scene,
                secondary_context=True,
            )
        expected_mask = oriented_secondary_mask(
            self.secondary_canonical_mask,
            target,
        )
        matches = tuple(
            item
            for item in scene.secondary
            if item.mask == expected_mask
            and canonical_secondary_mask(item.mask, scene.pose)
            == self.secondary_canonical_mask
        )
        self.secondary_last_candidate_matches = len(matches)
        if len(matches) != 1:
            self.secondary_regrounding_failures += 1
            self.secondary_c4_rejected_poses.add(target)
            if len(matches) > 1:
                self.secondary_candidate_ambiguities += 1
                self.diagnostic = "secondary-c4-component-ambiguous"
            else:
                self.diagnostic = "secondary-c4-component-not-regrounded"
            return None
        component = matches[0]
        contrast = self._fully_visible_palette_color(scene, expected_mask)
        if contrast is None:
            self.secondary_c4_rejected_poses.add(target)
            self.diagnostic = "no-visible-secondary-c4-color"
            return None
        if scene.selected_color != contrast:
            token = _palette_token(scene, contrast)
            if token is None:
                self.secondary_c4_rejected_poses.add(target)
                self.diagnostic = "secondary-c4-palette-unrepresented"
                return None
            self.diagnostic = "selecting-secondary-c4-color"
            return self._register(
                token,
                scene,
                kind="palette",
                secondary_context=True,
            )
        self.diagnostic = "confirming-secondary-c4-transfer"
        return self._register(
            component.token,
            scene,
            kind="secondary-c4-confirmation",
            secondary_mask=expected_mask,
            secondary_context=True,
        )

    def _select_stroke_step(
        self,
        scene: StencilScene,
        strokes: tuple[_StencilStroke, ...],
    ) -> StencilToken | None:
        if self.submit_action is None:
            self.diagnostic = "secondary-submit-control-missing"
            return None
        stroke = strokes[0]
        self.last_target_pose = stroke.pose
        if scene.selected_color != stroke.color:
            token = _palette_token(scene, stroke.color)
            if token is None:
                self.diagnostic = "secondary-plan-palette-unrepresented"
                return None
            self.diagnostic = "executing-secondary-stencil-plan"
            return self._register_secondary_plan_action(
                token,
                scene,
                kind="palette",
            )
        if scene.pose != stroke.pose:
            navigation = self._first_navigation_step(scene.pose, {stroke.pose})
            if navigation is None:
                self.diagnostic = "secondary-plan-navigation-stalled"
                return None
            self.diagnostic = "executing-secondary-stencil-plan"
            return self._register_secondary_plan_action(navigation, scene)
        if stroke.kind == "primary":
            self.diagnostic = "executing-secondary-stencil-plan"
            return self._register_secondary_plan_action(
                StencilToken(self.submit_action),
                scene,
                kind="primary",
            )
        matches = tuple(
            item for item in scene.secondary if item.mask == stroke.mask
        )
        self.secondary_last_candidate_matches = len(matches)
        if len(matches) != 1:
            self.secondary_regrounding_failures += 1
            if len(matches) > 1:
                self.secondary_candidate_ambiguities += 1
                self.diagnostic = "secondary-plan-component-ambiguous"
            else:
                self.diagnostic = "secondary-plan-component-not-regrounded"
            return None
        component = matches[0]
        self.diagnostic = "executing-secondary-stencil-plan"
        return self._register_secondary_plan_action(
            component.token,
            scene,
            kind="secondary-plan",
            secondary_mask=stroke.mask,
        )

    def _register_secondary_plan_action(
        self,
        token: StencilToken,
        scene: StencilScene,
        *,
        kind: PendingKind | None = None,
        secondary_mask: Mask | None = None,
    ) -> StencilToken:
        self.secondary_plan_actions_issued += 1
        return self._register(
            token,
            scene,
            kind=kind,
            secondary_mask=secondary_mask,
            secondary_context=True,
            secondary_plan_action=True,
        )

    def _fully_visible_palette_color(
        self,
        scene: StencilScene,
        mask: Mask,
        *,
        exclude: set[int | None] | None = None,
    ) -> int | None:
        blocked = exclude or set()
        support = _mask_points(mask)
        eligible = tuple(
            color
            for color, _token in scene.palette
            if color not in blocked
            and all(scene.construction[y][x] != color for x, y in support)
        )
        reference_counts = Counter(
            value for row in scene.reference for value in row
        )
        if (
            scene.selected_color in eligible
            and reference_counts[scene.selected_color] > 0
        ):
            return scene.selected_color
        represented = tuple(
            color for color in eligible if reference_counts[color] > 0
        )
        if represented:
            return max(
                represented,
                key=lambda color: (
                    reference_counts[color],
                    -eligible.index(color),
                ),
            )
        return eligible[0] if eligible else None

    def _first_navigation_step(
        self,
        start: Pose,
        targets: set[Pose],
    ) -> StencilToken | None:
        queue: deque[tuple[Pose, int | None]] = deque(((start, None),))
        visited = {start}
        while queue:
            pose, first = queue.popleft()
            if pose in targets and first is not None:
                return StencilToken(first)
            for action, direction in sorted(self.action_directions.items()):
                next_pose = move_pose(pose, direction)
                if next_pose == pose or next_pose in visited:
                    continue
                visited.add(next_pose)
                queue.append((next_pose, action if first is None else first))
        return None

    def _validate_pending(
        self,
        before: StencilScene,
        after: StencilScene,
        token: StencilToken,
    ) -> bool:
        strict_roles = self.secondary_enabled or self.pending_secondary_context
        if before.reference != after.reference:
            self.no_effect_poses.clear()
            if strict_roles:
                return self._reject_current_pending("pending-reference-changed")
            self.diagnostic = "level-scene-refreshed"
            return False
        if self.pending_kind in {
            "secondary-proposal",
            "secondary-confirmation",
            "secondary-c4-confirmation",
            "secondary-plan",
        }:
            return self._validate_secondary_pending(
                before,
                after,
                self.pending_kind,
                self.pending_secondary_mask,
            )
        if self.pending_kind == "palette" or (
            self.pending_kind is None
            and token.action_id == self.complex_action
            and token.data
        ):
            selected = next(
                (
                    color
                    for color, palette_token in before.palette
                    if palette_token == token
                ),
                None,
            )
            if selected is None:
                self.palette_conflicts += 1
                return self._reject_current_pending(
                    "unrepresented-palette-token",
                )
            self.palette_predictions += 1
            if (
                after.construction == before.construction
                and after.selected_color == selected
                and (
                    not strict_roles
                    or (
                        after.pose == before.pose
                        and after.reference_bbox == before.reference_bbox
                        and after.construction_bbox
                        == before.construction_bbox
                        and after.palette == before.palette
                        and after.secondary == before.secondary
                    )
                )
            ):
                self.palette_confirmations += 1
                self.diagnostic = "palette-selection-confirmed"
                return True
            self.palette_conflicts += 1
            return self._reject_current_pending("palette-commit-mismatch")
        if token.data:
            if strict_roles:
                return self._reject_current_pending(
                    "unclassified-complex-pending"
                )
            return False
        if token.action_id == self.submit_action:
            self.apply_predictions += 1
            expected = apply_primary_stencil(
                before.construction,
                before.pose,
                before.selected_color,
            )
            if (
                after.construction == expected
                and after.selected_color == before.selected_color
                and after.pose == before.pose
                and (
                    not strict_roles
                    or (
                        after.reference_bbox == before.reference_bbox
                        and after.construction_bbox
                        == before.construction_bbox
                        and after.palette == before.palette
                        and after.secondary == before.secondary
                    )
                )
            ):
                self.apply_confirmations += 1
                self.diagnostic = "stencil-apply-confirmed"
                return True
            self.apply_conflicts += 1
            return self._reject_current_pending("stencil-apply-mismatch")
        before_coord = POSE_COORDINATES[before.pose]
        after_coord = POSE_COORDINATES[after.pose]
        delta = (
            after_coord[0] - before_coord[0],
            after_coord[1] - before_coord[1],
        )
        if before.construction != after.construction:
            return self._reject_current_pending(
                (
                    "movement-changed-grounded-roles"
                    if strict_roles
                    else "movement-changed-grounded-grids"
                ),
            )
        if strict_roles and (
            after.selected_color != before.selected_color
            or after.reference_bbox != before.reference_bbox
            or after.construction_bbox != before.construction_bbox
            or after.palette != before.palette
        ):
            return self._reject_current_pending(
                "movement-changed-grounded-roles",
            )
        if delta in {(1, 0), (-1, 0), (0, 1), (0, -1)}:
            known = self.action_directions.get(token.action_id)
            if known is not None and known != delta:
                return self._reject_current_pending(
                    "controller-direction-conflict",
                )
            self.action_directions[token.action_id] = delta
            self.movement_confirmations[token.action_id] += 1
            self.diagnostic = "pose-controller-bound"
            return True
        elif delta == (0, 0):
            self.no_effect_poses.setdefault(token.action_id, set()).add(before.pose)
            self.diagnostic = "pose-boundary-no-effect"
            return True
        return self._reject_current_pending("noncardinal-pose-transition")

    def _validate_secondary_pending(
        self,
        before: StencilScene,
        after: StencilScene,
        kind: PendingKind,
        mask: Mask | None,
    ) -> bool:
        if mask is None:
            return self._reject_current_pending(
                "secondary-mask-missing",
                secondary=True,
            )
        if (
            after.reference != before.reference
            or after.selected_color != before.selected_color
            or after.pose != before.pose
            or after.reference_bbox != before.reference_bbox
            or after.construction_bbox != before.construction_bbox
            or after.palette != before.palette
            or after.secondary != before.secondary
        ):
            return self._reject_current_pending(
                "secondary-changed-nonconstruction-role",
                secondary=True,
            )
        expected = apply_secondary_stencil(
            before.construction,
            mask,
            before.selected_color,
        )
        changed = _changed_grid_points(before.construction, after.construction)
        support = _mask_points(mask)
        if kind == "secondary-proposal":
            if (
                not changed
                or changed != support
                or any(
                    after.construction[y][x] != before.selected_color
                    for x, y in changed
                )
            ):
                return self._reject_current_pending(
                    "secondary-proposal-not-exact-overwrite",
                    secondary=True,
                )
            self.secondary_proposals += 1
            self.secondary_proposed_mask = mask
            self.secondary_proposed_color = before.selected_color
            self.diagnostic = "secondary-mask-proposed"
            return True

        if after.construction != expected:
            return self._reject_current_pending(
                "secondary-overwrite-mismatch",
                secondary=True,
            )
        if before.pose not in _cardinal_poses():
            return self._reject_current_pending(
                "secondary-noncardinal-confirmation",
                secondary=True,
            )
        canonical = canonical_secondary_mask(mask, before.pose)
        if kind == "secondary-confirmation":
            if (
                self.secondary_proposed_mask is None
                or self.secondary_proposed_color == before.selected_color
                or canonical
                != canonical_secondary_mask(
                    self.secondary_proposed_mask,
                    before.pose,
                )
            ):
                return self._reject_current_pending(
                    "secondary-confirmation-not-independent",
                    secondary=True,
                )
            self.secondary_confirmations += 1
            self.secondary_canonical_mask = canonical
            self.secondary_confirmed_poses.add(before.pose)
            self.diagnostic = "secondary-overwrite-confirmed"
            return True
        if kind == "secondary-c4-confirmation":
            if (
                self.secondary_canonical_mask is None
                or canonical != self.secondary_canonical_mask
            ):
                return self._reject_current_pending(
                    "secondary-c4-mask-mismatch",
                    secondary=True,
                )
            self.secondary_confirmations += 1
            self.secondary_c4_confirmations += 1
            self.secondary_c4_confirmed = True
            self.secondary_confirmed_poses.add(before.pose)
            self.diagnostic = "secondary-c4-confirmed"
            return True
        if kind != "secondary-plan":
            return self._reject_current_pending(
                "secondary-pending-kind-invalid",
                secondary=True,
            )
        self.secondary_confirmations += 1
        self.diagnostic = "secondary-plan-step-confirmed"
        return True

    def _reject_current_pending(
        self,
        diagnostic: str,
        *,
        secondary: bool | None = None,
    ) -> bool:
        secondary_failure = (
            self.pending_secondary_context
            or self.pending_kind
            in {
                "secondary-proposal",
                "secondary-confirmation",
                "secondary-c4-confirmation",
                "secondary-plan",
            }
            if secondary is None
            else secondary
        )
        self.quarantined = True
        if secondary_failure:
            self.secondary_conflicts += 1
            self.secondary_causal_validation_failures += 1
        self.diagnostic = diagnostic
        return False

    def _register(
        self,
        token: StencilToken,
        scene: StencilScene,
        *,
        kind: PendingKind | None = None,
        secondary_mask: Mask | None = None,
        secondary_context: bool = False,
        secondary_plan_action: bool = False,
    ) -> StencilToken:
        self.pending_token = token
        self.pending_scene = scene
        if kind is None:
            if token in {item for _color, item in scene.palette}:
                kind = "palette"
            elif token.action_id == self.submit_action and not token.data:
                kind = "primary"
            else:
                kind = "movement"
        self.pending_kind = kind
        self.pending_secondary_mask = secondary_mask
        self.pending_secondary_context = secondary_context
        self.pending_secondary_plan_action = secondary_plan_action
        if kind == "secondary-proposal":
            self.secondary_proposal_attempts += 1
        elif kind in {
            "secondary-confirmation",
            "secondary-c4-confirmation",
            "secondary-plan",
        }:
            self.secondary_predictions += 1
            if kind == "secondary-c4-confirmation":
                self.secondary_c4_predictions += 1
        return token

    def to_dict(self) -> dict[str, object]:
        return {
            "active": int(self.enabled and not self.quarantined),
            "diagnostic": self.diagnostic,
            "scene_grounded": int(self.last_scene is not None),
            "current_pose": self.last_scene.pose if self.last_scene else None,
            "palette_roles": len(self.last_scene.palette) if self.last_scene else 0,
            "movement_bindings": len(self.action_directions),
            "movement_confirmations": sum(self.movement_confirmations.values()),
            "submit_action_grounded": int(self.submit_action is not None),
            "palette_predictions": self.palette_predictions,
            "palette_confirmations": self.palette_confirmations,
            "palette_conflicts": self.palette_conflicts,
            "apply_predictions": self.apply_predictions,
            "apply_confirmations": self.apply_confirmations,
            "apply_conflicts": self.apply_conflicts,
            "secondary_enabled": int(self.secondary_enabled),
            "secondary_components": (
                len(self.last_scene.secondary) if self.last_scene else 0
            ),
            "secondary_proposals": self.secondary_proposals,
            "secondary_predictions": self.secondary_predictions,
            "secondary_confirmations": self.secondary_confirmations,
            "secondary_progress_confirmations": (
                self.secondary_progress_confirmations
            ),
            "secondary_conflicts": self.secondary_conflicts,
            "secondary_c4_predictions": self.secondary_c4_predictions,
            "secondary_c4_confirmations": self.secondary_c4_confirmations,
            "secondary_c4_confirmed": int(self.secondary_c4_confirmed),
            "secondary_search_states": self.secondary_search_states,
            "secondary_search_diagnostic": self.secondary_search_diagnostic,
            "secondary_plan_actions_issued": self.secondary_plan_actions_issued,
            "secondary_plan_steps": self.secondary_plan_steps,
            "secondary_plan_action_conflicts": (
                self.secondary_plan_action_conflicts
            ),
            "secondary_proposal_attempts": self.secondary_proposal_attempts,
            "secondary_pose_inspections": self.secondary_pose_inspections,
            "secondary_inspected_poses": sorted(self.secondary_inspected_poses),
            "secondary_ambiguous_pose_observations": (
                self.secondary_ambiguous_pose_observations
            ),
            "secondary_probe_exhaustions": self.secondary_probe_exhaustions,
            "secondary_probe_exhausted": int(self.secondary_probe_exhausted),
            "secondary_candidate_ambiguities": (
                self.secondary_candidate_ambiguities
            ),
            "secondary_regrounding_failures": (
                self.secondary_regrounding_failures
            ),
            "secondary_causal_validation_failures": (
                self.secondary_causal_validation_failures
            ),
            "secondary_authority_resets": self.secondary_authority_resets,
            "secondary_last_candidate_matches": (
                self.secondary_last_candidate_matches
            ),
            "secondary_last_stroke_count": self.secondary_last_stroke_count,
            "secondary_probe_target": self.secondary_probe_target,
            "secondary_c4_rejected_poses": sorted(
                self.secondary_c4_rejected_poses
            ),
            "secondary_confirmed_poses": sorted(self.secondary_confirmed_poses),
            "secondary_proposed_mask_area": (
                len(_mask_points(self.secondary_proposed_mask))
                if self.secondary_proposed_mask is not None
                else 0
            ),
            "secondary_canonical_mask_area": (
                len(_mask_points(self.secondary_canonical_mask))
                if self.secondary_canonical_mask is not None
                else 0
            ),
            "pending_kind": self.pending_kind,
            "pending_secondary_context": int(self.pending_secondary_context),
            "pending_secondary_plan_action": int(
                self.pending_secondary_plan_action
            ),
            "pending_secondary_mask_area": (
                len(_mask_points(self.pending_secondary_mask))
                if self.pending_secondary_mask is not None
                else 0
            ),
            "search_states": self.search_states,
            "last_plan_length": self.last_plan_length,
            "plan_steps": self.plan_steps,
            "last_target_pose": self.last_target_pose,
            "last_reference_mismatches": self.last_reference_mismatches,
            "quarantined": int(self.quarantined),
        }


def infer_stencil_scene(
    frame: Frame,
    *,
    complex_action: int = 6,
) -> StencilScene | None:
    """Uniquely ground reference, construction, palette, template, and pose."""

    if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
        return None
    background = Counter(value for row in frame for value in row).most_common(1)[0][0]
    components = _components(frame)
    palette = _palette_roles(frame, components, complex_action=complex_action)
    if len(palette) < 2:
        return None
    patches = _dense_square_patches(frame, background)
    paired = tuple(
        (left, right)
        for index, left in enumerate(patches)
        for right in patches[index + 1 :]
        if len(left[1]) == len(right[1])
    )
    if len(paired) != 1:
        return None
    first, second = paired[0]
    size = len(first[1])
    palette_colors = {color for color, _token in palette}
    palette_centers = tuple(
        (
            dict(token.data)["x"],
            dict(token.data)["y"],
        )
        for _color, token in palette
    )
    template_candidates = tuple(
        item
        for item in components
        if item.color in palette_colors
        and size <= item.area <= 2 * size * size
        and not any(_bbox_contains(patch[0], item.bbox) for patch in (first, second))
        and not any(
            item.bbox[0] <= center[0] <= item.bbox[2]
            and item.bbox[1] <= center[1] <= item.bbox[3]
            for center in palette_centers
        )
    )
    if not template_candidates:
        return None
    ranked: list[
        tuple[int, int, tuple[tuple[int, int, int, int], Grid], _Component]
    ] = []
    for patch in (first, second):
        center = _bbox_center(patch[0])
        for component in template_candidates:
            distance = _chebyshev(center, component.centroid)
            ranked.append((distance, -component.area, patch, component))
    ranked.sort(key=lambda item: (item[0], item[1], item[2][0], item[3].bbox))
    if len(ranked) > 1 and ranked[0][:2] == ranked[1][:2]:
        return None
    _distance, _neg_area, construction, template = ranked[0]
    reference = second if construction == first else first
    pose = _relative_pose(
        _bbox_center(construction[0]),
        template.centroid,
        size=size,
    )
    if pose is None:
        return None
    secondary = _secondary_stencils(
        construction_bbox=construction[0],
        primary=template,
        template_candidates=template_candidates,
        pose=pose,
        complex_action=complex_action,
    )
    return StencilScene(
        reference=reference[1],
        construction=construction[1],
        reference_bbox=reference[0],
        construction_bbox=construction[0],
        palette=palette,
        selected_color=template.color,
        pose=pose,
        secondary=secondary,
    )


def _secondary_stencils(
    *,
    construction_bbox: tuple[int, int, int, int],
    primary: _Component,
    template_candidates: tuple[_Component, ...],
    pose: Pose,
    complex_action: int,
) -> tuple[SecondaryStencil, ...]:
    if pose not in _cardinal_poses():
        return ()
    size = construction_bbox[2] - construction_bbox[0] + 1
    if construction_bbox[3] - construction_bbox[1] + 1 != size:
        return ()
    center = _bbox_center(construction_bbox)
    primary_distance = _chebyshev(center, primary.centroid)
    ranked: list[tuple[int, SecondaryStencil]] = []
    for component in template_candidates:
        if (
            component == primary
            or component.color != primary.color
            or component.area >= primary.area
            or _relative_pose(center, component.centroid, size=size) != pose
        ):
            continue
        distance = _chebyshev(center, component.centroid)
        if distance <= primary_distance:
            continue
        mask = project_secondary_mask(
            size,
            construction_bbox=construction_bbox,
            payload_points=component.points,
            pose=pose,
        )
        if mask is None or len(_mask_points(mask)) != component.area:
            continue
        click = min(
            component.points,
            key=lambda point: (
                abs(point[0] - component.centroid[0])
                + abs(point[1] - component.centroid[1]),
                point,
            ),
        )
        ranked.append(
            (
                distance,
                SecondaryStencil(
                    mask=mask,
                    token=StencilToken(
                        complex_action,
                        (("x", click[0]), ("y", click[1])),
                    ),
                    radial_rank=0,
                ),
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1].token.data))
    return tuple(
        SecondaryStencil(
            mask=item.mask,
            token=item.token,
            radial_rank=index + 1,
        )
        for index, (_distance, item) in enumerate(ranked)
    )


def project_secondary_mask(
    size: int,
    *,
    construction_bbox: tuple[int, int, int, int],
    payload_points: tuple[Point, ...],
    pose: Pose,
) -> Mask | None:
    """Project a cardinal exterior payload into the aligned grid edge."""

    if size < 2 or pose not in _cardinal_poses() or not payload_points:
        return None
    min_x = min(point[0] for point in payload_points)
    max_x = max(point[0] for point in payload_points)
    min_y = min(point[1] for point in payload_points)
    max_y = max(point[1] for point in payload_points)
    construction_x, construction_y, max_construction_x, max_construction_y = (
        construction_bbox
    )
    if (
        max_construction_x - construction_x + 1 != size
        or max_construction_y - construction_y + 1 != size
    ):
        return None
    projected: set[Point] = set()
    for x, y in payload_points:
        if pose == "n":
            target = (x - construction_x, y - min_y)
        elif pose == "s":
            target = (x - construction_x, size - 1 - (max_y - y))
        elif pose == "w":
            target = (x - min_x, y - construction_y)
        else:
            target = (size - 1 - (max_x - x), y - construction_y)
        if not (0 <= target[0] < size and 0 <= target[1] < size):
            return None
        projected.add(target)
    if len(projected) != len(payload_points):
        return None
    return tuple(
        tuple((x, y) in projected for x in range(size))
        for y in range(size)
    )


def primary_mask(size: int, pose: Pose) -> Mask:
    """Return one normalized cardinal or inclusive diagonal half-plane."""

    if size < 2:
        raise ValueError("primary stencil requires a grid of size at least two")
    middle = size // 2
    return tuple(
        tuple(
            (
                y < middle
                if pose == "n"
                else y >= size - middle
                if pose == "s"
                else x < middle
                if pose == "w"
                else x >= size - middle
                if pose == "e"
                else x + y <= size - 1
                if pose == "nw"
                else x + y >= size - 1
                if pose == "se"
                else x >= y
                if pose == "ne"
                else y >= x
            )
            for x in range(size)
        )
        for y in range(size)
    )


def apply_primary_stencil(grid: Grid, pose: Pose, color: int) -> Grid:
    if not grid or any(len(row) != len(grid) for row in grid):
        raise ValueError("primary stencil grid must be non-empty and square")
    mask = primary_mask(len(grid), pose)
    return tuple(
        tuple(color if mask[y][x] else value for x, value in enumerate(row))
        for y, row in enumerate(grid)
    )


def apply_secondary_stencil(grid: Grid, mask: Mask, color: int) -> Grid:
    if (
        not grid
        or len(mask) != len(grid)
        or any(len(row) != len(grid) for row in grid)
        or any(len(row) != len(grid) for row in mask)
    ):
        raise ValueError("secondary stencil mask must match a non-empty square grid")
    return tuple(
        tuple(color if mask[y][x] else value for x, value in enumerate(row))
        for y, row in enumerate(grid)
    )


def canonical_secondary_mask(mask: Mask, pose: Pose) -> Mask:
    rotations = {"n": 0, "e": 3, "s": 2, "w": 1}.get(pose)
    if rotations is None:
        raise ValueError("secondary stencil canonicalization requires a cardinal pose")
    output = mask
    for _index in range(rotations):
        output = _rotate_mask_clockwise(output)
    return output


def oriented_secondary_mask(mask: Mask | None, pose: Pose) -> Mask:
    if mask is None:
        raise ValueError("a canonical secondary stencil mask is required")
    rotations = {"n": 0, "e": 1, "s": 2, "w": 3}.get(pose)
    if rotations is None:
        raise ValueError("secondary stencil orientation requires a cardinal pose")
    output = mask
    for _index in range(rotations):
        output = _rotate_mask_clockwise(output)
    return output


def synthesize_stencil_strokes(
    construction: Grid,
    reference: Grid,
    *,
    palette_colors: tuple[int, ...],
    secondary_masks: dict[Pose, Mask],
    max_depth: int,
    max_states: int,
) -> tuple[tuple[_StencilStroke, ...], int]:
    """Reverse-synthesize an exact last-write-wins stroke program."""

    if (
        not construction
        or len(construction) != len(reference)
        or any(len(row) != len(construction) for row in construction)
        or any(len(row) != len(reference) for row in reference)
    ):
        return (), 0
    size = len(construction)
    candidates: list[tuple[Literal["primary", "secondary"], Pose, Mask]] = [
        ("primary", pose, primary_mask(size, pose))
        for pose in POSE_COORDINATES
    ]
    candidates.extend(
        ("secondary", pose, mask)
        for pose, mask in sorted(secondary_masks.items())
        if len(mask) == size and all(len(row) == size for row in mask)
    )
    all_points = frozenset((x, y) for y in range(size) for x in range(size))
    queue: deque[tuple[frozenset[Point], tuple[_StencilStroke, ...]]] = deque(
        ((all_points, ()),)
    )
    visited = {all_points}
    states = 0
    palette = set(palette_colors)
    while queue and states < max_states:
        exposed, reverse_path = queue.popleft()
        states += 1
        if all(
            construction[y][x] == reference[y][x]
            for x, y in exposed
        ):
            return tuple(reversed(reverse_path)), states
        if len(reverse_path) >= max_depth:
            continue
        for kind, pose, mask in candidates:
            support = _mask_points(mask)
            touched = support & exposed
            if not touched:
                continue
            target_colors = {reference[y][x] for x, y in touched}
            if len(target_colors) != 1:
                continue
            color = next(iter(target_colors))
            if color not in palette:
                continue
            next_exposed = frozenset(exposed - support)
            if next_exposed in visited:
                continue
            visited.add(next_exposed)
            queue.append(
                (
                    next_exposed,
                    reverse_path
                    + (
                        _StencilStroke(
                            kind=kind,
                            pose=pose,
                            color=color,
                            mask=mask,
                        ),
                    ),
                )
            )
    return (), states


def move_pose(pose: Pose, direction: Point) -> Pose:
    x, y = POSE_COORDINATES[pose]
    candidate = (x + direction[0], y + direction[1])
    return COORDINATE_POSES.get(candidate, pose)


def _cardinal_poses() -> tuple[Pose, ...]:
    return ("n", "e", "s", "w")


def _rotate_mask_clockwise(mask: Mask) -> Mask:
    if not mask or any(len(row) != len(mask) for row in mask):
        raise ValueError("C4 mask rotation requires a non-empty square mask")
    size = len(mask)
    return tuple(
        tuple(mask[size - 1 - x][y] for x in range(size))
        for y in range(size)
    )


def _mask_points(mask: Mask) -> set[Point]:
    return {
        (x, y)
        for y, row in enumerate(mask)
        for x, active in enumerate(row)
        if active
    }


def _changed_grid_points(before: Grid, after: Grid) -> set[Point]:
    if len(before) != len(after) or any(
        len(before_row) != len(after_row)
        for before_row, after_row in zip(before, after, strict=False)
    ):
        return set()
    return {
        (x, y)
        for y, (before_row, after_row) in enumerate(
            zip(before, after, strict=True)
        )
        for x, (before_value, after_value) in enumerate(
            zip(before_row, after_row, strict=True)
        )
        if before_value != after_value
    }


def _palette_token(scene: StencilScene, color: int) -> StencilToken | None:
    return next(
        (token for candidate, token in scene.palette if candidate == color),
        None,
    )


def _components(frame: Frame) -> tuple[_Component, ...]:
    height = len(frame)
    width = len(frame[0])
    visited: set[Point] = set()
    output: list[_Component] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            color = frame[y][x]
            queue = [(x, y)]
            visited.add((x, y))
            points: list[Point] = []
            while queue:
                current = queue.pop()
                points.append(current)
                cx, cy = current
                for candidate in (
                    (cx - 1, cy),
                    (cx + 1, cy),
                    (cx, cy - 1),
                    (cx, cy + 1),
                ):
                    nx, ny = candidate
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and candidate not in visited
                        and frame[ny][nx] == color
                    ):
                        visited.add(candidate)
                        queue.append(candidate)
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points)
            output.append(
                _Component(
                    color=color,
                    points=tuple(sorted(points)),
                    bbox=(min_x, min_y, max_x, max_y),
                    centroid=(
                        sum(point[0] for point in points) // len(points),
                        sum(point[1] for point in points) // len(points),
                    ),
                )
            )
    return tuple(output)


def _palette_roles(
    frame: Frame,
    components: tuple[_Component, ...],
    *,
    complex_action: int,
) -> tuple[tuple[int, StencilToken], ...]:
    enclosures = tuple(
        item
        for item in components
        if item.area == 16
        and item.bbox[2] - item.bbox[0] == 4
        and item.bbox[3] - item.bbox[1] == 4
    )
    groups: dict[tuple[int, int], list[_Component]] = {}
    for item in enclosures:
        groups.setdefault((item.color, item.centroid[1]), []).append(item)
    candidates: list[tuple[tuple[int, StencilToken], ...]] = []
    for items in groups.values():
        ordered = tuple(sorted(items, key=lambda item: item.centroid[0]))
        if len(ordered) < 2:
            continue
        spacings = {
            right.centroid[0] - left.centroid[0]
            for left, right in zip(ordered, ordered[1:], strict=False)
        }
        if len(spacings) != 1:
            continue
        roles: list[tuple[int, StencilToken]] = []
        for enclosure in ordered:
            center_x, center_y = enclosure.centroid
            payload = {
                frame[y][x]
                for y in range(center_y - 1, center_y + 2)
                for x in range(center_x - 1, center_x + 2)
            }
            if len(payload) != 1:
                break
            roles.append(
                (
                    next(iter(payload)),
                    StencilToken(
                        complex_action,
                        (("x", center_x), ("y", center_y)),
                    ),
                )
            )
        if len(roles) == len(ordered) and len({item[0] for item in roles}) == len(
            roles
        ):
            candidates.append(tuple(roles))
    if len(candidates) != 1:
        return ()
    return candidates[0]


def _dense_square_patches(
    frame: Frame,
    background: int,
) -> tuple[tuple[tuple[int, int, int, int], Grid], ...]:
    height = len(frame)
    width = len(frame[0])
    output: list[tuple[tuple[int, int, int, int], Grid]] = []
    for size in range(6, min(16, height - 2, width - 2) + 1):
        for y in range(1, height - size):
            for x in range(1, width - size):
                if any(
                    frame[row][column] == background
                    for row in range(y, y + size)
                    for column in range(x, x + size)
                ):
                    continue
                ring = (
                    tuple((column, y - 1) for column in range(x - 1, x + size + 1))
                    + tuple(
                        (column, y + size)
                        for column in range(x - 1, x + size + 1)
                    )
                    + tuple((x - 1, row) for row in range(y, y + size))
                    + tuple((x + size, row) for row in range(y, y + size))
                )
                if all(frame[row][column] == background for column, row in ring):
                    bbox = (x, y, x + size - 1, y + size - 1)
                    grid = tuple(
                        tuple(frame[row][x : x + size])
                        for row in range(y, y + size)
                    )
                    output.append((bbox, grid))
    maximal = tuple(
        item
        for item in output
        if not any(
            item != other and _bbox_contains(other[0], item[0])
            for other in output
        )
    )
    return tuple(sorted(maximal, key=lambda item: item[0]))


def _relative_pose(center: Point, template: Point, *, size: int) -> Pose | None:
    dx = template[0] - center[0]
    dy = template[1] - center[1]
    threshold = max(2, size // 3)
    sx = 0 if abs(dx) < threshold else 1 if dx > 0 else -1
    sy = 0 if abs(dy) < threshold else 1 if dy > 0 else -1
    if (sx, sy) == (0, 0):
        return None
    return COORDINATE_POSES.get((sx, sy))


def _bbox_center(bbox: tuple[int, int, int, int]) -> Point:
    return ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)


def _bbox_contains(
    outer: tuple[int, int, int, int],
    inner: tuple[int, int, int, int],
) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _chebyshev(left: Point, right: Point) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]))


def _grid_mismatches(left: Grid, right: Grid) -> int:
    if len(left) != len(right) or any(
        len(left_row) != len(right_row)
        for left_row, right_row in zip(left, right, strict=False)
    ):
        return max(len(left), len(right))
    return sum(
        left_value != right_value
        for left_row, right_row in zip(left, right, strict=True)
        for left_value, right_value in zip(left_row, right_row, strict=True)
    )
