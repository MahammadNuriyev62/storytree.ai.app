"""A deterministic, offline stand-in for the LLM-backed ChatBot.

It mimics `ChatBot.prompt(messages) -> str` but never makes a network call.
Responses are chosen by inspecting the *last user message*, because the prompt
strings in generate.py are distinctive.

For scene generation it EVOLVES the world state read from the most recent
assistant turn, so tests can prove that state actually accumulates down a branch
(inventory grows, health drops, etc.) rather than just checking shape.

It also records every call so tests can assert how many times generation ran
(critical for the lazy-cache contract: a cached re-fetch must trigger 0 calls).
"""

import json

# Metadata blob — must contain every key create_story reads, now incl. initial_state.
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
    "initial_state": {
        "stats": {"health": 100, "gold": 0},
        "inventory": ["lantern"],
        "relationships": {"The Oracle": 50},
        "flags": {},
    },
    "first_introduction_scene": {
        "text": "Tester stands at the root of the story tree.",
        "choice": {"text": "Step into the maze", "loading_text": "Entering the maze..."},
    },
}

EMPTY_STATE = {"stats": {}, "inventory": [], "relationships": {}, "flags": {}}

NORMAL_CHOICES = [
    {"text": "Continue forward", "loading_text": "Moving on...", "is_wrong": False, "is_final": False},
    {"text": "Touch the cursed idol", "loading_text": "That felt unwise...", "is_wrong": True, "is_final": False},
    {"text": "Approach the exit", "loading_text": "The end nears...", "is_wrong": False, "is_final": True},
]


def _last_assistant_state(messages):
    """Recover the world state from the most recent assistant turn (the parent scene)."""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            try:
                return json.loads(m["content"]).get("state", dict(EMPTY_STATE))
            except (json.JSONDecodeError, AttributeError):
                return dict(EMPTY_STATE)
    return dict(EMPTY_STATE)


def _evolve(prev: dict) -> tuple[dict, list]:
    """Deterministically advance the world state one step."""
    prev = prev or dict(EMPTY_STATE)
    inv = list(prev.get("inventory", []))
    relic = f"relic_{len(inv) + 1}"
    inv.append(relic)

    stats = dict(prev.get("stats", {}))
    stats["health"] = max(0, stats.get("health", 100) - 5)

    rels = dict(prev.get("relationships", {}))
    if rels:
        first = next(iter(rels))
        rels[first] = min(100, rels[first] + 5)

    flags = dict(prev.get("flags", {}))
    flags["step_taken"] = True

    state = {"stats": stats, "inventory": inv, "relationships": rels, "flags": flags}
    changes = [f"Picked up {relic}", "Health -5"]
    return state, changes


class FakeChatBot:
    def __init__(self, model_name="fake"):
        self.model_name = model_name
        self.calls = []
        self.metadata_calls = 0
        self.description_calls = 0
        self.scene_calls = 0
        self.queue = []

    def enqueue(self, raw: str):
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
        prev_state = _last_assistant_state(messages)

        if "ends the story due to this wrong decision" in last_user:
            return json.dumps({
                "text": "Your mistake catches up with you. Darkness.",
                "pacing": "resolution",
                "state": prev_state,
                "state_changes": ["You perished"],
                "choices": [{"text": "Game Over", "loading_text": "RIP", "is_wrong": False, "is_final": False}],
            })
        if "satisfying resolution" in last_user:
            return json.dumps({
                "text": "You reach the end of the tale, changed but whole.",
                "pacing": "resolution",
                "state": prev_state,
                "state_changes": ["The journey concludes"],
                "choices": [{"text": "The End", "loading_text": "Fin", "is_wrong": False, "is_final": False}],
            })

        # normal next scene: evolve the world state
        state, changes = _evolve(prev_state)
        return json.dumps({
            "text": "A new chamber of the maze unfolds before you.",
            "pacing": "rising",
            "state": state,
            "state_changes": changes,
            "choices": [dict(c) for c in NORMAL_CHOICES],
        })
