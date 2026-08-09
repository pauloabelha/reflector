"""Build a self-contained v164 + online capability-registry Kaggle candidate."""
from __future__ import annotations
import base64,hashlib,json,pathlib,re,zipfile
from io import BytesIO

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=pathlib.Path("/home/pauloabelha/reflector/submission/kaggle_v164")
OUTPUT=pathlib.Path("/home/pauloabelha/reflector/submission/kaggle_v169_online_registry")

FILES={
    HERE/"online_registry_controller.py":"r2_experiments/autonomous-progress-synthesis-v0/online_registry_controller.py",
    HERE/"deployment_capability_registry.py":"r2_experiments/autonomous-progress-synthesis-v0/deployment_capability_registry.py",
    HERE/"progress_synthesis.py":"r2_experiments/autonomous-progress-synthesis-v0/progress_synthesis.py",
    HERE/"compositional_dsl.py":"r2_experiments/autonomous-progress-synthesis-v0/compositional_dsl.py",
    HERE/"executor_registry.py":"r2_experiments/autonomous-progress-synthesis-v0/executor_registry.py",
    HERE/"gradient_executor.py":"r2_experiments/autonomous-progress-synthesis-v0/gradient_executor.py",
    HERE/"route_option.py":"r2_experiments/autonomous-progress-synthesis-v0/route_option.py",
    HERE.parent/"progress-drive-object-placement-v0/object_placement.py":"r2_experiments/progress-drive-object-placement-v0/object_placement.py",
    HERE.parent/"progress-drive-flow-routing-v0/flow_routing.py":"r2_experiments/progress-drive-flow-routing-v0/flow_routing.py",
    HERE.parent/"progress-goal-generic-calibration-v1/tracker.py":"r2_experiments/progress-goal-generic-calibration-v1/tracker.py",
    HERE.parent/"progress-drive-conditional-route-v0/conditional_route.py":"r2_experiments/progress-drive-conditional-route-v0/conditional_route.py",
}


def digest(value:bytes)->str:return hashlib.sha256(value).hexdigest()


def patched_agent(source:str)->str:
    marker="from reflector import Observation, SymbolicPolicy\n"
    injection='''import sys\n+CAPABILITY_ROOT = Path(__file__).resolve().parents[2] / "r2_experiments" / "autonomous-progress-synthesis-v0"\n+if str(CAPABILITY_ROOT) not in sys.path:\n+    sys.path.insert(0, str(CAPABILITY_ROOT))\n+from online_registry_controller import OnlineCapabilityController\n+\n+'''.replace("\n+","\n")
    source=source.replace(marker,injection+marker)
    source=source.replace(
        "        self.policy = SymbolicPolicy(deployed_config())\n",
        "        self.policy = SymbolicPolicy(deployed_config())\n        self.capability_controller = OnlineCapabilityController()\n        self._capability_level = 0\n",
        1,
    )
    needle="""        observation = self._observation(latest_frame)\n        decision = self.policy.choose_action(observation)\n"""
    replacement="""        observation = self._observation(latest_frame)\n        if observation.levels_completed > self._capability_level:\n            # A level is a new empirical world. Keep transferable code, but\n            # discard every situated binding, action model, and workspace fact.\n            self._capability_level = observation.levels_completed\n            self.capability_controller = OnlineCapabilityController()\n            self.policy = SymbolicPolicy(deployed_config())\n        prior_phase = self.capability_controller.phase\n        command = None\n        if observation.frame and observation.state not in self.policy.NEEDS_RESET:\n            command = self.capability_controller.decide(\n                observation.frame, observation.available_actions, state=observation.state\n            )\n        if (\n            prior_phase == \"resetting\"\n            and self.capability_controller.phase in {\"executing\", \"abstained\"}\n        ):\n            # Calibration transitions never contaminate the broad fallback.\n            self.policy = SymbolicPolicy(deployed_config())\n        if command is not None:\n            action = GameAction.from_id(command.action_id)\n            if command.data:\n                action.set_data(command.data_dict())\n            action.reasoning = {\n                \"policy\": AGENT_VERSION,\n                \"why\": command.reason,\n                \"capability\": self.capability_controller.report(),\n            }\n            return action\n        decision = self.policy.choose_action(observation)\n"""
    if needle not in source:raise RuntimeError("agent decision seam changed")
    return source.replace(needle,replacement)


def build()->tuple[pathlib.Path,pathlib.Path]:
    original=(SOURCE/"reflector-kaggle-overlay.zip").read_bytes();input_zip=zipfile.ZipFile(BytesIO(original))
    output=BytesIO()
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as archive:
        for name in input_zip.namelist():
            payload=input_zip.read(name)
            if name=="agents/templates/reflector_agent.py":payload=patched_agent(payload.decode()).encode()
            archive.writestr(name,payload)
        for source,name in FILES.items():archive.writestr(name,source.read_bytes())
    overlay=output.getvalue();OUTPUT.mkdir(parents=True,exist_ok=True)
    overlay_path=OUTPUT/"reflector-kaggle-overlay.zip";overlay_path.write_bytes(overlay)
    notebook=json.loads((SOURCE/"reflector-kaggle-submission.ipynb").read_text())
    cell="".join(notebook["cells"][2]["source"]);encoded=base64.b64encode(overlay).decode()
    cell,count=re.subn(r'base64\.b64decode\("[A-Za-z0-9+/=]+"\)',f'base64.b64decode("{encoded}")',cell,count=1)
    if count!=1:raise RuntimeError("embedded overlay seam changed")
    notebook["cells"][2]["source"]=cell.splitlines(keepends=True)
    notebook_path=OUTPUT/"reflector-kaggle-submission.ipynb";notebook_path.write_text(json.dumps(notebook,indent=1)+"\n")
    (OUTPUT/"candidate.json").write_bytes((SOURCE/"candidate.json").read_bytes())
    metadata=json.loads((SOURCE/"kernel-metadata.json").read_text())
    metadata["id"]="pauloabelha/reflector-arc-agi-3-v169-online-registry"
    metadata["title"]="Reflector ARC-AGI-3 v169 Online Registry"
    (OUTPUT/"kernel-metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    manifest={
        "protocol":"reflector-v169-online-capability-registry","parent":"kaggle_v164",
        "overlay_sha256":digest(overlay),"notebook_sha256":digest(notebook_path.read_bytes()),
        "mechanism_files":{name:digest(source.read_bytes()) for source,name in FILES.items()},
        "development_evidence":{
            "public_first_levels_completed":16,"public_games":25,
            "capability_led_games":["ar25","ka59","re86","sp80","tu93"],
            "claim":"consumed public development only; not hidden generalization evidence",
        },
    }
    (OUTPUT/"release-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return overlay_path,notebook_path


if __name__=="__main__":
    overlay,notebook=build();print(json.dumps({"overlay":str(overlay),"notebook":str(notebook),"overlay_sha256":digest(overlay.read_bytes())},indent=2))
