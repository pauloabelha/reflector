# v1.4 result

`INVALID` by the frozen hard gate.

The fresh real-ARC control arm ran 48 actions without completing `ar25` level 1
and replayed exactly. The shared arm completed its first live Qwen call, then
the request builder refused to construct turn two because a prospective
environment-evidence payload exposed the key `action_id`. No leaking request
was sent. This is an interface/configuration invalidity, not evidence for or
against the cognitive hypothesis.

The exact offending path was:

`sparse_cut.objects[*].payload.prospective.action_id`

The outer action ledger remains authoritative; Qwen needs only the already
linked opaque intervention reference. The correction must therefore remove
that redundant raw field from the epistemic graph, under a new version.
