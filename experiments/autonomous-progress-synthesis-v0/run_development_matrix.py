"""Source-blind development matrix for the synthesized-goal control loop."""
from __future__ import annotations
import importlib.util,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"development-matrix"
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
BASE=load("synthesis_matrix_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py")
SYN=load("synthesis_matrix_core",HERE/"progress_synthesis.py")
EXEC=load("synthesis_matrix_exec",HERE/"executor_registry.py")
FIELD=load("synthesis_matrix_field",HERE/"progress_field.py")

def complex_actions(env,obs):
    available={int(getattr(item,"value",item)) for item in getattr(obs,"available_actions",())};out=[]
    for transport in getattr(env,"action_space",()):
        action=int(getattr(transport,"value",transport));test=getattr(transport,"is_complex",None)
        if action in available and callable(test) and test():out.append(action)
    return tuple(sorted(out))

def terminal(record):return str(record["state"]).upper().rsplit(".",1)[-1] in {"GAME_OVER","WIN"} or record["levels_completed"]>=1

def run_game(game,*,artifact_root=ART,action_budget=64):
    root=pathlib.Path(artifact_root)/game;arcade,env=BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[]
    try:
        initial=env.observation_space or env.reset();initial_record=BASE.observation_record(initial);initial_grid=BASE.observation_grid(initial)
        candidates=SYN.synthesize(initial_grid);simple=BASE.simple_legal_actions(env,initial);complex_ids=complex_actions(env,initial)
        motion={};calibration=[]
        for action in simple:
            before=env.reset();before_grid=BASE.observation_grid(before);after=BASE.execute_action(env,game,action,{},"synthesis-calibration");after_grid=BASE.observation_grid(after)
            deltas=[SYN.infer_role_translation(candidate,before_grid,after_grid) for candidate in candidates]
            delta=next((item for item in deltas if item is not None and (item[0]==0)!=(item[1]==0)),None)
            if delta is not None:motion[delta]=action
            calibration.append({"opaque_action":action,"role_translation":delta,"changed_cells":sum(a!=b for ra,rb in zip(before_grid,after_grid) for a,b in zip(ra,rb))})
        release=tuple(row["opaque_action"] for row in calibration if row["role_translation"] is None)
        focus=proposal=None
        for candidate in sorted(candidates,key=lambda item:(-item.attention,item.candidate_id,item.binding_id)):
            try:
                proposal=EXEC.compile_execution(candidate,initial_grid,motion_actions=motion,parameterized_actions=complex_ids,release_actions=release)
                focus=candidate;break
            except Exception:continue
        if focus is None or proposal is None:raise RuntimeError("no synthesized goal has an executable grounding")
        obs=env.reset();rounds=[];field=FIELD.make_state([focus]);field_events=[]
        for _ in range(3):
            for command in proposal.commands:
                if len(history)>=action_budget:break
                before=BASE.observation_record(obs);before_grid=BASE.observation_grid(obs)
                try:before_candidates=[row for row in SYN.synthesize(before_grid) if row.candidate_id==focus.candidate_id]
                except SYN.SynthesisError:before_candidates=[]
                before_candidate=min(before_candidates,key=lambda row:(-row.attention,row.binding_id),default=focus);before_value=SYN.evaluate(before_candidate,before_grid)
                obs=BASE.execute_action(env,game,command.opaque_action,dict(command.data),"synthesized-progress-control");after=BASE.observation_record(obs);after_grid=BASE.observation_grid(obs)
                try:after_candidates=[row for row in SYN.synthesize(after_grid) if row.candidate_id==focus.candidate_id]
                except SYN.SynthesisError:after_candidates=[]
                after_candidate=min(after_candidates,key=lambda row:(-row.attention,row.binding_id),default=None);after_value=None if after_candidate is None else SYN.evaluate(after_candidate,after_grid)
                if isinstance(before_value,int) and isinstance(after_value,int):
                    transition_id=f"transition:{len(history)}:"+after["digest"][:20]
                    field=FIELD.observe(field,candidate_id=focus.candidate_id,binding_id=focus.binding_id,opaque_action=command.opaque_action,before=before_value,after=after_value,direct=True,transition_id=transition_id)
                    field_events.append({"transition_id":transition_id,"before":before_value,"after":after_value,"support":field.candidates[0].support})
                history.append({"action":command.opaque_action,"data":dict(command.data),"before":before,"after":after,"role":command.role})
                if terminal(after):break
            rounds.append({"potential":proposal.potential_type,"expected_before":proposal.expected_before,"expected_after":proposal.expected_after,"complete":proposal.complete})
            if terminal(BASE.observation_record(obs)) or proposal.complete or len(history)>=action_budget:break
            grid=BASE.observation_grid(obs);current=next((candidate for candidate in SYN.synthesize(grid) if candidate.candidate_id==focus.candidate_id),focus)
            proposal=EXEC.compile_execution(current,grid,motion_actions=motion,parameterized_actions=complex_ids,release_actions=release,grounding_memory=proposal.grounding_memory)
        final=BASE.observation_record(obs)
    finally:arcade.close_scorecard()
    replay_arcade,replay_env=BASE.open_environment(ROOT/"environment_files",root/"replay",game)
    try:
        replay=replay_env.observation_space or replay_env.reset();_=BASE.execute_action(replay_env,game,simple[0],{},"replay-warmup");replay=replay_env.reset();exact=True
        for row in history:
            replay=BASE.execute_action(replay_env,game,row["action"],row["data"],"exact-replay")
            exact=exact and BASE.observation_record(replay)["digest"]==row["after"]["digest"]
        exact=exact and BASE.observation_record(replay)["levels_completed"]==final["levels_completed"]
    finally:replay_arcade.close_scorecard()
    return {"game":game,"initial_digest":initial_record["digest"],"candidate_count":len(candidates),"selected_ast":focus.ast,"selected_support":focus.support,"final_evidence_support":field.candidates[0].support,"field_events":field_events,"workspace":FIELD.workspace_document(field),"calibration":calibration,"planning_rounds":rounds,"actions":[{"opaque_action":row["action"],"data":row["data"],"role":row["role"]} for row in history],"factual_actions":len(history),"total_interactions":len(calibration)+len(history),"action_budget":action_budget,"levels_completed":final["levels_completed"],"exact_replay":exact,"final_digest":final["digest"]}

def main():
    results=[]
    for game in ("ka59","sp80","re86"):
        try:results.append(run_game(game))
        except Exception as error:results.append({"game":game,"error":f"{type(error).__name__}: {error}"})
    document={"protocol":"autonomous-progress-synthesis-development-matrix-v0","source_blind_runtime":True,"results":results}
    ART.mkdir(parents=True,exist_ok=True);(ART/"RESULT.json").write_text(json.dumps(document,indent=2,sort_keys=True)+"\n");print(json.dumps(document,indent=2));return 0 if all(row.get("levels_completed",0)>=1 and row.get("exact_replay") for row in results) else 1
if __name__=="__main__":raise SystemExit(main())
