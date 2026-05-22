"""A deterministic, offline stand-in for the LLM-backed ChatBot.

It mimics `ChatBot.prompt(messages) -> str` but never makes a network call.
Responses are chosen by inspecting the *last user message*, because the prompt
strings in generate.py are distinctive (see USER_*_TEMPLATE there).

It also records every call so tests can assert how many times generation ran
(critical for the lazy-cache contract: a cached re-fetch must trigger 0 calls).
"""

import json

# A complete story-metadata blob — must contain every key create_story reads
# (see api.create_story): title, description, characters, main_character,
# worldview, themes, emojis, first_introduction_scene{text, choice{...}}.
DEFAULT_METADATA = {
    "title": "The Test Expanse",
    "description": "A deterministic adventure used to exercise the engine.",
    "main_character": {
        "name": "Tester",
        "role": "Protagonist",
        "traits": ["methodical", "curious"],
        "description": "Walks every branch of the tree.",
    },
    "characters": [
        {
            "name": "The Oracle",
            "role": "Guide",
            "traits": ["cryptic"],
            "description": "Knows where the bugs hide.",
        }
    ],
    "emojis": ["🧪", "🌳", "🔁"],
    "worldview": {
        "setting": "A branching maze of scenes.",
        "timePeriod": "CI runtime",
        "technologyLevel": "pytest",
        "magicSystem": "Deterministic responses.",
    },
    "themes": ["Testing", "Recursion", "Determinism"],
    "first_introduction_scene": {
        "text": "Tester stands at the root of the story tree.",
        "choice": {
            "text": "Step into the maze",
            "loading_text": "Entering the maze...",
        },
    },
}

# A normal scene offers three archetypal choices so a single fake can drive
# every path: continue, a 'wrong' dead-end, and a 'final' (pre-final) ending.
NORMAL_CHOICES = [
    {"text": "Continue forward", "loading_text": "Moving on...", "is_wrong": False, "is_final": False},
    {"text": "Touch the cursed idol", "loading_text": "That felt unwise...", "is_wrong": True, "is_final": False},
    {"text": "Approach the exit", "loading_text": "The end nears...", "is_wrong": False, "is_final": True},
]


class FakeChatBot:
    def __init__(self, model_name="fake"):
        self.model_name = model_name
        self.calls = []          # full message lists, in order
        self.metadata_calls = 0
        self.description_calls = 0
        self.scene_calls = 0     # number of scene generations (the recursion)
        self.queue = []          # optional: scripted raw responses, popped FIFO

    def enqueue(self, raw: str):
        """Force the next prompt() to return exactly `raw` (bypasses routing)."""
        self.queue.append(raw)

    async def prompt(self, messages):
        self.calls.append(messages)
        if self.queue:
            return self.queue.pop(0)

        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = str(m["content"])
                break

        if "Output the complete json" in last_user:
            self.metadata_calls += 1
            return json.dumps(DEFAULT_METADATA)

        if "story description" in last_user:
            self.description_calls += 1
            return "A lone signal blinks in the dark; someone, somewhere, is still listening."

        # --- scene generation (the recursive core) ---
        self.scene_calls += 1
        if "ends the story due to the wrong decision" in last_user:
            return json.dumps({
                "text": "Your mistake catches up with you. Darkness.",
                "choices": [{"text": "Game Over", "loading_text": "RIP", "is_wrong": False, "is_final": False}],
            })
        if "Generate final scene" in last_user:
            return json.dumps({
                "text": "You reach the end of the tale, changed but whole.",
                "choices": [{"text": "The End", "loading_text": "Fin", "is_wrong": False, "is_final": False}],
            })
        # first scene or normal next scene
        return json.dumps({
            "text": "A new chamber of the maze unfolds before you.",
            "choices": [dict(c) for c in NORMAL_CHOICES],
        })
