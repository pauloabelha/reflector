"""Provider-neutral, schema-constrained proposals for symbolic genomes."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from ..core.mind import MindConfig

MUTABLE_FIELDS = frozenset(MindConfig().to_dict())


@dataclass(frozen=True, slots=True)
class MutationProposal:
    patch: dict[str, bool | int | float]
    rationale: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MutationProposal":
        if set(value) != {"patch", "rationale"}:
            raise ValueError("proposal requires exactly patch and rationale")
        patch = value["patch"]
        rationale = value["rationale"]
        if not isinstance(patch, dict) or not patch:
            raise ValueError("proposal patch must be a non-empty object")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("proposal rationale must be non-empty")
        unknown = set(patch) - MUTABLE_FIELDS
        if unknown:
            raise ValueError(f"proposal contains unknown fields: {sorted(unknown)}")
        if any(
            isinstance(item, (dict, list, tuple, str)) or item is None
            for item in patch.values()
        ):
            raise ValueError("proposal values must be scalar booleans or numbers")
        return cls(dict(patch), rationale.strip())

    def apply(self, parent: MindConfig) -> MindConfig:
        # Dataclass construction is the final type/range firewall.
        updated = parent.to_dict()
        updated.update(self.patch)
        return MindConfig.from_dict(updated)

    def to_dict(self) -> dict[str, Any]:
        return {"patch": self.patch, "rationale": self.rationale}


class MutationProvider(Protocol):
    def propose(
        self, parent: MindConfig, feedback: dict[str, Any]
    ) -> MutationProposal: ...


class DeterministicMutationProvider:
    """Offline provider used for tests and reproducible baseline evolution."""

    def __init__(self, proposal: MutationProposal) -> None:
        self.proposal = proposal

    def propose(
        self, parent: MindConfig, feedback: dict[str, Any]
    ) -> MutationProposal:
        del parent, feedback
        return self.proposal


class OpenAICompatibleMutationProvider:
    """Optional development-only JSON provider; never imported by inference."""

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def propose(
        self, parent: MindConfig, feedback: dict[str, Any]
    ) -> MutationProposal:
        prompt = {
            "task": (
                "Propose one bounded mutation to this symbolic ARC agent genome. "
                "Return JSON only: {patch: {...}, rationale: string}."
            ),
            "mutable_fields": sorted(MUTABLE_FIELDS),
            "parent": parent.to_dict(),
            "feedback": feedback,
        }
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(prompt, sort_keys=True),
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            }
        ).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = json.loads(response.read())
        if "choices" in raw:
            raw = json.loads(raw["choices"][0]["message"]["content"])
        return MutationProposal.from_dict(raw)
