import json
from typing import List, Tuple
from chatbots.chatbot import ChatBot
from db_models import Choice, Scene, Story


async def generate_description(chatbot: ChatBot):
    description = await chatbot.prompt(
        [
            {"role": "system", "content": "You're best story teller. (/no_think)"},
            {"role": "user", "content": "Give me 2-3 sentence story description"},
            {
                "role": "assistant",
                "content": "In the darkest depths of the ocean, Iroh the Diver stumbles upon the ruins of a long-lost civilization and unearths secrets guarded for millennia. Joined by mythical beings and a legendary captain, he must navigate ancient magic, monstrous guardians, and mysterious alliances to uncover the truth of Atlantis.",
            },
            {
                "role": "user",
                "content": "Give me another 2-3 sentence story description",
            },
        ]
    )
    return description


example_description = "In the darkest depths of the ocean, Iroh the Diver stumbles upon the ruins of a long-lost civilization and unearths secrets guarded for millennia. Joined by his loyal friend Taro, mythical beings, and a legendary captain, he must navigate ancient magic, monstrous guardians, and mysterious alliances to uncover the truth of Atlantis."

story_example = {
    "title": "Deep under ocean",
    "description": "Story about a deep-sea diver and his trusted friend who discover an ancient civilization and meet interesting creatures.",
    "main_character": {
        "name": "Iroh the Diver",
        "role": "Diver",
        "traits": ["brave", "curious", "adventurous"],
        "description": "A skilled diver who is determined to explore the depths of the ocean and uncover its secrets.",
    },
    "characters": [
        {
            "name": "Captain Nemo",
            "role": "Captain of the Nautilus",
            "traits": ["brave", "adventurous", "intelligent"],
            "description": "A legendary captain who has explored the ocean for years and knows its secrets. Not a normal human anymore.",
        },
        {
            "name": "Maria",
            "role": "Former Queen of Atlantis",
            "traits": ["wise", "mysterious", "elegant", "sexy", "passionate"],
            "description": "The former queen of Atlantis who has been transformed into a mermaid. She is wise and mysterious, with a deep connection to the ocean.",
        },
        {
            "name": "Monster of the Deep",
            "role": "Guardian of Atlantis",
            "traits": ["fearsome", "ancient", "powerful", "dangerous"],
            "description": "A fearsome creature that guards the entrance to Atlantis. It is ancient and powerful, with a deep connection to the ocean.",
        },
        {
            "name": "Taro",
            "role": "Iroh's Friend and Navigator",
            "traits": ["loyal", "resourceful", "playful"],
            "description": "A fellow diver and longtime friend of Iroh. He navigates treacherous currents with ease and lightens tense moments with his humor, always ready to support Iroh in every challenge.",
        },
    ],
    "emojis": ["🌊", "🐠", "🏴‍☠"],
    "worldview": {
        "setting": "The story takes place in the depths of the ocean, where Iroh discovers an ancient civilization and meets interesting creatures.",
        "timePeriod": "Modern day",
        "technologyLevel": "Advanced technology for diving and exploration, but the civilization is ancient.",
        "magicSystem": "The ocean has its own magic, with creatures and phenomena that defy explanation. The civilization has its own ancient magic that is tied to the ocean.",
    },
    "themes": ["Exploration", "Adventure", "Discovery", "Mystery", "Transformation"],
    "initial_state": {
        "stats": {"health": 100, "oxygen": 100, "gold": 0},
        "inventory": ["diving suit", "underwater flashlight"],
        # Only characters PRESENT at the very start — Taro is along for the dive;
        # Captain Nemo, Maria, etc. are added to relationships when first met.
        "relationships": {"Taro": 60},
        "flags": {"found_atlantis": False},
    },
    "first_introduction_scene": {
        "text": "Iroh the Diver checks his oxygen tanks one last time, the rusted gauges trembling under his thumb.{{break}}Above him the *Ariadne* rocks in the swell; below him, three thousand feet of black water and whatever rumour put him here.",
        "choice": {
            "text": "Dive into the ocean",
            "loading_text": "Diving into the ocean, let's see what we can find",
        },
    },
}


