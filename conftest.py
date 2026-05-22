"""Pytest fixtures for StoryTree.

Key trick: the SQLModel engine is created at *import time* from settings.db_name,
so we point DB_NAME at a throwaway file BEFORE importing any app module. Tables
are reset per-test for isolation, and the LLM is replaced with a FakeChatBot.
"""

import os
import tempfile

# Must run before db_models / api / main are imported anywhere.
_TMP_DIR = tempfile.mkdtemp(prefix="storytree_tests_")
os.environ["DB_NAME"] = os.path.join(_TMP_DIR, "test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import db_models  # noqa: E402
import api  # noqa: E402
import main  # noqa: E402
from tests.fakes import FakeChatBot  # noqa: E402

db_models.engine.echo = False  # silence SQL logging during tests


@pytest.fixture(autouse=True)
def fresh_db():
    """Give every test an empty database."""
    db_models.SQLModel.metadata.drop_all(db_models.engine)
    db_models.SQLModel.metadata.create_all(db_models.engine)
    yield


@pytest.fixture
def fake():
    return FakeChatBot()


@pytest.fixture
def client(fake, monkeypatch):
    """TestClient with the LLM swapped for the deterministic FakeChatBot."""
    monkeypatch.setattr(api, "light_weight_chatbot", fake)
    monkeypatch.setattr(api, "heavy_weight_chatbot", fake)
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def make_story(client):
    """Create a story via the real POST endpoint; return its parsed body."""
    def _make(description="A deterministic test adventure that branches.", n_scenes=5, difficulty=0.4):
        resp = client.post(
            "/api/stories",
            json={"description": description, "n_scenes": n_scenes, "difficulty": difficulty},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()
    return _make


@pytest.fixture
def get_scene(client):
    """Fetch (and lazily generate) a scene; choice_id=None returns the root."""
    def _get(story_id, choice_id=None):
        url = f"/api/stories/{story_id}/scene"
        if choice_id is not None:
            url += f"?choice_id={choice_id}"
        resp = client.get(url)
        assert resp.status_code == 200, resp.text
        return resp.json()
    return _get
