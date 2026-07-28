# Reflector validation protocol v8

Status: runner and protocol frozen after a passing development run;
confirmation seeds have not been executed.

V8 tests the narrow claim that a represented language-invention mechanism can
record falsifiable trials, distinguish insufficient from sufficient evidence,
earn its own complexity, revise itself, license a compositional operator, and
cause a held-out representational change. It does not test arbitrary language
invention, source-code evolution, psychological metareflection, task-score
improvement, or ARC-AGI-3 generalization.

## Identification strategy

Each paired seed constructs one strong cyclic vocabulary from the same
`SchemaStore` for both causal variants. Object names, action ID, context atoms,
predicate order, repetitions, and the held-out object identity are generated
from the seed. The semantic rotation magnitudes remain 90, 180, and 270
degrees because those are the typed source language under test.

The first reflection occurs after evidence for only one rotation predicate.
This must produce a rejected proposal with reason
`insufficient-distinct-predicates` and no operator. More evidence is then added
for all three predicates. A second reflection evaluates the accumulated
history.

The causal variants are:

- `language_meta_reflection`: the ordinary shared `AbstractionStore`;
- `no_language_meta_reflection`: the identical store and schemas with only
  `enable_language_meta_reflection=False`.

The ablation retains schema-family and concept-type reflection. It removes
only language-mechanism proposals and their products.

## Independent controls

Three controls are mandatory for every seed:

1. **Weak evidence:** only two distinct rotation predicates are observed, even
   with high support. A proposal may be recorded but no operator may be
   accepted.
2. **Non-cyclic vocabulary:** the same counts, actions, contexts, and object
   identities use non-rotation event predicates. No cyclic-language proposal
   or operator may appear.
3. **Independent oracle:** a validation-only calculation, not imported from
   `AbstractionStore`, checks the frozen requirements of three distinct source
   predicates, total support of at least four, positive operator description
   savings, and positive mechanism utility after the separately specified
   symbolic-token charge.

The oracle computes:

```text
operator_raw = Σ len(predicate) × support(predicate)
operator_complexity =
    len("orientation_delta(object,k)")
  + len("k in Z4; compose(a,b)=(a+b) mod 4")
operator_compiled = operator_complexity + 3 × total_support
operator_utility = operator_raw − operator_compiled

mechanism_complexity =
    strategy hyphen tokens
  + input-form underscore tokens
  + output-form underscore tokens
  + required-distinct threshold
  + minimum-support threshold
  + 8
mechanism_utility = operator_utility − mechanism_complexity
```

The oracle must predict acceptance for every strong history and rejection for
every weak history before inspecting the agent structures.

## Held-out intervention

After induction, neither variant learns from the held-out transition. Both are
given the same new object identity and a concrete `rotated_90` event.

- The enabled descendant must transform it to
  `orientation_delta(held_out_object,1)`.
- The ablation must preserve the concrete `rotated_90` event byte-for-byte.

This is a causal representational intervention. It is not an alternate
environment rollout and carries no score or action-efficiency claim.

## Provenance and leakage checks

For every enabled run:

- the accepted operator must name the exact mechanism revision that proposed
  it;
- that mechanism revision must descend from the initial inducer;
- its proposal list must contain both the early rejected trial and the
  accepted trial;
- its evidence must resolve to proposal or schema IDs in the same run;
- the language version must name the later mechanism revision that retained
  the operator;
- dependency-graph `invented_by`, `evaluated`, `retains`, and `licensed_by`
  edges must have valid endpoints;
- repeated reflection over unchanged evidence must not alter operator
  provenance, create another revision, or create another proposal.

No held-out object identity or held-out transition may occur in induction
evidence.

## Split and execution discipline

Development uses seeds 0–29. Confirmation uses seeds
210,000–210,029.

The confirmation command may be executed once only after:

1. this protocol is committed;
2. the runner, independent oracle, output schema, criteria, negative controls,
   determinism test, and command are committed;
3. development results pass;
4. Ruff, mypy, the full Python suite, frontend build, Kaggle smoke test, and
   Kaggle export pass;
5. the implementation commit is recorded in this document without changing
   criteria or confirmation seeds.

The canonical command will be:

```bash
.venv/bin/reflector validate --suite v8 \
  --seed-start 210000 --seeds 30 \
  --output validation-v8-holdout.json
```

The output must embed a SHA-256 over canonical JSON before the hash field. The
archived file hash must also be recorded after the single run.

The runner, oracle, controls, criteria, and output schema were frozen in commit
`19dda26`. Development seeds 0–29 passed all fourteen criteria. An immediate
second execution reproduced the report byte-for-byte. The canonical
development report is `validation-v8-development.json`, with file SHA-256
`a56eec45d98bf7c47c69ca53cc0794cbf99f81584e007bca595210a14b4572cf`
and embedded result SHA-256
`8b514ac3ddb890e355802b71d27d2008686ec5d8d0013dc58d84b0a7981d1739`.

## Preregistered support criteria

All fourteen criteria must pass:

1. independent oracle accepts every strong history;
2. independent oracle rejects every weak history;
3. paired enabled and ablated histories have identical canonical evidence
   hashes;
4. every enabled history records an early rejected proposal;
5. every enabled strong history constructs exactly one orientation operator;
6. every enabled strong history produces a positive-utility validated
   mechanism revision;
7. every ablated history produces no language proposals or operators;
8. every weak history produces no accepted operator;
9. every non-cyclic control produces no language proposal or operator;
10. every enabled held-out transition is normalized correctly;
11. every ablated held-out transition remains unchanged;
12. all provenance and dependency endpoints are valid;
13. no held-out identity leaks into induction evidence;
14. rerunning reflection over unchanged evidence is structurally idempotent.

Passing supports only the bounded causal mechanism claim stated above.

## Rejection and interpretation

Any failed criterion yields `not_supported`; no partial aggregate may override
it. If the runner or oracle changes after confirmation is viewed, a new version
and new untouched seed range are required. A pass must be described as
synthetic structural evidence, never as an ARC score, general intelligence,
general language invention, or prize readiness.
