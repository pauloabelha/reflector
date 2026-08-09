"""Consumed-development test of live, evidence-bounded capability macros.

No game identity enters synthesis or arbitration.  The CLI game is harness
routing only.  R2 acts normally while opaque motion laws accumulate.  After a
generic stagnation gate, one exact capability may spend a bounded macro-probe
to its declared progress boundary.  Every command is causally committed into
R2, and the environment alone adjudicates the resulting potential change.
"""
from __future__ import annotations

import argparse,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import capability_registry as REG
import compositional_dsl as DSL
import online_compositional_options as ONLINE
import progress_synthesis as SYN
import run_broad_nonregression as R
from broad_policy_bridge import HybridDecision,SharedBroadPolicy
from transactional_broad_policy import TransactionalBroadPolicy
from reflector import MindConfig,SymbolicPolicy

ART=HERE/"artifacts/live-capability-hybrid"
MIN_CARDINAL_CALIBRATIONS=4
MAX_MACRO_COMMANDS=16
MAX_CONFIRMED_CONTROL_COMMANDS=32


def complex_actions(env,obs):
    available={int(getattr(row,"value",row)) for row in getattr(obs,"available_actions",())}
    return tuple(sorted(
        int(getattr(row,"value",row)) for row in getattr(env,"action_space",())
        if int(getattr(row,"value",row)) in available
        and callable(getattr(row,"is_complex",None)) and row.is_complex()
    ))


def current_value(candidate,grid):
    matches=[row for row in SYN.synthesize(grid) if row.candidate_id==candidate.candidate_id]
    values={SYN.evaluate(row,grid) for row in matches};values.discard(None)
    return next(iter(values)) if len(values)==1 else None


def tracked_value(proposal,grid):
    memory=proposal.grounding_memory
    if isinstance(memory,REG.exact.PlacementMemory):
        scene=REG.exact.PLACEMENT.track_item_scene(memory.reference_grid,grid,memory.initial_scene)
        return len(scene.items)
    return None


def commit_macro_command(tx,obs,command):
    fallback=tx.choose_action(R.symbolic(obs));data=tuple(command.data)
    decision=HybridDecision(
        command.opaque_action,data,"probe",fallback.action_id,
        tuple(sorted((str(k),int(v)) for k,v in fallback.data_dict().items())),
        None,"bounded-capability-progress-test",
    )
    tx.commit_decision(R.symbolic(obs),decision)
    return fallback


