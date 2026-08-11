"""Production R2.2 Agent Arcade.

The implementation and its frozen runtime ancestry live entirely inside this
package. Imports are lazy so the human Arcade remains lightweight.
"""

from __future__ import annotations

from typing import Any, Sequence


def main(argv: Sequence[str] | None = None) -> int:
    from .experiment import main as run

    return int(run(argv))


def run_game(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .experiment import run_game as run

    return run(*args, **kwargs)


__all__ = ["main", "run_game"]
