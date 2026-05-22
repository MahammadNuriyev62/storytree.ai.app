"""Opt-in contract tests against the REAL Claude backend.

These guard against model/prompt *drift*: a model upgrade or a prompt edit that
makes the output unparseable or drop required keys. They assert on STRUCTURE,
never on exact wording (which is non-deterministic).

Excluded from the default run (see pytest.ini addopts). Run explicitly with:
    pytest -m llm
"""

import os
import shutil

import pytest

from chatbots.claude_chatbot import ChatBot, _NODE_BIN
from generate import generate_story_metadata, generate_description

_claude_available = shutil.which("claude") is not None or os.path.exists(
    os.path.join(_NODE_BIN, "claude")
)

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not _claude_available, reason="claude CLI not installed"),
]


async def test_metadata_has_all_required_keys():
    bot = ChatBot(model_name="o4-mini")  # -> claude sonnet
    md = await generate_story_metadata(
        bot, "A clockmaker discovers her repairs are quietly rewinding the town's history."
    )
    assert isinstance(md, dict), f"metadata did not parse to a dict: {md!r}"
    for key in [
        "title", "description", "characters", "main_character",
        "worldview", "themes", "emojis", "first_introduction_scene",
    ]:
        assert key in md, f"metadata missing required key '{key}'"

    intro = md["first_introduction_scene"]
    assert "text" in intro and "choice" in intro
    assert "text" in intro["choice"] and "loading_text" in intro["choice"]


async def test_description_is_nonempty_prose():
    bot = ChatBot()
    desc = await generate_description(bot)
    assert isinstance(desc, str) and len(desc.strip()) > 10
