"""The lazy-cache contract: generate once, then serve from the DB forever.

This is the property that makes 'infinite' stories affordable. If a refactor
ever regenerates an already-materialized scene, these tests fail.
"""


def test_root_scene_is_already_materialized(make_story, get_scene, fake):
    story = make_story()
    root = get_scene(story["id"])  # no choice_id
    assert root["text"].startswith("Tester stands at the root of the story tree.")
    assert fake.scene_calls == 0  # root text came from creation, not generation


def test_refetch_serves_cache_with_zero_extra_llm_calls(make_story, get_scene, fake):
    story = make_story()
    opening = get_scene(story["id"])["choices"][0]

    first = get_scene(story["id"], opening["id"])
    assert fake.scene_calls == 1

    second = get_scene(story["id"], opening["id"])
    assert fake.scene_calls == 1, "re-fetching a generated scene must not call the LLM"
    assert second["id"] == first["id"]
    assert second["text"] == first["text"]
    # choices must be stable across the cache hit (same ids, same order)
    assert [c["id"] for c in second["choices"]] == [c["id"] for c in first["choices"]]


def test_revisiting_a_path_is_fully_cached(make_story, get_scene, fake):
    """Replaying the same 3-hop path a second time triggers no new generation."""
    story = make_story(n_scenes=20)

    def play_three_hops():
        choice = get_scene(story["id"])["choices"][0]
        for _ in range(3):
            scene = get_scene(story["id"], choice["id"])
            choice = scene["choices"][0]

    play_three_hops()
    assert fake.scene_calls == 3
    play_three_hops()  # identical path again
    assert fake.scene_calls == 3, "the second walk down a known path must be free"