async def generate_story_metadata(chatbot: ChatBot, description: str):
    response = await chatbot.prompt(
        [
            {
                "role": "system",
                "content": "You only output valid JSON. (/no_think)",
            },
            {
                "role": "user",
                "content": f"Output the complete json (ONLY JSON) for interactive story quest with the following description: {example_description}.",
            },
            {"role": "assistant", "content": json.dumps(story_example)},
            {
                "role": "user",
                "content": f"Output the complete json (ONLY JSON) for interactive story quest with the following description: {description}. "
                "(include the same fields as previously, but matching the new description). "
                "In initial_state.relationships include ONLY characters present at the very start (e.g. a companion); "
                "others are added when the player meets them.",
            },
        ]
    )

    story_metadata = response

    try:
        return json.loads(story_metadata)
    except json.JSONDecodeError:
        try:
            return dict(story_metadata)
        except ValueError:
            return story_metadata


# Empty world state used when a story predates the feature or metadata omits it.
EMPTY_STATE = {"stats": {}, "inventory": [], "relationships": {}, "flags": {}}

# The exact JSON shape every scene generation must return. Stories with a
# pre-generated asset manifest also include a "stage" object (see _stage_block).
OUTPUT_SCHEMA = (
    '{"text": "<scene prose in markdown, second person. SPLIT into 2-4 short pages '
    'separated by the literal token {{break}} — each page is one dramatic beat '
    '(1-3 sentences). Use markdown emphasis (*italics*, **bold**) freely.>", '
    '"pacing": "setup|rising|climax|resolution", '
    '"state": {"stats": {"<name>": <number>}, "inventory": ["<item>"], '
    '"relationships": {"<character>": <int -100..100>}, "flags": {"<name>": <bool>}}, '
    '"state_changes": ["<short human-readable change, e.g. \'Found a brass key\' or \'Health -10\'>"], '
    '"stage": {"setting": "<one of the available settings>", '
    '"characters_present": [{"name": "<character>", "expression": "<one of available>"}]}, '
    '"choices": [{"text": "<choice>", "loading_text": "<in-character anticipation>", '
    '"is_wrong": <bool>, "is_final": <bool>}]}'
)


def _stage_block(story: Story) -> str:
    """Build the 'available settings + characters' prompt section, or '' if the
    story has no manifest. The model is told to pick STRICTLY from these lists
    so the frontend can resolve every value to a real PNG."""
    settings_map = story.backgrounds or {}
    sprites_map = story.character_sprites or {}
    if not settings_map and not sprites_map:
        return ""

    lines = [
        "\nVISUAL STAGE — every scene specifies which background and visible "
        "characters to render. Pick STRICTLY from the lists below; any value "
        "not in these lists will be silently dropped.",
    ]
    if settings_map:
        lines.append("Available SETTINGS (pick exactly one as stage.setting):")
        for sid, meta in settings_map.items():
            desc = (meta or {}).get("description", "")
            lines.append(f"  - {sid}: {desc}")
    if sprites_map:
        lines.append(
            "Available CHARACTERS in stage.characters_present (omit any not "
            "visibly on-screen in this scene). The protagonist is ALWAYS the "
            "POV and MUST NEVER appear here. Each entry: "
            '{"name": <character>, "expression": <one of: angry, sad, smiling, '
            "neutral, scared>}. Use at most 2 characters per scene; the same "
            "character should keep an expression that matches the moment."
        )
        for name in sprites_map:
            lines.append(f"  - {name}")
    return "\n".join(lines) + "\n"


def _difficulty_label(difficulty: float) -> str:
    if difficulty <= 0.2:
        return "easy"
    if difficulty <= 0.4:
        return "medium"
    if difficulty <= 0.8:
        return "hard"
    return "impossible"


def _current_state(story: Story, scenes: List[Scene]) -> dict:
    """The world state the next scene should evolve from."""
    if scenes and scenes[-1].state:
        return scenes[-1].state
    return story.initial_state or EMPTY_STATE


