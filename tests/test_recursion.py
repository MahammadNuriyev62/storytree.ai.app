"""The recursive core: lazy generation, branch-history reconstruction, divergence.

These are the tripwires that should fire if a future refactor (e.g. the React
rewrite or a schema change) breaks the engine.
"""


def _root_choice(get_scene, story_id):
    root = get_scene(story_id)  # choice_id=None -> root scene
    assert root["choices"], "root scene must offer the opening choice"
    return root["choices"][0]


def test_first_fetch_generates_then_advances(make_story, get_scene, fake):
    story = make_story()
    opening = _root_choice(get_scene, story["id"])

    assert fake.scene_calls == 0  # nothing generated yet
    scene = get_scene(story["id"], opening["id"])
    assert fake.scene_calls == 1  # exactly one generation
    assert scene["text"]
    assert len(scene["choices"]) == 3  # NORMAL_CHOICES


def test_multi_hop_playthrough_generates_one_scene_per_hop(make_story, get_scene, fake):
    """Walking 'continue' down the tree must generate exactly one scene per step."""
    story = make_story(n_scenes=20)
    choice = _root_choice(get_scene, story["id"])

    seen_scene_ids = []
    for hop in range(1, 5):
        scene = get_scene(story["id"], choice["id"])
        seen_scene_ids.append(scene["id"])
        assert fake.scene_calls == hop, f"hop {hop} should mean {hop} generations"
        assert scene["text"]
        # follow the 'continue' choice (index 0) deeper
        choice = scene["choices"][0]

    # every hop produced a distinct scene -> we really descended the tree
    assert len(set(seen_scene_ids)) == 4


def test_branch_history_grows_with_depth(make_story, get_scene, fake):
    """Each generation should replay the full ancestor chain to the model."""
    story = make_story(n_scenes=20)
    choice = _root_choice(get_scene, story["id"])

    for expected_depth in range(1, 5):
        scene = get_scene(story["id"], choice["id"])
        last_call = fake.calls[-1]
        assistant_turns = sum(1 for m in last_call if m.get("role") == "assistant")
        # history = root + (expected_depth-1) generated scenes = expected_depth scenes
        assert assistant_turns == expected_depth, (
            f"depth {expected_depth}: expected {expected_depth} prior scenes in prompt, "
            f"got {assistant_turns}"
        )
        choice = scene["choices"][0]


def test_divergent_choices_yield_distinct_branches(make_story, get_scene):
    """Different choices from the same scene must lead to different next scenes."""
    story = make_story()
    opening = _root_choice(get_scene, story["id"])
    scene = get_scene(story["id"], opening["id"])

    cont, _wrong, finale = scene["choices"]
    assert cont["next_scene_id"] != finale["next_scene_id"]

    branch_a = get_scene(story["id"], cont["id"])
    branch_b = get_scene(story["id"], finale["id"])
    # distinct scene rows, and the engine routed them to different content
    assert branch_a["id"] != branch_b["id"]
    assert branch_a["text"] != branch_b["text"]


def test_first_generation_includes_opening_framing(make_story, get_scene, fake):
    """The opening generation must include the 'opening scene' framing in its prompt."""
    story = make_story()
    opening = _root_choice(get_scene, story["id"])
    get_scene(story["id"], opening["id"])

    prompt_text = "\n".join(str(m["content"]) for m in fake.calls[-1])
    assert "opening scene" in prompt_text
