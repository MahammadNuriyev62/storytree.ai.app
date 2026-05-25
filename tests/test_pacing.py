"""Model-decided pacing: n_scenes is a soft target, but a hard cap guarantees
every story terminates so the engine can never run away."""


def test_pacing_phase_is_reported(make_story, get_scene):
    story = make_story(n_scenes=20)
    opening = get_scene(story["id"])["choices"][0]
    scene = get_scene(story["id"], opening["id"])
    assert scene["pacing"] in {"setup", "rising", "climax", "resolution"}


def test_hard_cap_forces_termination_at_target(make_story, get_scene):
    """With a tiny target, 'continue' must hit a forced ending at the cap."""
    story = make_story(n_scenes=2)
    choice = get_scene(story["id"])["choices"][0]

    reached_end = False
    for _ in range(6):  # well past the cap of 2
        scene = get_scene(story["id"], choice["id"])
        if all(c["next_scene_id"] is None for c in scene["choices"]):
            reached_end = True
            break
        choice = scene["choices"][0]  # keep choosing 'continue'
    assert reached_end, "hard cap should force the story to end near the target length"


def test_resolution_scene_marked_resolution(make_story, get_scene):
    story = make_story(n_scenes=10)
    opening = get_scene(story["id"])["choices"][0]
    scene = get_scene(story["id"], opening["id"])
    finale = scene["choices"][-1]  # the is_final choice
    ending = get_scene(story["id"], finale["id"])
    assert ending["pacing"] == "resolution"
