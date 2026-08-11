# Experiment insights

This file is append-only. Environment evidence, recorded data, computation, and
inference are never conflated.

## IN-000 — The prior decisive run did not engage its treatment

- **Source:** `RECORDED_DATA`
- **Observation:** Arm C produced a code value but selected verbal mode, so the
  sandbox did not execute it. B and C both abstained at action zero.
- **Interpretation:** the prior run established authority isolation but cannot
  identify the effect of code-mediated computation.
- **Affected explanation:** “Python availability does not help this Executor”
  remains unsupported rather than confirmed.
- **Confidence:** high
- **Falsifier:** a trace showing executed Python causally cited by the selected
  C proposal in that run
- **Control consequence:** C treatment compliance is now a hard causal gate.

## IN-001 — Empty initial state is a poor test of history computation

- **Source:** `INFERENCE` from prior artifacts and the Kaggle insight corpus
- **Observation:** the prior B/C calls occurred before any environment action,
  while the hypothesized advantage is programmatic analysis of accumulated
  transitions.
- **Interpretation:** invoking C at action zero deprived it of the main substrate
  it was intended to exploit.
- **Confidence:** high
- **Falsifier:** a preregistered mechanism by which empty-state computation is
  the intended treatment target
- **Control consequence:** the new comparison begins at an exact prefix with at
  least 24 committed transitions.

## IN-002 — Raw disagreement must be control relevant

- **Source:** `INFERENCE`
- **Observation:** an unsupported minority explanation can disagree with every
  other explanation without making a real action valuable.
- **Interpretation:** disagreement is useful only when credible alternatives
  predict different observations that would change later control.
- **Confidence:** medium-high
- **Falsifier:** evidence that unweighted disagreement consistently improves
  action efficiency under matched risk
- **Control consequence:** Executor reports decision relevance, progress, option
  value, risk, and redundancy separately.

## IN-003 — Lossless history and prompt context are different products

- **Source:** `COMPUTATION`
- **Observation:** the exact decision-25 snapshot is approximately 4.19 MB and
  correctly exceeded the inherited 1.5 MB durable-snapshot limit.
- **Interpretation:** a lossless computational substrate cannot also be treated
  as the direct model prompt. The model needs a compact, hash-auditable view,
  while bounded code must retain read-only access to the full snapshot.
- **Confidence:** high
- **Falsifier:** a lossless encoding of the same graph/history below the compact
  prompt bound without deleting queryable content
- **Control consequence:** separate durable-snapshot and model-view bounds; do
  not solve context pressure by hiding evidence from C's computation.

## IN-004 — Code availability is not code usability for a small model

- **Source:** `RECORDED_DATA`
- **Observation:** with Python mode mandatory, Qwen3-VL-4B generated a valid
  opening but filled one code string with repetitive natural-language comments
  until the 3,072-token completion limit, leaving invalid JSON. No code ran.
- **Interpretation:** treatment delivery requires a syntax-level brevity
  affordance, not merely a tool description. This is model/interface compliance,
  not evidence about the value of the intended computation.
- **Confidence:** high
- **Falsifier:** a complete structured response in the preserved raw completion
- **Control consequence:** bound each physical code line, forbid comments and
  helper definitions, and request a short generic history query. Because this
  changes qualification, rerun B as well as C before any branch comparison.

## IN-005 — Every generative string needs a causal resource bound

- **Source:** `RECORDED_DATA`
- **Observation:** after bounding code lines and analysis findings, Arm B used
  nearly its entire remaining context on one `computed_reason` value and ended
  with an unterminated JSON string.
- **Interpretation:** structured decoding constrains shape but does not by
  itself constrain deliberation cost. A single unbounded leaf can defeat the
  entire proposal contract and prevent an otherwise legal experiment.
- **Confidence:** high
- **Falsifier:** a complete proposal in the preserved raw response
- **Control consequence:** every free-text leaf in an action-authority message
  needs a preregistered maximum length, or should be replaced by typed references
  to prior findings.

## IN-006 — A tool call must cross syntax, execution, and provenance gates

- **Source:** `RECORDED_DATA`
- **Observation:** Arm C selected Python mode and emitted short code, but all
  three lines were unterminated string assignments. The sandbox reported a
  syntax error, returned no structured value, and no action was proposed.
- **Interpretation:** “the model chose Python” is weaker than treatment delivery.
  The useful causal unit is successful computation whose returned finding is
  cited by the selected action.
- **Confidence:** high
- **Falsifier:** a successful sandbox record and computation-citing C proposal
  for this attempt
- **Control consequence:** preserve the existing hard treatment gate. A future
  interface may use a small typed computation AST or validated repair pass, but
  that interface must be frozen and tested symmetrically before the comparison.

## IN-007 — Append-only science requires immutable run namespaces