async def continue_story_branch(
    chatbot: ChatBot, story: Story, scenes: List[Scene], choices: List[Choice]
) -> Tuple[dict, bool]:
    difficulty = _difficulty_label(story.difficulty)
    target = story.n_scenes
    depth = len(scenes)  # scenes already materialized on this branch
    state = _current_state(story, scenes)

    # Trim the raw asset manifests from the metadata blob — they're large
    # JSON and we render a focused "Available settings/characters" block below.
    story_json = {
        k: v
        for k, v in story.model_dump().items()
        if k not in ("initial_state", "character_sprites", "backgrounds")
    }
    story_json["difficulty"] = difficulty

    system = (
        "You are a master interactive storyteller. Story metadata:\n"
        f"{story_json}\n\n"
        + _stage_block(story)
        + "PERSISTENT WORLD STATE — you maintain state across scenes:\n"
        "- stats: named numbers (e.g. health, gold, oxygen)\n"
        "- inventory: list of item names the player carries\n"
        "- relationships: character name -> integer standing (-100 hostile .. 100 devoted). "
        "ONLY include characters the player has actually MET. Add a character the first time "
        "they appear in a scene; never list characters not yet encountered.\n"
        "- flags: named booleans for story events that have happened\n"
        "Each scene you MUST return the FULL updated state (carry over unchanged "
        "values verbatim) plus a short 'state_changes' list describing what changed.\n\n"
        f"PACING — aim for a narrative arc of roughly {target} scenes, but YOU decide "
        "when the story resolves; end earlier or later as the story demands. Report the "
        "current phase via 'pacing' (setup -> rising -> climax -> resolution). As the arc "
        'nears its end, mark a concluding choice with "is_final": true.\n\n'
        f"DIFFICULTY ({difficulty}) — controls how often choices have downsides and how "
        "severe their consequences are. NEVER kill the player from a single wrong choice. "
        "Death (if it happens at all) emerges from accumulated state damage across many scenes.\n"
        "  easy:       rare downsides (~0-1 'is_wrong' per scene); small penalties (~5% stat hit); plenty of recovery (rest, supplies, NPC help).\n"
        "  medium:     occasional downsides (~1 per scene); moderate penalties (~10-15% stat hit); some recovery available.\n"
        "  hard:       frequent downsides (~1-2 per scene); heavy penalties (~20-30% stat hit, item loss); limited recovery.\n"
        "  impossible: most choices have downsides; severe penalties (~30-50% stat hit, multiple losses); almost no recovery.\n\n"
        "A choice marked \"is_wrong\": true is COSTLY but NOT fatal in itself — it imposes "
        "notable negative consequences (stat drop, item lost/broken, NPC turns hostile, fear "
        "spike, flag flips against the player) proportional to the difficulty above. The "
        "story CONTINUES; the next scene plays out the cost narratively.\n\n"
        "STATE BALANCE — not every scene should worsen the situation. Smart or savvy choices "
        "MUST produce positive state changes: relief (fear DOWN), found items, allies gained, "
        "useful information (flag flips in the player's favor), restored stats. Aim for at "
        "least one recovery beat every 3-4 scenes — without these moments the story becomes "
        "unwinnable and the player has no agency. Reward smart play.\n\n"
        "RESOLUTION can go MULTIPLE ways — choose what fits the player's accumulated state and "
        "choices: VICTORY (escape, rescue, mystery solved, threat defeated), TRANSFORMATION "
        "(changed but alive, a new equilibrium), or LOSS (death/failure when a vital stat is "
        "depleted across the arc). Do NOT default to doom; positive endings are equally valid. "
        'Mark the concluding choice with "is_final": true regardless of which ending type.\n\n'
        "Write in the second person, present tense, from the main character's view.\n\n"
        "FORMATTING — the 'text' field is markdown that you SPLIT into pages with the "
        "literal token {{break}}. Aim for 2-4 pages per scene; each page is a single "
        "dramatic beat of 1-3 sentences. The reader clicks through pages before reaching "
        "the choices, so end each page on a hook or image that invites the next click. "
        "Do NOT put {{break}} at the very start or end of the text. Markdown emphasis is "
        "fine; do NOT use markdown headings or code blocks.\n\n"
        "Output ONLY valid JSON of this exact shape (no markdown, no prose outside JSON):\n"
        + OUTPUT_SCHEMA
    )
    messages = [{"role": "system", "content": system}]

    # Replay the branch as a real conversation so the model sees how the world
    # state and narrative have evolved. Each historical scene -> one assistant turn.
    for i, scene in enumerate(scenes):
        if i == 0:
            messages.append({"role": "user", "content": "Begin the story. Generate the opening scene."})
        else:
            chosen = choices[i - 1].text
            messages.append({"role": "user", "content": f'The player chose "{chosen}". Continue.'})
        history_turn: dict = {
            "text": scene.text,
            "pacing": scene.pacing or "rising",
            "state": scene.state or EMPTY_STATE,
            "state_changes": scene.state_changes or [],
            "choices": [
                {
                    "text": c.text,
                    "loading_text": c.loading_text,
                    "is_wrong": c.is_wrong,
                    "is_final": c.is_pre_final,
                }
                for c in scene.choices
            ],
        }
        if scene.stage:
            history_turn["stage"] = scene.stage
        messages.append({"role": "assistant", "content": json.dumps(history_turn)})

    selected_choice = choices[-1]
    state_json = json.dumps(state)
    force_final = depth >= target  # hard cap: stories must terminate

    if selected_choice.is_pre_final or force_final:
        is_branch_over = True
        instruction = (
            f'The player chose "{selected_choice.text}". Current world state: {state_json}. '
            "Bring the story to a satisfying resolution NOW: generate the final scene with a "
            'single concluding choice (e.g. "The End"). Update the world state and set '
            '"pacing":"resolution".'
        )
    else:
        is_branch_over = False
        scene_n = depth + 1
        if selected_choice.is_wrong:
            instruction = (
                f'The player chose "{selected_choice.text}", a COSTLY choice. Current world state: '
                f"{state_json}. Apply meaningful negative consequences to the world state, proportional "
                f"to {difficulty} difficulty — stat drops, lost/broken items, hostile NPC reactions, "
                "fear spikes, story flags flipping against the player. Show the cost playing out "
                "narratively in this scene. The story CONTINUES; do NOT end it unless a vital stat is "
                'already at 0 — in that case end via a concluding choice with "is_final": true. '
                f"This is roughly scene {scene_n} of a ~{target}-scene arc. Offer 1-3 new choices."
            )
        else:
            instruction = (
                f'The player chose "{selected_choice.text}". Current world state: {state_json}. '
                f"This is roughly scene {scene_n} of a ~{target}-scene arc. Generate the next scene, "
                "updating the world state to reflect this choice's OUTCOMES — which may be positive "
                "(relief, items, allies, useful intel) OR negative (penalties, threats), depending on "
                "how smart the choice was. Offer 1-3 intriguing choices, some marked is_wrong per "
                f"{difficulty} difficulty (costly, not deadly). If the story is reaching its natural "
                'climax/resolution, mark a concluding choice with "is_final": true.'
            )
    messages.append({"role": "user", "content": instruction})

    response = await chatbot.prompt(messages)

    for _ in range(10):
        try:
            parsed = json.loads(response)
            parsed.setdefault("state", state)
            parsed.setdefault("state_changes", [])
            parsed.setdefault("pacing", "resolution" if is_branch_over else "rising")
            return parsed, is_branch_over
        except json.JSONDecodeError as e:
            messages.append({"role": "assistant", "content": response})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The json you output is invalid.\n{e}\nRetry — output ONLY this JSON:\n"
                        + OUTPUT_SCHEMA
                    ),
                }
            )
            response = await chatbot.prompt(messages)
    raise ValueError(
        f"Failed to parse response after 10 attempts: {response}\nMessages: {messages}"
    )
