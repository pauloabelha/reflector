# Reflector II 2.2 Agent Arcade

R2.2 is the production, model-neutral successor to the frozen R2.1 experiment.
Its controller, Agent Arcade, model transport, and frozen runtime closure live
under `arcade/r2`; no production import resolves through `experiments/`.

The semantic model proposes bounded schemas and explanations. R2 still owns
grounding, action selection, authority, evidence, settlement, and reusable
schema promotion. Changing a provider or model never changes that boundary.

## Shared model scratchpad

The workspace carries one canonical `model_scratchpad` object:

```json
{
  "explanation": "...",
  "goal": "...",
  "expectation": "...",
  "notes": "..."
}
```

The object is stored in the durable working note, shown directly by Agent
Arcade, and passed without field renaming or presentation-derived reconstruction
to both ordinary semantic calls and deep explanation-consolidation calls. The
model must rewrite the same exact four-field shape. Compatibility prose used by
the inherited compiler is derived only from `notes`; it is not a second model
scratchpad.

Every settled observation makes a semantic revision due. R2 waits for that
revision before the next external action, so the model always receives the
latest epistemic delta and exact prior scratchpad. The resulting object is
accepted only for the evidence basis it read; a stale reply cannot replace the
workspace scratchpad. Representation metadata such as compressed ledger rows
is removed from semantic vocabulary and rejected if copied into model state.

## Local Qwen

The default profile preserves the resident OpenAI-compatible Qwen service:

```bash
python -m arcade.r2 --arcade --game ar25
```

## OpenAI models

Load the existing key without copying it into this repository, then select a
profile and an exact model ID:

```bash
set -a
source ~/inhambu/.env
set +a

python -m arcade.r2 --arcade --game ar25 \
  --model-profile openai-gpt-5.6 \
  --model gpt-5.6-terra
```

The browser picker deliberately offers only **Qwen (local)** and **GPT-5.6
Luna**. Each choice loads server-owned context, output, frontier, and reasoning
defaults. The selection is validated before a run starts, frozen for that run,
and restored after it ends. Arbitrary model IDs and explicit budget sweeps stay
available through the CLI and Kaggle runner, not the browser.

The known GPT-5.6 profile configures its 1,050,000-token context, 8,192-token
ordinary output budget, 16,384-token consolidation output budget, 12,000-token
R2 frontier, medium ordinary reasoning, and high consolidation reasoning.
The OpenAI Responses input-token endpoint counts the exact text, image, message,
and JSON-schema input before every admitted request. Counts are cached by exact
canonical payload. A request is never sent when prompt plus output reserve does
not fit.

Use `openai-custom` for another Responses model. Unknown limits are never
guessed; all four budget dimensions are required:

```bash
python -m arcade.r2 --arcade --game ar25 \
  --model-profile openai-custom \
  --model MODEL_ID \
  --model-context-window-tokens CONTEXT \
  --model-max-tokens ORDINARY_OUTPUT \
  --model-consolidation-max-tokens DEEP_OUTPUT \
  --model-frontier-token-budget FRONTIER
```

Add `--model-reasoning-effort` and
`--model-consolidation-reasoning-effort` only when that model supports those
parameters. R2 requires image input and strict JSON-schema output, so a model
without either capability is intentionally rejected by the provider rather
than silently routed through a weaker contract.

The API key value is read only from the configured environment variable at
request time. Manifests and results record the provider, API, exact model ID,
profile, budgets, reasoning settings, timeout, and retry policy, but never the
credential. Transient requests use a stable idempotency key and bounded retry;
permanent API and schema failures fail closed without model authority.

## Kaggle ARC-AGI-3 breadth runs

Kaggle uses the same R2.2 runtime and the same model flags:

```bash
python -m arcade.r2.kaggle \
  --global-seconds 27300 \
  --per-run-seconds 900 \
  --model-profile openai-gpt-5.6 \
  --model gpt-5.6-terra
```

Each worker inherits the resolved environment, then records the same public
model metadata in its result. The breadth manifest freezes the entire
production `arcade/r2` source closure before launching the first game.

## Entrypoints

After installation, the equivalent commands are:

```bash
reflector2-agent-arcade --arcade --game ar25
reflector2-r2-kaggle --list-games
```
