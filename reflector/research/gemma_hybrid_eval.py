"""Run the research-only inference-time Gemma hybrid on offline games."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import redirect_stdout
from importlib import import_module
from pathlib import Path
from typing import Any


def run_game(
    *,
    game: str,
    environments_dir: Path,
    recordings_dir: Path,
    stream_dir: Path,
    endpoint: str,
    model: str,
    action_budget: int,
) -> dict[str, Any]:
    os.environ["OPERATION_MODE"] = "offline"
    os.environ["ENVIRONMENTS_DIR"] = str(environments_dir.resolve())
    os.environ["RECORDINGS_DIR"] = str(recordings_dir.resolve())
    os.environ["REFLECTOR_GEMMA_STREAM_DIR"] = str(stream_dir.resolve())
    os.environ["REFLECTOR_GEMMA_ENDPOINT"] = endpoint
    os.environ["REFLECTOR_GEMMA_MODEL"] = model
    os.environ["REFLECTOR_GEMMA_ACTION_BUDGET"] = str(action_budget)

    agents_module = import_module("agents")
    agent_module = import_module("agents.templates.gemma_hybrid_agent")
    agents_module.AVAILABLE_AGENTS["gemma-hybrid"] = getattr(
        agent_module, "GemmaHybridAgent"
    )
    swarm_class = getattr(agents_module, "Swarm")
    with redirect_stdout(sys.stderr):
        swarm = swarm_class(
            agent="gemma-hybrid",
            ROOT_URL="http://localhost:8001",
            games=[game],
            record=False,
        )
        scorecard = swarm.main()
    if scorecard is None or len(swarm.agents) != 1:
        raise RuntimeError("Gemma hybrid returned no scorecard")
    agent = swarm.agents[0]
    return {
        "kind": "research-inference-time-llm-evaluation",
        "classification": "hybrid-symbolic-llm",
        "game": game,
        "model": model,
        "endpoint": endpoint,
        "scorecard": scorecard.model_dump(mode="json"),
        "agent": {
            "actions": agent.action_counter,
            "levels_completed": agent.levels_completed,
            "brain_metrics": agent.brain.metrics(),
        },
        "kaggle_compatible": False,
        "kaggle_limitation": (
            "The current offspring depends on an external local llama.cpp "
            "process and model weight not included in the submission overlay."
        ),
        "claim_boundary": (
            "Experimental local hybrid comparison; not a symbolic candidate "
            "and not a Kaggle score."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("game")
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--recordings-dir", type=Path, required=True)
    parser.add_argument("--stream-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:18092"
    )
    parser.add_argument(
        "--model", default="google_gemma-4-E2B-it-Q4_K_M.gguf"
    )
    parser.add_argument("--action-budget", type=int, default=40)
    args = parser.parse_args()
    payload = run_game(
        game=args.game,
        environments_dir=args.environments_dir,
        recordings_dir=args.recordings_dir,
        stream_dir=args.stream_dir,
        endpoint=args.endpoint,
        model=args.model,
        action_budget=args.action_budget,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
