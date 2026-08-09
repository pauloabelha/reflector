# Progress-seeking live goal reconstruction v3

v1/v2 showed that the 4B semantic worker can identify the relevant controlled
entity, repeated class, and compatible region but uses uncertainty to abstain.
v3 tests a generic cognitive-drive rule:

> When the workspace exposes at least one grounded, measurable, nonterminal
> opportunity with a cheap intervention path, uncertainty requires a proposal
> and test; it does not justify abstention.

The workspace now reports, for every capacity hypothesis, `current_inside_count`
and `outside_count`, explicitly distinguishing a candidate role population from
current contents. These are exact geometric observations, not goal support.
When any outside count is positive, the response grammar requires one
support-zero hypothesis. If no measurable opportunity exists, null remains
allowed.

Everything else is inherited: six equal goal families, direct visual frame,
opaque interventions, no action meanings/sequence, environment-only support,
same controller and <=40 completion gate. The reasoning budget is reduced to
2,048 inside a 3,072-token completion reserve to discourage repetitive analysis
while retaining ample structured-output space.
