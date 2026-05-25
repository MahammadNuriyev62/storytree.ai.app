"""Story creation: the root of the tree must be wired correctly."""

from sqlmodel import Session, select
import db_models
from db_models import Story, Scene, Choice


def test_create_story_persists_metadata(make_story):
    story = make_story(n_scenes=7, difficulty=0.3)
    assert story["title"] == "The Test Expanse"
    assert story["n_scenes"] == 7
    assert story["emojis"] == ["🧪", "🌳", "🔁"]
    assert story["main_characters"][0]["name"] == "Tester"


def test_create_story_builds_root_scene_choice_and_child(make_story):
    story = make_story()
    with Session(db_models.engine) as s:
        scenes = s.exec(select(Scene).where(Scene.story_id == story["id"])).all()
        choices = s.exec(select(Choice)).all()

        # exactly one root scene (has text) + one child placeholder (text None)
        with_text = [sc for sc in scenes if sc.text is not None]
        without_text = [sc for sc in scenes if sc.text is None]
        assert len(with_text) == 1
        assert len(without_text) == 1
        assert with_text[0].text.startswith("Tester stands at the root of the story tree.")

        # one root choice, pointing from the root scene to the child placeholder
        assert len(choices) == 1
        root_choice = choices[0]
        assert root_choice.scene_id == with_text[0].id
        assert root_choice.next_scene_id == without_text[0].id


def test_only_metadata_llm_call_on_create(make_story, fake):
    make_story()
    assert fake.metadata_calls == 1
    assert fake.scene_calls == 0  # no scene generation happens at creation time
