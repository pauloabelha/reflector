# Conditional visual-route development gate v2

Fresh versioned repair of v1's measurement failure.  v1 stopped after seven
actions because the agent rotates when changing direction, so exact translated
pixel masks did not correspond.  v2 changes only correspondence: the unique
connected component with the calibrated color set, mass and bounding size is
tracked across rotations.  Route inference, Qwen contract, budgets, topology,
action opacity and PASS gate are unchanged.  No v1 state or response is reused.
