"""Fail closed unless the experiment uses the audited frozen v1.16 chain."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final


SOURCE_COMMIT: Final = "3da145b8d0f502c393d3fd9c6dc7d4a2d53d68ca"
REPOSITORY = Path(__file__).resolve().parents[2]

# Only executable modules imported by the v1.16 chain are included. Tests and
# generated artifacts are intentionally outside the runtime trust boundary.
EXPECTED_SHA256: Final = {
    "experiments/parallel-cognitive-workspace-v0/experiment.py": "3258905a0b313b4678cc255515f3c000f25cf7c4bd1cf64eeb1b18582b50f200",
    "experiments/parallel-cognitive-workspace-v0/qwen_protocol.py": "7da1d31efa01eaf52f15c02b4f39fe4d280971b57c69a21ffd72067ea4e9a4b2",
    "experiments/parallel-cognitive-workspace-v0/qwen_worker.py": "1ef6abc75b34a8f3306a7cda774c115c91d3cb5e309571e3da7a91601cd2b441",
    "experiments/parallel-cognitive-workspace-v0/workspace.py": "b28cc1d4de96a4afae9c80d6c8b0e45a5761c32162073eb515cec09169807899",
    "experiments/parallel-cognitive-workspace-v1-4/ambiguity.py": "a811d1df8f1de5818cdc4e6211e0e8d4530cc440edaaccb39fabf721788b2218",
    "experiments/parallel-cognitive-workspace-v1-4/census.py": "17e1918cda17cfdb68bc50889c640f64dee3acb5d274d17704581e481ae16525",
    "experiments/parallel-cognitive-workspace-v1-4/epistemic_graph.py": "b2524d5c65ead9f37b52302d1d432bd4db037461d432ea53bc1ada5babb4de05",
    "experiments/parallel-cognitive-workspace-v1-4/experiment.py": "5721291d18aba64b5e06ef48c8a42fd5c4f7f98629142db3159bf5813bade18b",
    "experiments/parallel-cognitive-workspace-v1-4/ledger.py": "1f94c3b0d779ef5a3d0d30ad99752293a2cb2c16f4477838ed16da84ae387e25",
    "experiments/parallel-cognitive-workspace-v1-4/live_controller.py": "0e1af77af385b0be65df6145f4d728f31c5d7b0addbee3f27cc73c31095bd2d9",
    "experiments/parallel-cognitive-workspace-v1-4/prospective_control.py": "f1d6ce64eac307bef4a2a579d2ae243eddaee17838ae2f7ee7caa9cc17e82298",
    "experiments/parallel-cognitive-workspace-v1-4/qwen_cognition.py": "99871e2b9b0c2735733f9c52485cd3bcf1550ea3d584504f156ea0d92ef33ab6",
    "experiments/parallel-cognitive-workspace-v1-5/experiment.py": "6e1132048540df0cd61630888b9a33b22e003151a9aa547f45e873249a14f96a",
    "experiments/parallel-cognitive-workspace-v1-6/experiment.py": "e5bd7228cb3ef06bc61f6569986b1383c7b636409f5e40b46c574f54a848a9d6",
    "experiments/parallel-cognitive-workspace-v1-7/experiment.py": "d7ef65527439906e85da9b12bcb4b49dd8bb5b1856fc27a6ba6f229ab70a5030",
    "experiments/parallel-cognitive-workspace-v1-8/experiment.py": "afb96984744fb14fe8b7d7442a6b2bacdbe4ab2b92e57d91b9c58a2fcf8a8622",
    "experiments/parallel-cognitive-workspace-v1-9/evidence_bridge.py": "c06f5b11e53e71ceaa350e0b7a32d7b1632dd48164e838e31dda6cbce60d223a",
    "experiments/parallel-cognitive-workspace-v1-9/evidence_revision.py": "ec15a826de2fdd20d2a955ebe0f930a954289481219f5326bef75d0fedd18a11",
    "experiments/parallel-cognitive-workspace-v1-9/experiment.py": "f45e4a6500870c80ffe61aaaeaef1dbede523fbb5729a05f56ab1b4768e12535",
    "experiments/parallel-cognitive-workspace-v1-9/live_controller.py": "d1b708bb52594db93836073e19b1aa2e5e7c4a06a236a09d36d140dfe3f17a4e",
    "experiments/parallel-cognitive-workspace-v1-10/experiment.py": "7ecfc7de378d739c236405a640e5f33908e476bd98e20ca29069004f2b836527",
    "experiments/parallel-cognitive-workspace-v1-11/experiment.py": "aee24ab44ebe7039e458403fb68001fbb54bda68cea4f22fb0e54555eaaf8a1b",
    "experiments/parallel-cognitive-workspace-v1-12/causal_packet.py": "cbb32ebf83aefcaf35269a335e114724551a8026b4586577bc1bb49bb3a03c99",
    "experiments/parallel-cognitive-workspace-v1-12/experiment.py": "763ce54193a808f82fc1f44da5fc96c34e0418f7b62c7630d7607d4c6182010a",
    "experiments/parallel-cognitive-workspace-v1-12/revision_response.py": "ec91477e966f161dc4e9128dec868d8a6a48d9414f9ce361d38cf9040087edcc",
    "experiments/parallel-cognitive-workspace-v1-13/experiment.py": "9d610666b866c44b38afbfd95878a9f13090f801d554592eef4f04854500bc89",
    "experiments/parallel-cognitive-workspace-v1-14/compiler_feedback.py": "bf474bc600d5ee8f77227f52455ccc5f6ba009073251ef571fd180df1a329579",
    "experiments/parallel-cognitive-workspace-v1-14/experiment.py": "2e4dc9b1089f704c52d9122e32411dc5a171be7c7f56a987d173ff64f01abf6a",
    "experiments/parallel-cognitive-workspace-v1-14/grounding_diagnostics.py": "6cf957b7acfef419d8924fedd575c24205e6f478c4cd1ce8c552da66beedd1c1",
    "experiments/parallel-cognitive-workspace-v1-15/experiment.py": "ce2268f64b79330c07a4c891b2c38d1475953bbc18faf5fe598ff2f54d9293dc",
    "experiments/parallel-cognitive-workspace-v1-15/prospective_criticism_dedup.py": "ad7cb9b5967a98cce275b86b2903c2a8bc1972e6e20651896408c8b5e43b061a",
    "experiments/parallel-cognitive-workspace-v1-16/experiment.py": "49864f5daf175d51bf7b9ee908e7976e87d694422b61a56c5eca10f9f97f59cc",
}


class SourceBoundaryError(RuntimeError):
    """The local frozen implementation differs from the audited source."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_sources() -> dict[str, str]:
    observed: dict[str, str] = {}
    failures: list[str] = []
    for relative, expected in sorted(EXPECTED_SHA256.items()):
        path = REPOSITORY / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        actual = file_sha256(path)
        observed[relative] = actual
        if actual != expected:
            failures.append(f"changed:{relative}:{actual}")
    if failures:
        raise SourceBoundaryError("frozen source guard failed: " + ", ".join(failures))
    return observed
