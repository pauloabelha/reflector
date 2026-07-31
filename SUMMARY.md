# Reflector current summary

Last updated: 2026-07-30

## Best verified result

Reflector's best complete, process-isolated 25-game public-development result is
**16.355448098096414 / 100**.

- Candidate: `candidate-40b2dad207199755` (`v82f`)
- Frozen source: `79a872ca0ed3fa40a98b185b3217e304d81dc68f`
- Coverage: 25/25 games
- Levels: **39/183**
- Games with progress: **13/25**
- Complete games: **3/25**
- Actions: **9,185**
- Report:
  [`reports/official-isolated-v82f-dihedral-bridge-400.json`](reports/official-isolated-v82f-dihedral-bridge-400.json)
- Candidate:
  [`candidates/v82f-dihedral-bridge-composition-400.json`](candidates/v82f-dihedral-bridge-composition-400.json)
- Report SHA-256:
  `a29e963af1dd3af31d6e7cf040b8d28e7006e9bbf1e5007ed02e32e714674f56`

Relative to the clean v74 restart at **14.450686193334509**, v82f changes only
`tr87`: it advances from 0/6 to **4/6**, scoring 47.6190476190 on that game.
All other game outcomes are exactly preserved. The aggregate gain is
**+1.904761904761905 points**.

## New accepted mechanism: demonstrated analogy algebra

V82f learns transformations from visible input/output demonstrations rather
than from a game-specific route. Its abstraction grew through four levels:

1. glyph class to glyph class under the eight square symmetries;
2. glyph class to variable-length output sequence;
3. sequence-to-sequence substitution;
4. relational composition through a latent bridge color.

On `tr87`, the frozen agent reproduced 4/6 twice with level actions
`[56, 45, 44, 38, 217, 0]`. The complete quality gate passed with 437 tests,
3 skips, Ruff, and mypy.

## Current development result

V84 adds a distinct relational mechanism: colored landmark centers constrain
where switchable movable shapes must be translated. A black-box derivation
solved `re86` level 1 in exactly 20 actions. The first frozen autonomous run
also advanced level 1, in 34 actions:

- target score: **1.6243752402921952**
- target levels: **1/8**
- controls grounded: four translations and one control-transfer action
- conflicts/quarantines: zero
- report:
  [`reports/experimental-v84-constellation-re86-r1-400.json`](reports/experimental-v84-constellation-re86-r1-400.json)

Level 2 falsified the plus-only version of the perceptual rule. It contains a
plus, an X, and a diamond. The stronger ongoing hypothesis is generic subset
embedding: translate each mover so all same-colored landmark centers lie on
its translated pixel mask. V84 is therefore promising but **not promoted** and
does not change the verified 25-game score yet.

## Rejected branch

V83 tested distance-decreasing replay on an inferred one-dimensional track.
It was behaviorally active on `sc25` but remained 0/6 in 400 actions. The
endpoint was not the task goal. The mechanism is retained exact-off as a
negative result and is disabled in v82f/v84 candidates.

## Immediate objective

The verified score remains **16.3554480981 / 100**. Reaching 20 requires at
least **+3.6445519019** aggregate points. The current priority is to validate
generic shape-to-landmark subset embedding across changed `re86` layouts,
repeat any gain deterministically, run the preservation/full-suite gate, and
only then submit the exact accepted package to Kaggle using `KAGGLE.md`.
