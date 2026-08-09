# Frozen visual-progress cross-game gate v1

The metadata-only selector fixes `tr87-cd924810` before any frame or source is
opened.  Exclusions are `ar25`, `wa30`, `ls20`, and the earlier invalid `g50t`
attempt.  There is no substitution on launch or runtime failure.

Two fresh arms receive identical generic calibration and live Qwen workspace
turns.  `shared_cycle` continues the ordinary opaque-action cycle;
`shared_progress` adds only commit `5bfbf95`'s frozen visual progress field.
Both have 32 actions and must start from the same observation digest.  PASS
requires exact replay and either a level uniquely completed by progress or at
least 25 percent action saving.  Otherwise the valid result is FAIL.

Prior public-corpus census exposure means this is a fresh cross-game mechanism
test, not a pristine hidden-game claim.
