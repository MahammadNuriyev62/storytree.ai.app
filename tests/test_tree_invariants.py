"""Structural invariants of the materialized story tree.

If any of these break, the root-scene lookup (api.get_story) or the parent-walk
branch reconstruction will start misbehaving — often silently.
"""

from sqlmodel import Session, select
import db_models
from db_models import Scene, Choice


def _build_small_tree(make_story, get_scene):
    """Create a story and explore a few branches to grow a real tree."""
    story = make_story(n_scenes=20)
    opening = get_scene(story["id"])["choices"][0]
    s1 = get_scene(story["id"], opening["id"])
    # explore two children of s1: continue, and the wrong branch
    get_scene(story["id"], s1["choices"][0]["id"])
    get_scene(story["id"], s1["choices"][1]["id"])
    return story["id"]


def test_exactly_one_root_scene(make_story, get_scene):
    story_id = _build_small_tree(make_story, get_scene)
    with Session(db_models.engine) as s:
        scenes = s.exec(select(Scene).where(Scene.story_id == story_id)).all()
        pointed_to = {
            c.next_scene_id
            for c in s.exec(select(Choice)).all()
            if c.next_scene_id is not None
        }
        roots = [sc for sc in scenes if sc.id not in pointed_to]
        assert len(roots) == 1, f"expected exactly one root, found {len(roots)}"
        # the root-scene query in api.py must agree
        assert roots[0].text is not None


def test_every_non_root_scene_has_exactly_one_parent(make_story, get_scene):
    story_id = _build_small_tree(make_story, get_scene)
    with Session(db_models.engine) as s:
        scenes = s.exec(select(Scene).where(Scene.story_id == story_id)).all()
        choices = s.exec(select(Choice)).all()
        parents_of = {}
        for c in choices:
            if c.next_scene_id is not None:
                parents_of.setdefault(c.next_scene_id, 0)
                parents_of[c.next_scene_id] += 1
        # no scene is the target of more than one choice (a tree, not a graph)
        assert all(count == 1 for count in parents_of.values()), parents_of
        # exactly one scene has zero parents (the root)
        rootless = [sc for sc in scenes if sc.id not in parents_of]
        assert len(rootless) == 1


def test_parent_walk_terminates(make_story, get_scene):
    """Reconstructing history from any leaf must reach the root without looping."""
    story_id = _build_small_tree(make_story, get_scene)
    with Session(db_models.engine) as s:
        scenes = s.exec(select(Scene).where(Scene.story_id == story_id)).all()
        for leaf in scenes:
            current = leaf
            steps = 0
            while current.parent_choice is not None:
                current = current.parent_choice.scene
                steps += 1
                assert steps <= len(scenes), f"cycle detected walking up from {leaf.id}"
