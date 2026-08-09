# Live progress-goal reconstruction v2

v1 was a valid abstention. This version makes exactly two generic repairs:

1. A placement-capacity hypothesis exists only when repeated member dimensions
   tile the candidate region on an integer lattice; equal area alone is not
   capacity.
2. Qwen receives a 3,072-token thinking budget within a 4,096-token completion
   reserve so its semantic comparison can finish.

The prompt, goal-family vocabulary, support-zero compiler, calibration prefix,
visual input, controller, 40-action completion gate, and empty-workspace rule
are otherwise inherited unchanged. No v1 reasoning or response enters the new
request. PASS/FAIL/INVALID semantics remain identical.
