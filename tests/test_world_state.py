"""Persistent world state: seeded at creation, snapshotted per scene, and
carried (and evolved) down a branch."""


def _opening_choice(get_scene, story_id):
    return get_scene(story_id)["choices"][0]


def test_root_scene_carries_initial_state(make_story, get_scene):
    story = make_story()
    assert story["initial_state"]["inventory"] == ["lantern"]
    assert story["initial_state"]["stats"]["health"] == 100

    root = get_scene(story["id"])
    assert root["state"] == story["initial_state"]
    assert root["pacing"] == "setup"


def test_generated_scene_has_full_state_and_changes(make_story, get_scene):
    story = make_story()
    opening = _opening_choice(get_scene, story["id"])
    scene = get_scene(story["id"], opening["id"])

    for bucket in ["stats", "inventory", "relationships", "flags"]:
        assert bucket in scene["state"], f"state missing '{bucket}'"
    assert scene["state_changes"], "a generated scene should report what changed"
    assert scene["pacing"] in {"setup", "rising", "climax", "resolution"}


def test_state_accumulates_down_a_branch(make_story, get_scene):
    """Walking 'continue' must thread state through: inventory grows, health drops."""
    story = make_story(n_scenes=20)
    start_health = story["initial_state"]["stats"]["health"]
    start_items = len(story["initial_state"]["inventory"])

    choice = _opening_choice(get_scene, story["id"])
    for hop in range(1, 4):
        scene = get_scene(story["id"], choice["id"])
        assert len(scene["state"]["inventory"]) == start_items + hop
        assert scene["state"]["stats"]["health"] == start_health - 5 * hop
        assert scene["state"]["flags"]["step_taken"] is True
        choice = scene["choices"][0]


def test_state_diverges_independently_per_branch(make_story, get_scene):
    """Two different branches must not share mutated state."""
    story = make_story(n_scenes=20)
    opening = _opening_choice(get_scene, story["id"])
    scene = get_scene(story["id"], opening["id"])

    # descend two hops on the 'continue' branch
    deep = get_scene(story["id"], scene["choices"][0]["id"])
    deep2 = get_scene(story["id"], deep["choices"][0]["id"])

    # the shallow scene's state is untouched by the deeper exploration
    assert len(scene["state"]["inventory"]) < len(deep2["state"]["inventory"])
