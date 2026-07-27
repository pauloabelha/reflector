"""Deterministic representation holdouts for development-time trace evaluation."""

from __future__ import annotations

import random
from dataclasses import replace

from .symbolic import Observation
from .trace import EpisodeTrace

PALETTE_SIZE = 16


def color_permutation(seed: int) -> tuple[int, ...]:
    """Return a seeded ARC-AGI-3 palette permutation, keeping zero fixed."""

    rng = random.Random(seed)
    colors = list(range(1, PALETTE_SIZE))
    rng.shuffle(colors)
    return (0, *colors)


def transform_observation(
    observation: Observation, palette: tuple[int, ...]
) -> Observation:
    if len(palette) != PALETTE_SIZE or set(palette) != set(
        range(PALETTE_SIZE)
    ):
        raise ValueError("palette must permute ARC-AGI-3 colors 0..15")
    return Observation.create(
        state=observation.state,
        available_actions=observation.available_actions,
        frame=tuple(
            tuple(palette[color] for color in row) for row in observation.frame
        ),
        levels_completed=observation.levels_completed,
    )


def color_holdout(trace: EpisodeTrace, seed: int) -> EpisodeTrace:
    """Relabel colors while preserving recorded environment outcomes.

    The holdout probes representational robustness. It is not a substitute for
    rerunning a game environment, so recorded transitions remain ground truth.
    """

    palette = color_permutation(seed)
    transformed = EpisodeTrace(
        format_version=trace.format_version,
        agent_version=trace.agent_version,
        mind_config=dict(trace.mind_config),
    )
    for step in trace.steps:
        transformed.append(
            replace(
                step,
                observation=transform_observation(step.observation, palette),
            )
        )
    if (
        trace.terminal_observation is not None
        and trace.terminal_scene is not None
    ):
        transformed.finish(
            transform_observation(trace.terminal_observation, palette),
            trace.terminal_scene,
            trace.terminal_transition,
        )
    return transformed


def transformed_holdouts(
    traces: dict[str, EpisodeTrace], seeds: tuple[int, ...]
) -> dict[str, EpisodeTrace]:
    return {
        f"{name}::color-{seed}": color_holdout(trace, seed)
        for name, trace in sorted(traces.items())
        for seed in seeds
    }
