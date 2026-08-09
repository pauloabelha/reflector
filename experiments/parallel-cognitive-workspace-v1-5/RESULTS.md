# v1.5 result

`INVALID`, with a useful partial causal result.

The action-blind evidence correction worked. A live Qwen proposal was grounded
into three R2 alternatives, R2 selected a genuinely discriminating prospective
probe, and the environment directly matched all three committed one-step
predictions. The run then stopped on a controller/witness status merge bug
before that evidence could be sent back to Qwen. Therefore v1.5 establishes
the proposal→grounding→active-probe→exact-evidence prefix, but cannot test
Qwen revision or downstream control.
