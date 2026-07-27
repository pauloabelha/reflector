"""Load the serializable genome selected for this deployed agent."""

from __future__ import annotations

import json
import os

from .mind import MindConfig

CONFIG_ENV = "REFLECTOR_CONFIG_JSON"


def deployed_config() -> MindConfig:
    """Return the packaged candidate configuration, or the symbolic baseline."""

    raw = os.environ.get(CONFIG_ENV)
    if raw is None:
        return MindConfig()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{CONFIG_ENV} must encode a JSON object")
    return MindConfig.from_dict(value)
