# Abstraction firewall

The deployed runtime is standard-library Python, LLM-free, neural-free, and
offline. A schema is accepted only when its entire canonical representation is
inspectable and contains no executable code outside the audited primitive
registry.

Rejected material includes game or level identifiers, exact full-frame hashes,
single-frame action scripts, future observations, evaluation-only fields,
model/network calls, hidden semantic labels, and callable payloads. Generic
relational names are allowed; privileged nouns such as key, door, enemy,
portal, gravity, and inventory cannot enter S0.

Every primitive proposal must state that it is task-general, does not encode a
semantic game abstraction, cannot solve a level by itself, is necessary for
language interpretation, and has counted complexity. It is also compared with
the existing registry closure before coordinator acceptance.

Blind execution admits only observation data, temporal history, progress/state
signals actually exposed by the runtime, and current legal action identifiers.
Traces are direct structured execution events, never retrospective generated
explanations.

