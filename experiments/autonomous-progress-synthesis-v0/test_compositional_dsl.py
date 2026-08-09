import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import pytest
import compositional_dsl as dsl
import progress_synthesis as ps


def grid():
    g=[[0]*12 for _ in range(12)]
    for y in range(2,5):
        for x in range(2,5):g[y][x]=1
    for y in range(6,11):
        for x in range(6,11):g[y][x]=2
    for y in range(7,10):
        for x in range(7,10):g[y][x]=0
    return g


def test_closed_primitives_are_generated_and_pixel_executable():
    rows=dsl.propose(grid());kinds={row.ast["potential"]["op"] for row in rows}
    assert "ContainmentDeficit" in kinds and "AxisMisalignment" in kinds
    assert all(isinstance(dsl.evaluate(row,grid()),int) for row in rows)


def test_composition_is_bounded_and_grounded():
    scene=ps.perceive(grid());ids=[row.region_id for row in scene.regions]
    expression={"op":"Sum","terms":[{"op":"AxisMisalignment","arguments":["?x","?y"]},{"op":"BoundingBoxGap","arguments":["?x","?y"]}]}
    candidate=dsl.compile_candidate(expression,{"?x":ids[0],"?y":ids[1]},scene)
    assert dsl.evaluate(candidate,grid())>=0
    with pytest.raises(ps.SynthesisError):dsl.compile_candidate({"op":"Sum","terms":[expression]*5},{"?x":ids[0],"?y":ids[1]},scene)


@pytest.mark.parametrize("expression",[
    {"op":"TeleportToColor","arguments":["?a","?b"]},
    {"op":"AxisMisalignment","arguments":["action","?b"]},
    {"op":"AxisMisalignment","arguments":["?a","?b"],"game":"ar25"},
])
def test_semantic_and_game_shortcuts_are_rejected(expression):
    with pytest.raises(ps.SynthesisError):dsl.validate_expression(expression)


def test_qwen_gets_closed_vocabulary_and_visible_addresses_not_truth():
    doc=dsl.qwen_contract(ps.perceive(grid()));text=str(doc)
    assert set(doc["allowed_operators"])==set(dsl.OPS)
    assert "support zero" in text and "action_id" not in text