- **Source:** `AUDIT`
- **Observation:** rerunning into `artifacts/arm-b` and `artifacts/arm-c` left
  earlier `result.json` files beside later `failure.json` files.
- **Interpretation:** the top-level summary is internally correct, but mutable
  per-arm directories make manual inspection vulnerable to stale-success bias.
- **Confidence:** high
- **Falsifier:** proof that every per-arm file is atomically cleared or namespaced
  before each attempt
- **Control consequence:** future runs must write to content-addressed or
  monotonically numbered attempt directories and publish a single immutable
  pointer to the decisive attempt.

## IN-008 — Grammar membership and semantic validation should be separated

- **Source:** `COMPUTATION` and interface audit
- **Observation:** enumerating every visible workspace ID inside each JSON-schema
  leaf materially inflated the prompt even though the host already possessed
  the authoritative dependency set.
- **Interpretation:** the decoder grammar should enforce bounded shape; the
  arbiter should enforce state-dependent membership and liveness. Duplicating a
  large dynamic universe in the grammar consumes reasoning context without
  strengthening the authority boundary.
- **Confidence:** high
- **Falsifier:** a measured grammar-enum condition with equal prompt size and
  materially stronger invalid-reference rejection
- **Control consequence:** references use bounded strings in the grammar and
  exact snapshot membership checks after decoding and before computation/action.

## IN-009 — Removing an enum requires restoring its semantic affordance

- **Source:** `RECORDED_DATA`, immutable run 001
- **Observation:** both workers produced valid bounded JSON but used conceptual
  dependency names after the ID enum was removed from the decoder grammar.
- **Interpretation:** host-side validation is the right authority mechanism, but
  the model still needs a compact explicit vocabulary of admissible references.
- **Confidence:** high
- **Falsifier:** evidence that the prompt already supplied and explained the
  exact admissible IDs in run 001
- **Control consequence:** provide the ID catalogue once in task content, never
  replicate it in every schema leaf, and reject all nonmembers before Python or
  action authorization.

## IN-010 — Post-tool provenance has a different reference universe

- **Source:** `RECORDED_DATA`, immutable run 002
- **Observation:** C executed successfully, but its proposal cited the four
  pre-execution claims rather than the single host-recorded Python result.
- **Interpretation:** after a tool call, finding identities must be regenerated
  from actual results and explicitly exposed. A model cannot infer that the
  provenance universe narrowed from several planned findings to one executed
  return merely from a computation object.
- **Confidence:** high
- **Falsifier:** a cited executed finding in run 002
- **Control consequence:** construct `valid_finding_refs` after execution and
  constrain proposal references to that exact set.

## IN-011 — The verbal Executor is genuinely mapping-sensitive

- **Source:** `RECORDED_DATA`, model-in-the-loop coherent permutation control
- **Observation:** Arm B selected action 1 on the original packet and action 2
  after the complete 1↔2 action/effect relabeling.
- **Interpretation:** the verbal worker is not merely anchored to the literal
  action number; it responds equivariantly to the supplied history mapping.
- **Confidence:** high for this fixture
- **Falsifier:** a hidden inconsistency in the permutation transform or evidence
  that the two outputs came from different non-permuted packets
- **Control consequence:** retain the coherent permutation control as positive
  dependency-use evidence, separate from gameplay quality.

## IN-012 — Perturbation robustness is weaker than nominal compliance

- **Source:** `RECORDED_DATA`, model-in-the-loop controls
- **Observation:** both workers crossed the nominal decision boundary in run
  003, yet dependency deletion induced stale-ID citations, and C failed to
  engage reliably across control variants.
- **Interpretation:** a valid nominal trace does not imply robust provenance
  discipline. The host firewall is doing necessary scientific work; the 4B
  model/interface still has a meaningful compliance ceiling.
- **Confidence:** high
- **Falsifier:** successful deleted-dependency and permuted C traces under the
  frozen control manifest
- **Control consequence:** report nominal mechanism engagement and robustness
  controls separately; never weaken the validator to improve pass rate.

## IN-013 — Python added computation without adding policy leverage

- **Source:** `ENVIRONMENT_EVIDENCE` plus recorded Executor provenance, canonical
  run 005
- **Observation:** C successfully counted all 25 transitions and cited the
  result, yet selected the same action and reached the same successor as B. Its
  checkpoint was correct but assigned only 0.084 confidence versus B's 0.813.
- **Interpretation:** treatment delivery is proven, but the computation was too
  shallow and partly mixed with a hard-coded pattern string to change control.
  More tool calls would not by themselves solve this; the worker must discover
  a decision-relevant test.
- **Confidence:** high for this decision boundary
- **Falsifier:** a hidden difference between B/C predecessor state or successor
  branch, both excluded by the exact hashes
- **Control consequence:** freeze the negative v0. Do not expand primitives
  post hoc; test a stronger worker or preregistered generic computation
  representation as a separate intervention.
