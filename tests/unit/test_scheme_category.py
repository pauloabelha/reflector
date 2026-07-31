from reflector.core.scheme_category import (
    FocusedRewriteObject,
    FocusedVariable,
    FocusMorphism,
    TranslationMorphism,
    apply_focus,
    apply_translation,
    compile_focused_option,
    focus_square,
    translation_square,
)


def _state(
    focused: tuple[int, int] = (12, 15),
) -> FocusedRewriteObject:
    return FocusedRewriteObject(
        (
            FocusedVariable(9, focused, frozenset({(3, 6)})),
            FocusedVariable(11, (20, 20), frozenset({(20, 20)})),
        ),
        9,
    )


def test_translation_is_an_endomorphism_on_only_the_focused_variable() -> None:
    source = _state()
    morphism = TranslationMorphism(1, (0, -3))

    destination = apply_translation(source, morphism)

    assert destination.focused.value == (12, 12)
    assert destination.variables[1] == source.variables[1]
    assert destination.focused.goals == source.focused.goals


def test_commuting_square_confirms_exact_abstract_prediction() -> None:
    source = _state()
    morphism = TranslationMorphism(1, (0, -3))
    destination = apply_translation(source, morphism)

    assert translation_square(source, destination, morphism).commutes
    assert not translation_square(source, _state((9, 15)), morphism).commutes


def test_focus_morphism_preserves_relational_content() -> None:
    source = _state()
    morphism = FocusMorphism(5, 9, 11)

    destination = apply_focus(source, morphism)

    assert destination.variables == source.variables
    assert destination.focus == 11
    assert focus_square(source, destination, morphism).commutes
    changed = FocusedRewriteObject(
        (
            source.variables[0],
            FocusedVariable(11, (17, 20), frozenset({(20, 20)})),
        ),
        11,
    )
    assert not focus_square(source, changed, morphism).commutes


def test_compiles_shortest_reachable_goal_as_compressed_option() -> None:
    state = _state()
    morphisms = (
        TranslationMorphism(1, (0, -3)),
        TranslationMorphism(2, (0, 3)),
        TranslationMorphism(3, (-3, 0)),
        TranslationMorphism(4, (3, 0)),
    )

    option = compile_focused_option(
        state,
        morphisms,
        width=32,
        height=32,
    )

    assert option.status == "solved"
    assert len(option.actions) == 6
    assert option.actions.count(1) == 3
    assert option.actions.count(3) == 3
    assert option.target == (3, 6)
    assert option.compression_utility > 0
    assert option.retained


def test_selects_only_action_lattice_reachable_embedding_candidate() -> None:
    state = FocusedRewriteObject(
        (
            FocusedVariable(
                13,
                (38, 30),
                frozenset({(18, 10), (19, 11), (20, 12)}),
            ),
        ),
        13,
    )
    morphisms = (
        TranslationMorphism(1, (0, -3)),
        TranslationMorphism(2, (0, 3)),
        TranslationMorphism(3, (-3, 0)),
        TranslationMorphism(4, (3, 0)),
    )

    option = compile_focused_option(
        state,
        morphisms,
        width=64,
        height=64,
    )

    assert option.status == "solved"
    assert option.target == (20, 12)
    assert len(option.actions) == 12
