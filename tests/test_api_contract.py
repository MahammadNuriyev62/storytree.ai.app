"""Freeze the JSON shapes the (future React) frontend depends on.

If a refactor renames or drops a field the client reads, these fail loudly.
Field list mirrors what templates/play.html consumes today.
"""


def test_post_stories_shape(make_story):
    story = make_story()
    for key in ["id", "title", "description", "emojis", "themes",
                "main_characters", "characters", "worldview", "n_scenes", "difficulty"]:
        assert key in story, f"create story response missing '{key}'"
    assert isinstance(story["emojis"], list)
    assert isinstance(story["worldview"], dict)


def test_list_stories_shape(make_story, client):
    make_story()
    body = client.get("/api/stories").json()
    assert "stories" in body and isinstance(body["stories"], list)
    item = body["stories"][0]
    for key in ["id", "title", "description", "emojis"]:
        assert key in item


def test_story_details_shape(make_story, client):
    story = make_story()
    body = client.get(f"/api/stories/{story['id']}").json()
    for key in ["id", "title", "description", "emojis", "characters",
                "main_characters", "worldview", "themes", "n_scenes"]:
        assert key in body, f"story details missing '{key}'"


def test_scene_shape_is_stable(make_story, get_scene):
    """The contract the player UI binds to: scene.text + scene.choices[*]."""
    story = make_story()
    root = get_scene(story["id"])

    assert isinstance(root["id"], int)
    assert isinstance(root["text"], str) and root["text"]
    assert isinstance(root["choices"], list) and root["choices"]

    for choice in root["choices"]:
        assert isinstance(choice["id"], int)
        assert isinstance(choice["text"], str) and choice["text"]
        assert "loading_text" in choice  # UI shows this while generating
        assert "next_scene_id" in choice  # None => finale (UI renders 'The End')


def test_generated_scene_shape_is_stable(make_story, get_scene):
    story = make_story()
    opening = get_scene(story["id"])["choices"][0]
    scene = get_scene(story["id"], opening["id"])
    assert set(["id", "text", "choices"]).issubset(scene.keys())
    for choice in scene["choices"]:
        assert set(["id", "text", "loading_text", "next_scene_id"]).issubset(choice.keys())


def test_scene_world_state_contract(make_story, get_scene):
    """The HUD/relationships UI binds to these fields — freeze them."""
    story = make_story()
    scene = get_scene(story["id"])  # root scene
    assert set(["state", "state_changes", "pacing"]).issubset(scene.keys())
    assert set(["stats", "inventory", "relationships", "flags"]).issubset(scene["state"].keys())
    assert isinstance(scene["state_changes"], list)


def test_story_details_exposes_initial_state(make_story, client):
    story = make_story()
    body = client.get(f"/api/stories/{story['id']}").json()
    assert "initial_state" in body
    assert set(["stats", "inventory", "relationships", "flags"]).issubset(body["initial_state"].keys())


def test_description_endpoint_shape(client):
    body = client.get("/api/stories/description").json()
    assert "description" in body and isinstance(body["description"], str)
