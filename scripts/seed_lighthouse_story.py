"""Seed *The Lighthouse in Winter* into the DB with its asset manifest.

Bypasses the LLM-based metadata generator in `api.create_story` so the canonical
character + setting names line up exactly with `ml/images/lighthouse_assets`.

Idempotent: if a story with the same title already exists we update it in place
(and overwrite the root scene + root choice), so re-running while iterating on
prompts or assets is safe.

  python -m scripts.seed_lighthouse_story
"""

from typing import cast

from sqlmodel import Session, select, delete

from db_models import Choice, Scene, Story, engine
from ml.images.lighthouse_assets import wire_uploads

TITLE = "The Lighthouse in Winter"

# Pre-baked metadata. Matches what the LLM-generator would produce, but the
# character names and setting language are pinned so the asset manifest keys
# stay valid forever (no drift between the prompt and the on-disk PNGs).
METADATA: dict = {
    "title": TITLE,
    "description": (
        "Anouk, recently widowed, retreats alone to a remote cottage on the "
        "storm-battered Cornish coast to grieve. The lighthouse keeper next "
        "door, Iwan, has lived in his own silence for years. Through a long "
        "winter of small kindnesses, sharp-tongued shopkeeper Morvah, and the "
        "lingering memory of her late husband Henk, Anouk has to decide what "
        "kind of person she becomes on the other side of grief — and whether "
        "the door to her heart is closed for good."
    ),
    "user_given_description": (
        "A quiet, intimate love-after-loss story set on the winter Cornish "
        "coast. A widow and a widowed lighthouse keeper, slowly."
    ),
    "emojis": ["🌊", "🕯", "🏚"],
    "themes": ["Grief", "Quiet intimacy", "Solitude", "Coastal winter", "Second chances"],
    "main_characters": [
        {
            "name": "Anouk",
            "role": "Recently widowed writer",
            "traits": ["observant", "guarded", "kind", "perceptive"],
            "description": (
                "A woman in her late thirties, recently widowed, who has come "
                "to the Cornish coast alone to begin again. The story is told "
                "from her point of view — she is the reader and is not shown "
                "on screen."
            ),
        }
    ],
    "characters": [
        {
            "name": "Iwan",
            "role": "Lighthouse keeper, widower",
            "traits": ["quiet", "watchful", "steady", "tender beneath the salt"],
            "description": (
                "The lighthouse keeper next door. Early forties, weatherworn, "
                "has lived alone since his wife died years ago. Slow to speak, "
                "slower to trust, but the kind of man who notices everything."
            ),
        },
        {
            "name": "Morvah",
            "role": "Keeper of the village shop",
            "traits": ["sharp-tongued", "shrewd", "secretly kind", "observant"],
            "description": (
                "Early sixties, widowed years ago, runs the only shop in the "
                "village. She knows everyone's business and pretends not to. "
                "Pushes Anouk in the direction of the world without ever "
                "quite admitting that's what she's doing."
            ),
        },
        {
            "name": "Henk",
            "role": "Anouk's late husband (memory)",
            "traits": ["warm", "intelligent", "gentle", "present"],
            "description": (
                "Anouk's late husband, who appears in memories and dreams. He "
                "is depicted as he was before his long illness — healthy, "
                "kind, attentive. He is not alive in the world of the story; "
                "he is the love Anouk is grieving."
            ),
        },
    ],
    "worldview": {
        "setting": (
            "A remote village on the Cornish coast in midwinter. A weathered "
            "stone cottage, a working lighthouse on the headland, a single "
            "village shop, cliffs that drop sheer to a grey, restless sea."
        ),
        "timePeriod": "Present day",
        "technologyLevel": "Modern, but the village runs slow — woodstoves, oil lamps, postcards.",
        "magicSystem": "None. The only magic is weather, memory, and small human gestures.",
    },
    "initial_state": {
        # Quiet, internal stats — this isn't a survival story.
        "stats": {"warmth": 40, "courage": 30, "grief": 90},
        "inventory": ["Henk's old wool scarf", "a half-finished notebook"],
        # Empty at start — Anouk has not met anyone yet.
        "relationships": {},
        "flags": {
            "met_iwan": False,
            "met_morvah": False,
            "spoke_of_henk": False,
            "let_someone_in": False,
        },
    },
    "first_introduction_scene": {
        "text": (
            "You stand in the doorway of the cottage with your suitcase still in "
            "your hand. The fire someone has laid in the stove hasn't been lit; the "
            "air smells of cold stone and the sea.{{break}}"
            "Outside, the lighthouse on the headland is just turning its eye — a "
            "slow, steady sweep across the dusk. You came here to be alone with "
            "what's left of you. Now you're here, and the door is still open behind "
            "you."
        ),
        "choice": {
            "text": "Close the door, light the fire, and stay.",
            "loading_text": "You set the suitcase down. The latch clicks behind you...",
        },
    },
    # The root scene is Anouk arriving alone in the cottage — late afternoon
    # light leaning toward dusk. Closest match in our asset library.
    "first_introduction_stage": {
        "setting": "cottage_interior_day",
        "characters_present": [],
    },
}


