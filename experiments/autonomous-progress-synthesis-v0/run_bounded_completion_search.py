"""Game-blind observed-state completion search for development evaluation.

This is the system's last-resort curiosity drive: when no semantic capability
can act, it searches a bounded graph whose nodes are *observed* world states
and whose edges are currently legal opaque interventions.  It knows no game
identity, action meaning, target geometry, or solution trace.  Environment
completion is the only goal test.

Planning interactions are reported honestly.  They are not hidden behind the
short factual plan, because a useful Kaggle mechanism must eventually make
both numbers small.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ART=HERE/"artifacts"/"bounded-completion-search-development"
sys.path.insert(0,str(HERE))

import editable_topology_capability as CAP
import run_broad_nonregression as BROAD


def _write(path:pathlib.Path,document:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(document,indent=2,sort_keys=True)+"\n")
    temporary.replace(path)


def _complex_actions(environment:Any,observation:Any)->tuple[int,...]:
    available={int(getattr(row,"value",row)) for row in getattr(observation,"available_actions",())}
    return tuple(sorted(
        int(getattr(row,"value",row)) for row in getattr(environment,"action_space",())
        if int(getattr(row,"value",row)) in available
        and callable(getattr(row,"is_complex",None)) and row.is_complex()
    ))


def run(game:str,*,max_depth:int=16,max_expansions:int=2_000,max_points:int=8)->dict[str,Any]:
    root=ART/game
    arcade,environment=BROAD.BASE.open_environment(BROAD.ROOT/"environment_files",root/"planning",game)
    planning_interactions=0
    prefix_evaluations=0
    try:
        initial=environment.observation_space or environment.reset()
        initial_record=BROAD.BASE.observation_record(initial)
        initial_grid=BROAD.BASE.observation_grid(initial)
        simple=BROAD.BASE.simple_legal_actions(environment,initial)
        parameterized=_complex_actions(environment,initial)
        capability=CAP.compile_capability(
            initial_grid,simple_actions=simple,parameterized_actions=parameterized,
            max_points=max_points,max_depth=max_depth,max_expansions=max_expansions,
        )
        _write(root/"CHECKPOINT.json",{
            "status":"searching","game":game,"initial_digest":initial_record["digest"],
            "max_depth":max_depth,"max_expansions":max_expansions,"max_points":max_points,
            "candidate_id":capability.candidate_id,"binding_id":capability.binding_id,
        })

        def observe(prefix):
            nonlocal planning_interactions,prefix_evaluations
            observation=environment.reset();prefix_evaluations+=1
            for command in prefix:
                observation=BROAD.BASE.execute_action(
                    environment,game,command.action_id,command.payload(),"bounded-completion-search",
                )
                planning_interactions+=1
            record=BROAD.BASE.observation_record(observation)
            grid=BROAD.BASE.observation_grid(observation) if record["state"].upper().rsplit(".",1)[-1] not in {"GAME_OVER","WIN"} or record["levels_completed"]>=1 else ()
            if prefix_evaluations%100==0:
                _write(root/"CHECKPOINT.json",{
                    "status":"searching","game":game,"initial_digest":initial_record["digest"],
                    "prefix_evaluations":prefix_evaluations,"planning_interactions":planning_interactions,
                    "latest_depth":len(prefix),"max_depth":max_depth,"max_expansions":max_expansions,
                })
            return {"record":record,"grid":grid}

        def interventions(state):
            grid=state["grid"]
            if not grid:return ()
            situated=CAP.compile_capability(
                grid,simple_actions=simple,parameterized_actions=parameterized,
                max_points=max_points,max_depth=max_depth,max_expansions=max_expansions,
            )
            return situated.interventions

        plan=CAP.plan(
            capability,observe_prefix=observe,
            state_key=lambda state:state["record"]["frame_sha256"],
            completed=lambda state:int(state["record"]["levels_completed"])>=1,
            viable=lambda state:str(state["record"]["state"]).upper().rsplit(".",1)[-1] not in {"GAME_OVER","WIN"},
            interventions_for_state=interventions,
        )
    finally:
        arcade.close_scorecard()

    factual_arcade,factual_environment=BROAD.BASE.open_environment(BROAD.ROOT/"environment_files",root/"factual",game)
    history=[]
    try:
        observation=factual_environment.observation_space or factual_environment.reset()
        for command in plan.commands:
            before=BROAD.BASE.observation_record(observation)
            observation=BROAD.BASE.execute_action(factual_environment,game,command.action_id,command.payload(),"bounded-completion-plan")
            after=BROAD.BASE.observation_record(observation)
            history.append({"action":command.action_id,"data":command.payload(),"before":before["digest"],"after":after["digest"],"intervention_ref":command.token})
        final=BROAD.BASE.observation_record(observation)
    finally:
        factual_arcade.close_scorecard()

    replay_arcade,replay_environment=BROAD.BASE.open_environment(BROAD.ROOT/"environment_files",root/"replay",game)
    exact=True
    try:
        observation=replay_environment.observation_space or replay_environment.reset()
        for row in history:
            observation=BROAD.BASE.execute_action(replay_environment,game,row["action"],row["data"],"bounded-completion-replay")
            exact=exact and BROAD.BASE.observation_record(observation)["digest"]==row["after"]
    finally:
        replay_arcade.close_scorecard()
    result={
        "protocol":"bounded-observed-state-completion-search-v0","development_only":True,
        "game":game,"goal_ast":capability.goal_ast,"empirical_support":0,
        "planning_interactions":planning_interactions,"prefix_evaluations":prefix_evaluations,
        "expanded":plan.expanded,"observed_state_count":plan.observed_state_count,
        "factual_actions":len(history),"levels_completed":final["levels_completed"],
        "exact_replay":exact,"actions":[{"action":row["action"],"data":row["data"]} for row in history],
    }
    _write(root/"RESULT.json",result);_write(root/"CHECKPOINT.json",{"status":"complete",**result})
    return result


def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--game",required=True)
    parser.add_argument("--max-depth",type=int,default=16);parser.add_argument("--max-expansions",type=int,default=2_000)
    parser.add_argument("--max-points",type=int,default=8);args=parser.parse_args()
    try:result=run(args.game,max_depth=args.max_depth,max_expansions=args.max_expansions,max_points=args.max_points)
    except Exception as error:
        result={"protocol":"bounded-observed-state-completion-search-v0","development_only":True,"game":args.game,"status":"failed","error":f"{type(error).__name__}: {error}"}
        _write(ART/args.game/"RESULT.json",result);_write(ART/args.game/"CHECKPOINT.json",result);print(json.dumps(result,indent=2,sort_keys=True));return 1
    print(json.dumps(result,indent=2,sort_keys=True));return 0 if result["levels_completed"]>=1 and result["exact_replay"] else 1


if __name__=="__main__":raise SystemExit(main())
