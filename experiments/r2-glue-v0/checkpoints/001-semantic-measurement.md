# Checkpoint 001: generic semantic measurement proposals

Time: 2026-08-12T02:48:30Z

## Predeclared capability

Permit the semantic model to propose why two grounded spatial roles might be
related without supplying code or fixing a verb's meaning in the prompt. R2
must compile only a bounded neutral expression and must leave unmeasurable
proposals non-authoritative.

## Implementation

`SemanticMeasureHypothesis` accepts exactly:

- left/right source: actor or target;
- feature: occupancy, boundary, enclosed negative space, or envelope negative
  space;
- comparison: symmetric difference, either directed difference, or overlap
  deficit;
- coordinate frame: scene or intrinsic;
- optional separation gap only in the scene frame.

Custom observable names must begin with `proposed_`. Empty selected features
return no measurement rather than a vacuous zero. Definitions are fingerprinted
into `GoalControlSignature`; two lexical verbs may share an exact construction,
but two constructions with the same name conflict and fail closed.

The prompt no longer says FIT must use `fit_residual`, that FIT normally moves a
particular residual, or that a lexical verb requires a particular potential.
Built-in verbs and observables remain explicitly labeled defeasible priors.

## Tests

- exact enclosed-negative-space extraction;
- gradient and zero terminal for a synthetic spatial-set match;
- empty-feature fail-open behavior;
- invalid protocol, feature, operator, and coordinate-frame rejection;
- compilation without support/control promotion;
- missing-definition and same-name conflict rejection;
- verb label independence from potential and direction;
- measurement definition included in structural control identity;
- source leakage guard for the new production module.

Focused result: 135 passed.  
Full result: 233 passed, 1 pre-existing missing-artifact failure out of 234.

## Evidence boundary

This checkpoint establishes representational and control-path availability only.
It does not show that Qwen will make a useful abduction, that role grounding will
choose the intended entities, that a proposed residual predicts a real action,
or that any ARC level or score improves.