def run(game,limit=64):
    policy=SymbolicPolicy(MindConfig.from_dict(R.CANDIDATE["config"]));tx=TransactionalBroadPolicy(policy)
    controller=SharedBroadPolicy(tx,stagnation_threshold=24,max_option_probes=0,max_divergent_probes=0)
    arcade,env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"factual",game)
    obs=env.observation_space or env.reset();initial_grid=R.BASE.observation_grid(obs)
    legal=R.BASE.simple_legal_actions(env,obs);parameterized=complex_actions(env,obs)
    try:candidates=DSL.propose(initial_grid)
    except Exception:candidates=()
    inducer=ONLINE.OnlineCompositionalOptionInducer(initial_grid,legal_actions=legal,candidates=candidates)
    history=[];macro=None;attempted=False;reset_at=None;reset_digest=None
    try:
        while int(obs.levels_completed)<1 and len(history)<limit:
            grid=R.BASE.observation_grid(obs)
            if not attempted:
                motion=inducer.calibrated_motion_actions()
                if len(motion)<MIN_CARDINAL_CALIBRATIONS:
                    motion={}
                if motion:
                    restoration=inducer.restoration_actions()
                    if restoration is None:
                        motion={}
                    else:
                        for action in restoration:
                            if len(history)>=limit or int(obs.levels_completed)>=1:break
                            before_record=R.BASE.observation_record(obs)
                            command=REG.exact.Command(action,(),"restore-calibrated-role")
                            fallback=commit_macro_command(tx,obs,command)
                            obs=R.BASE.execute_action(env,game,action,{},"capability-calibration-restore")
                            after_record=R.BASE.observation_record(obs);transition_id=f"transition:{len(history)}:{after_record['digest'][:16]}"
                            inducer.observe_option_transition(opaque_action=action,after=R.BASE.observation_grid(obs),transition_id=transition_id,direct=True)
                            history.append({"action":action,"data":{},"mode":"calibration_restore","fallback_action":fallback.action_id,"before":before_record["digest"],"after":after_record["digest"],"role":"restore-calibrated-role"})
                        if inducer.restoration_actions()!=():motion={}
                        grid=R.BASE.observation_grid(obs)
                release=tuple(action for action in legal if action not in set(motion.values()))
                rows=REG.propose_calibrated(
                    grid,motion_actions=motion,
                    parameterized_actions=parameterized,release_actions=release,
                ) if motion else ()
                exact=[row for row in rows if row.capability.startswith("exact:")]
                if exact:
                    # Calibration may change latent attachment/selection state
                    # even when pixels return.  Keep only the directly learned
                    # opaque laws; reset every situated/controller cache before
                    # granting a capability its test.
                    reset_at=len(history);obs=env.reset();reset_digest=R.BASE.observation_record(obs)["digest"]
                    policy=SymbolicPolicy(MindConfig.from_dict(R.CANDIDATE["config"]));tx=TransactionalBroadPolicy(policy)
                    controller=SharedBroadPolicy(tx,stagnation_threshold=24,max_option_probes=0,max_divergent_probes=0)
                    grid=R.BASE.observation_grid(obs)
                    try:reset_candidates=DSL.propose(grid)
                    except Exception:reset_candidates=()
                    inducer=ONLINE.OnlineCompositionalOptionInducer(grid,legal_actions=legal,candidates=reset_candidates)
                    rows=REG.propose_calibrated(grid,motion_actions=motion,parameterized_actions=parameterized,release_actions=release)
                    exact=[row for row in rows if row.capability.startswith("exact:")]
                    if not exact:attempted=True;continue
                    selected=exact[0];proposal=selected.execution.proposal
                    commands=proposal.commands[:MAX_MACRO_COMMANDS]
                    attempted=True;before=current_value(selected.execution.candidate,grid)
                    macro={
                        "capability":selected.capability,"goal_ast":selected.goal_ast,
                        "candidate_id":selected.execution.candidate.candidate_id,
                        "support_before":0,"potential_before":before,
                        "planned_command_count":len(proposal.commands),
                        "executed_command_count":0,"phases":[],
                    }
                    first_signature=[(row.opaque_action,list(row.data),row.role) for row in proposal.commands]
                    active_proposal=proposal
                    phase={"kind":"goal" if proposal.complete else "enabling","commands":[]}
                    for command in commands:
                        if len(history)>=limit or int(obs.levels_completed)>=1:break
                        before_record=R.BASE.observation_record(obs);fallback=commit_macro_command(tx,obs,command)
                        obs=R.BASE.execute_action(env,game,command.opaque_action,dict(command.data),"capability-macro-probe")
                        after_record=R.BASE.observation_record(obs);transition_id=f"transition:{len(history)}:{after_record['digest'][:16]}"
                        inducer.observe_option_transition(opaque_action=command.opaque_action,after=R.BASE.observation_grid(obs),transition_id=transition_id,direct=True)
                        history.append({"action":command.opaque_action,"data":dict(command.data),"mode":"capability_probe","fallback_action":fallback.action_id,"before":before_record["digest"],"after":after_record["digest"],"role":command.role})
                        macro["executed_command_count"]+=1
                        phase["commands"].append({"intervention_ref":"iv:"+SYN.stable_hash({"opaque":command.opaque_action})[:16],"role":command.role,"transition_id":transition_id})
                    macro["phases"].append(phase)
                    after_value=current_value(selected.execution.candidate,R.BASE.observation_grid(obs))
                    # An incomplete exact plan is an explicitly unsupported
                    # enabling hypothesis.  It may unlock one changed,
                    # complete continuation, but it never raises goal support
                    # by itself.  The complete continuation is still judged
                    # against the original observable potential.
                    if (
                        not proposal.complete and after_value==before
                        and macro["executed_command_count"]<MAX_MACRO_COMMANDS
                        and int(obs.levels_completed)<1
                    ):
                        continued=REG.propose_calibrated(
                            R.BASE.observation_grid(obs),motion_actions=motion,
                            parameterized_actions=parameterized,release_actions=release,
                        )
                        next_rows=[
                            row for row in continued
                            if row.capability==selected.capability
                            and row.execution.candidate.candidate_id==selected.execution.candidate.candidate_id
                            and row.execution.proposal.complete
                        ]
                        if next_rows:
                            next_proposal=next_rows[0].execution.proposal
                            active_proposal=next_proposal
                            next_signature=[(row.opaque_action,list(row.data),row.role) for row in next_proposal.commands]
                            if next_signature!=first_signature:
                                phase={"kind":"goal","commands":[]}
                                remaining=MAX_MACRO_COMMANDS-macro["executed_command_count"]
                                for command in next_proposal.commands[:remaining]:
                                    if len(history)>=limit or int(obs.levels_completed)>=1:break
                                    before_record=R.BASE.observation_record(obs);fallback=commit_macro_command(tx,obs,command)
                                    obs=R.BASE.execute_action(env,game,command.opaque_action,dict(command.data),"capability-goal-probe")
                                    after_record=R.BASE.observation_record(obs);transition_id=f"transition:{len(history)}:{after_record['digest'][:16]}"
                                    inducer.observe_option_transition(opaque_action=command.opaque_action,after=R.BASE.observation_grid(obs),transition_id=transition_id,direct=True)
                                    history.append({"action":command.opaque_action,"data":dict(command.data),"mode":"capability_probe","fallback_action":fallback.action_id,"before":before_record["digest"],"after":after_record["digest"],"role":command.role})
                                    macro["executed_command_count"]+=1
                                    phase["commands"].append({"intervention_ref":"iv:"+SYN.stable_hash({"opaque":command.opaque_action})[:16],"role":command.role,"transition_id":transition_id})
                                macro["phases"].append(phase)
                                after_value=current_value(selected.execution.candidate,R.BASE.observation_grid(obs))
                    macro.update({"potential_after":after_value,"environment_verdict":"supports" if before is not None and after_value is not None and after_value<before else "refutes" if before is not None and after_value is not None else "unresolved","support_after":1 if before is not None and after_value is not None and after_value<before else 0})
                    control_used=0
                    while (
                        macro["support_after"]>0 and after_value is not None and after_value>0
                        and int(obs.levels_completed)<1 and len(history)<limit
                        and control_used<MAX_CONFIRMED_CONTROL_COMMANDS
                    ):
                        try:
                            next_proposal=REG.exact.compile_execution(
                                selected.execution.candidate,R.BASE.observation_grid(obs),
                                motion_actions=motion,
                                parameterized_actions=parameterized,release_actions=release,
                                grounding_memory=active_proposal.grounding_memory,
                            )
                        except Exception as error:
                            macro["control_stop"]=f"{type(error).__name__}: {error}"
                            break
                        active_proposal=next_proposal
                        phase={"kind":"confirmed_control","commands":[],"potential_before":after_value}
                        prior=after_value
                        allowance=min(
                            len(next_proposal.commands),
                            MAX_CONFIRMED_CONTROL_COMMANDS-control_used,
                            limit-len(history),
                        )
                        for command in next_proposal.commands[:allowance]:
                            if int(obs.levels_completed)>=1:break
                            before_record=R.BASE.observation_record(obs);fallback=commit_macro_command(tx,obs,command)
                            obs=R.BASE.execute_action(env,game,command.opaque_action,dict(command.data),"capability-confirmed-control")
                            after_record=R.BASE.observation_record(obs);transition_id=f"transition:{len(history)}:{after_record['digest'][:16]}"
                            inducer.observe_option_transition(opaque_action=command.opaque_action,after=R.BASE.observation_grid(obs),transition_id=transition_id,direct=True)
                            history.append({"action":command.opaque_action,"data":dict(command.data),"mode":"capability_control","fallback_action":fallback.action_id,"before":before_record["digest"],"after":after_record["digest"],"role":command.role})
                            control_used+=1;macro["executed_command_count"]+=1
                            phase["commands"].append({"intervention_ref":"iv:"+SYN.stable_hash({"opaque":command.opaque_action})[:16],"role":command.role,"transition_id":transition_id})
                        after_value=(0 if int(obs.levels_completed)>=1 else tracked_value(next_proposal,R.BASE.observation_grid(obs)))
                        if after_value is None:
                            after_value=current_value(selected.execution.candidate,R.BASE.observation_grid(obs))
                        phase["potential_after"]=after_value;macro["phases"].append(phase)
                        # A supported lease is revoked immediately by measured
                        # regression or loss of a direct potential reading.
                        if after_value is None or after_value>prior:
                            macro["environment_verdict"]="refutes-after-support";macro["support_after"]=0;break
                        if not phase["commands"] or after_value==prior:break
                    macro["potential_after"]=after_value
                    continue
                if motion:attempted=True
            before_record=R.BASE.observation_record(obs);decision=controller.choose_from_inducer(R.symbolic(obs),inducer)
            obs=R.BASE.execute_action(env,game,decision.action_id,dict(decision.data),f"hybrid-{decision.mode}")
            after_record=R.BASE.observation_record(obs);transition_id=f"transition:{len(history)}:{after_record['digest'][:16]}"
            verdict=controller.observe_inducer_transition(inducer,decision,after=R.BASE.observation_grid(obs),transition_id=transition_id,direct=True)
            history.append({"action":decision.action_id,"data":dict(decision.data),"mode":decision.mode,"fallback_action":decision.fallback_action_id,"before":before_record["digest"],"after":after_record["digest"],"verdict":verdict})
        tx.observe(R.symbolic(obs));final=R.BASE.observation_record(obs)
    finally:arcade.close_scorecard()
    replay_arcade,replay_env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"replay",game);replay=replay_env.observation_space or replay_env.reset();exact=True
    try:
        for index,row in enumerate(history):
            if reset_at is not None and index==reset_at:
                replay=replay_env.reset();exact=exact and R.BASE.observation_record(replay)["digest"]==reset_digest
            replay=R.BASE.execute_action(replay_env,game,row["action"],row["data"],"capability-replay")
            exact=exact and R.BASE.observation_record(replay)["digest"]==row["after"]
    finally:replay_arcade.close_scorecard()
    return {"actions":len(history),"resets":int(reset_at is not None),"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":exact,"macro":macro,"trace":history}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--game",required=True);args=parser.parse_args()
    baseline=R.run(args.game,False);shared=run(args.game)
    result={"protocol":"live-capability-hybrid-development-v0","development_only":True,"game":args.game,"gates":{"minimum_cardinal_calibrations":MIN_CARDINAL_CALIBRATIONS,"max_macro_commands":MAX_MACRO_COMMANDS},"baseline":{"actions":len(baseline["actions"]),"levels_completed":baseline["levels_completed"]},"shared":shared}
    target=ART/args.game/"RESULT.json";target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":args.game,"baseline":result["baseline"],"shared":{"actions":shared["actions"],"levels_completed":shared["levels_completed"],"exact_replay":shared["exact_replay"],"macro":shared["macro"]}}));return 0


if __name__=="__main__":raise SystemExit(main())
