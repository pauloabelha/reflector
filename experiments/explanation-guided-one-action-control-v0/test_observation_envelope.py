from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent


def load(name: str):
    path = HERE / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"test_observation_envelope_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ENVELOPE = load("observation_envelope")

FIRST = [[1, 0, 0], [0, 0, 0]]
SECOND = [[1, 2, 0], [0, 0, 0]]
SETTLED = [[1, 2, 3], [0, 0, 0]]


class Array:
    def __init__(self, value):
        self.value = value

    def tolist(self):
        return self.value


def observation(frames):
    return SimpleNamespace(
        frame=frames,
        available_actions=(SimpleNamespace(value=1),),
        state=SimpleNamespace(value="RUNNING"),
        levels_completed=0,
        win_levels=4,
        full_reset=False,
    )


def test_multiframe_packet_preserves_exact_order_and_marks_last_support_settled():
    packet = ENVELOPE.from_observation(observation([Array(FIRST), Array(SECOND), Array(SETTLED)]))

    assert packet["ordered_frames"] == [FIRST, SECOND, SETTLED]
    assert packet["support_count"] == 3
    assert packet["settled_support_ordinal"] == 2
    assert ENVELOPE.settled_frame(packet) == SETTLED
    assert len(set(packet["support_digests"])) == 3
    json.dumps(packet)


def test_packet_digest_is_order_sensitive_even_when_settled_frame_is_identical():
    forward = ENVELOPE.from_observation(observation([FIRST, SECOND, SETTLED]))
    reversed_transients = ENVELOPE.from_observation(observation([SECOND, FIRST, SETTLED]))

    assert ENVELOPE.settled_frame(forward) == ENVELOPE.settled_frame(reversed_transients)
    assert forward["settled_support_digest"] == reversed_transients["settled_support_digest"]
    assert forward["digest"] != reversed_transients["digest"]


def test_single_grid_is_one_support_not_a_stack_of_rows():
    packet = ENVELOPE.from_observation(observation(Array(SETTLED)))

    assert packet["ordered_frames"] == [SETTLED]
    assert packet["support_count"] == 1
    assert packet["settled_support_ordinal"] == 0


def test_runtime_keeps_envelope_but_exposes_settled_frame_to_control():
    runtime_module = load("runtime")
    runtime = runtime_module.LiveRuntime()
    runtime.set_observation_envelope_builder(ENVELOPE.from_observation)
    raw = observation([FIRST, SECOND, SETTLED])

    frame, packet = runtime.observation_surfaces(raw)
    runtime.update(frame=frame, observation_envelope=packet, turn=7)

    snapshot = runtime.read()
    assert snapshot["frame"] == SETTLED
    assert snapshot["observation_envelope"]["ordered_frames"] == [FIRST, SECOND, SETTLED]
    assert snapshot["observation_envelope"]["settled_support_ordinal"] == 2


def test_replay_surface_exposes_ordered_packet_and_keeps_settled_frame():
    arcade = load("arcade")
    packet = ENVELOPE.from_observation(observation([FIRST, SECOND, SETTLED]))

    fields = arcade._frame_fields({"grid": SETTLED, "observation_envelope": packet})

    assert fields["frame"] == SETTLED
    assert fields["ordered_frames"] == [FIRST, SECOND, SETTLED]
    assert fields["observation_envelope"] == packet


def test_inherited_ledger_blob_keeps_envelope_and_legacy_settled_grid(tmp_path):
    experiment = load("experiment")
    experiment.install(experiment.RUNTIME.LiveRuntime())
    raw = observation([FIRST, SECOND, SETTLED])

    digest, _record, grid = experiment.BASE.store_observation(tmp_path, raw)
    stored = experiment.BASE.LEDGER.read_blob(tmp_path, digest)

    assert [list(row) for row in grid] == SETTLED
    assert stored["grid"] == SETTLED
    assert stored["observation_envelope"]["ordered_frames"] == [FIRST, SECOND, SETTLED]
    assert stored["observation_envelope"]["settled_support_ordinal"] == 2
