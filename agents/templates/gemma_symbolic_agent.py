"""Research adapter for Reflector with bounded runtime Gemma arbitration."""

from __future__ import annotations

import os
from typing import Any, cast

from reflector.research.gemma_hybrid import GemmaAugmentedSymbolicPolicy
from reflector.runtime.deployment import deployed_config

from .reflector_agent import ReflectorAgent


class GemmaSymbolicAgent(ReflectorAgent):
    """Accepted symbolic architecture plus an impasse-gated Gemma component."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.policy = GemmaAugmentedSymbolicPolicy(
            deployed_config(),
            endpoint=os.environ.get(
                "REFLECTOR_GEMMA_ENDPOINT", "http://127.0.0.1:18092"
            ),
            model=os.environ.get(
                "REFLECTOR_GEMMA_MODEL",
                "google_gemma-4-E2B-it-Q4_K_M.gguf",
            ),
        )
        self.MAX_ACTIONS = self.policy.mind.config.action_budget - 1

    @property
    def brain(self) -> Any:
        return cast(GemmaAugmentedSymbolicPolicy, self.policy).gemma
