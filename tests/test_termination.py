"""Branches must end. 'Wrong' and 'pre-final' choices lead to terminal scenes
(scenes whose choices have next_scene_id == None), which the UI reads as 'The End'.
"""


def _first_real_scene(make_story, get_scene, n_scenes=10):
    story = make_story(n_scenes=n_scenes)
    opening = get_scene(story["id"])["choices"][0]
    scene = get_scene(story["id"], opening["id"])
    # NORMAL_CHOICES order: [0] continue, [1] wrong, [2] final
    return story, scene


def test_wrong_choice_continues_with_consequences(make_story, get_scene):
    """is_wrong is COSTLY but not fatal — story continues, with a bigger state hit."""
    story, scene = _first_real_scene(make_story, get_scene)
    health_before = scene["state"]["stats"]["health"]

    # baseline: a normal 'continue' choice -> small health hit
    normal_next = get_scene(story["id"], scene["choices"][0]["id"])
    normal_hit = health_before - normal_next["state"]["stats"]["health"]

    # the wrong choice from the same parent -> story continues, bigger hit
    wrong_next = get_scene(story["id"], scene["choices"][1]["id"])
    wrong_hit = health_before - wrong_next["state"]["stats"]["health"]

    assert wrong_next["choices"], "story must continue after a costly choice"
    assert any(c["next_scene_id"] is not None for c in wrong_next["choices"]), (
        "a wrong choice must NOT auto-terminate the story"
    )
    assert wrong_hit > normal_hit, (
        f"costly choice should hurt more than a normal one (wrong={wrong_hit}, normal={normal_hit})"
    )


def test_pre_final_choice_leads_to_terminal_finale(make_story, get_scene):
    story, scene = _first_real_scene(make_story, get_scene)
    finale = scene["choices"][2]
    ending = get_scene(story["id"], finale["id"])
    assert ending["choices"]
    assert all(c["next_scene_id"] is None for c in ending["choices"]), (
        "a finale must be terminal"
    )


def test_normal_choice_is_not_terminal(make_story, get_scene):
    story, scene = _first_real_scene(make_story, get_scene)
    cont = scene["choices"][0]
    assert cont["next_scene_id"] is not None  # continuing leads onward, not to an end


def test_playthrough_reaches_an_end_in_bounded_steps(make_story, get_scene):
    """Choosing the finale path must terminate, not recurse forever."""
    story = make_story(n_scenes=50)
    choice = get_scene(story["id"])["choices"][0]

    for _ in range(10):  # generous upper bound; should end well before this
        scene = get_scene(story["id"], choice["id"])
        finale = scene["choices"][-1]  # the 'final' choice
        ending = get_scene(story["id"], finale["id"])
        if all(c["next_scene_id"] is None for c in ending["choices"]):
            return  # reached a terminal scene
        choice = scene["choices"][0]
    raise AssertionError("story never terminated within the step budget")