def seed(n_scenes: int = 12, difficulty: float = 0.25) -> int:
    """Insert (or refresh) the story + root scene + root choice. Returns story id."""
    with Session(engine) as session:
        # Find or create the story shell.
        existing = session.exec(select(Story).where(Story.title == TITLE)).first()
        if existing is None:
            story = Story(
                title=METADATA["title"],
                description=METADATA["description"],
                user_given_description=METADATA["user_given_description"],
                emojis=METADATA["emojis"],
                themes=METADATA["themes"],
                main_characters=METADATA["main_characters"],
                characters=METADATA["characters"],
                worldview=METADATA["worldview"],
                initial_state=METADATA["initial_state"],
                n_scenes=n_scenes,
                difficulty=difficulty,
            )
            session.add(story)
            session.commit()
            story_id = cast(int, story.id)
            print(f"created story id={story_id}")
        else:
            story = existing
            # Refresh metadata in place so re-runs pick up edits.
            for k in (
                "description", "user_given_description", "emojis", "themes",
                "main_characters", "characters", "worldview", "initial_state",
            ):
                setattr(story, k, METADATA[k])
            story.n_scenes = n_scenes
            story.difficulty = difficulty
            story_id = cast(int, story.id)
            print(f"updating existing story id={story_id}")

        # Wire on-disk assets and pin the manifest to the story.
        manifest = wire_uploads(story_id)
        story.character_sprites = manifest["character_sprites"]
        story.backgrounds = manifest["backgrounds"]
        session.add(story)
        session.commit()

        # Wipe the existing scene tree for this story — easiest way to keep
        # re-runs clean when iterating on the opening scene / prompt changes.
        scene_ids = session.exec(
            select(Scene.id).where(Scene.story_id == story_id)
        ).all()
        if scene_ids:
            session.exec(delete(Choice).where(Choice.scene_id.in_(scene_ids)))
            session.exec(delete(Scene).where(Scene.story_id == story_id))
            session.commit()
            print(f"wiped {len(scene_ids)} existing scenes")

        # Lay down the root scene + an empty child + the opening choice.
        first = METADATA["first_introduction_scene"]
        root_scene = Scene(
            story_id=story_id,
            text=first["text"],
            state=METADATA["initial_state"],
            state_changes=[],
            pacing="setup",
            stage=METADATA["first_introduction_stage"],
        )
        child_scene = Scene(story_id=story_id)
        session.add(root_scene)
        session.add(child_scene)
        session.commit()

        root_choice = Choice(
            text=first["choice"]["text"],
            loading_text=first["choice"]["loading_text"],
            scene_id=cast(int, root_scene.id),
            next_scene_id=cast(int, child_scene.id),
        )
        session.add(root_choice)
        session.commit()
        print(f"seeded root scene id={root_scene.id} -> child id={child_scene.id}")

    return story_id


if __name__ == "__main__":
    sid = seed()
    print(f"\ndone. open the story at:  http://localhost:8000/app/story/{sid}")
