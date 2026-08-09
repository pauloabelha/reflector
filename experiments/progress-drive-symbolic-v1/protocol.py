from __future__ import annotations

import json
from typing import Mapping

PROTOCOL = "grounded-symbolic-progress-v1"


def response_schema(workspace: Mapping[str, object]) -> dict:
    return {"type":"json_schema","json_schema":{"name":"symbolic_progress","strict":True,"schema":{
        "type":"object","additionalProperties":False,"required":["protocol","family","desired_outputs","rule"],
        "properties":{
            "protocol":{"const":PROTOCOL},
            "family":{"const":"transformation"},
            "desired_outputs":{"type":"array","minItems":workspace["slot_count"],"maxItems":workspace["slot_count"],"items":{"enum":workspace["allowed_output_ids"]}},
            "rule":{"type":"string","maxLength":300}
        }}}}


def request_payload(workspace, config, image_url):
    prompt = """You are the semantic induction worker in one shared epistemic workspace.
R2 has grounded rotation-invariant visual token IDs, demonstrated input-output pairs, a query sequence, and editable output slots. Every claim starts with support zero.
Infer the output sequence by applying only relations demonstrated in the examples. Do not invent token IDs, actions, colors, coordinates, or a route. Return a transformation proposal; R2 will validate the IDs and execute opaque edits, and only the environment can confirm it.

EPISTEMIC_WORKSPACE
""" + json.dumps(workspace, sort_keys=True, separators=(",",":"))
    return {"model":config["model"],"temperature":config["temperature"],"seed":config["seed"],"max_tokens":config["max_tokens"],"thinking_budget_tokens":config["thinking_budget_tokens"],"messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":image_url}}]}],"response_format":response_schema(workspace)}
