import json
import re
from typing import List, Optional, Tuple
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
    "art_style": (
        "Anime-illustration style, clean lines, soft cel shading, slightly "
        "desaturated deep-ocean palette (midnight blue, brass, slate-grey, "
        "with faint amber bioluminescence accents)."
    ),
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
            # Visual brief for Nano Banana — describe outfit, build, hair,
            # palette anchors, distinguishing features. NO pose grid here;
            # the code appends that scaffolding.
            "art_prompt": (
                "Captain Nemo, a man in his late fifties with weather-beaten "
                "salt-tanned skin, deep-set steel-grey eyes, a thick salt-and-"
                "pepper beard trimmed close, and a long faintly-glowing scar "
                "running from his right temple down past his ear (the ocean's "
                "magic re-shaped him). He wears a navy-blue captain's coat with "
                "tarnished brass buttons and a high collar, a worn white cotton "
                "shirt with rolled sleeves, dark canvas trousers tucked into "
                "seasoned leather sea-boots, and a battered captain's hat with "
                "a brass anchor pin."
            ),
            "position": "right",
            "poses": {
                "angry": "shoulders squared, fists at his sides, jaw set under the beard",
                "sad": "head bowed, one hand resting on the hat held against his chest",
                "smiling": "small wry half-smile, weight on one leg, hands clasped behind back",
                "neutral": "hands behind his back, captain's parade stance, watching",
                "scared": "eyes wide, half-step back, one hand raised palm-out",
            },
        },
        {
            "name": "Maria",
            "role": "Former Queen of Atlantis",
            "traits": ["wise", "mysterious", "elegant", "passionate"],
            "description": "The former queen of Atlantis who has been transformed into a mermaid. She is wise and mysterious, with a deep connection to the ocean.",
            "art_prompt": (
                "Maria, a woman in her early thirties of timeless ageless beauty, "
                "with long flowing silver-blue hair shot through with strands of "
                "kelp, luminous sea-green eyes, and pale opalescent skin that "
                "shimmers faintly. From the waist down a long iridescent "
                "blue-green mermaid tail with translucent fins; from the waist "
                "up a fitted top of woven seaweed and small pearls. A delicate "
                "coral crown rests above her brow, and barnacled silver bracelets "
                "ring her wrists."
            ),
            "position": "left",
            "poses": {
                "angry": "tail curled tight, fists clenched, glare like a deep current",
                "sad": "tail drifting low, one hand to her chest, eyes downcast",
                "smiling": "a slow knowing half-smile, head tilted, hair drifting",
                "neutral": "weight balanced, hands clasped at the waist, watching",
                "scared": "tail tense beneath her, both hands raised defensively",
            },
        },
        {
            "name": "Taro",
            "role": "Iroh's Friend and Navigator",
            "traits": ["loyal", "resourceful", "playful"],
            "description": "A fellow diver and longtime friend of Iroh. He navigates treacherous currents with ease and lightens tense moments with his humor, always ready to support Iroh in every challenge.",
            "art_prompt": (
                "Taro, a man in his early thirties with a friendly weather-tanned "
                "face, short messy black hair, dark almond-shaped eyes, and a "
                "quick easy grin. He wears a streamlined modern diving suit in "
                "slate grey and orange high-vis trim, a chest-mounted dive "
                "computer, a pair of fins clipped to his belt, and a small "
                "underwater flashlight on a lanyard around his neck. A nautical "
                "compass tattoo on his right forearm."
            ),
            "position": "center",
            "poses": {
                "angry": "fists clenched, brow furrowed, leaning slightly forward",
                "sad": "shoulders slumped, hand on the back of his neck, eyes down",
                "smiling": "broad open-mouth grin, thumbs hooked in his belt",
                "neutral": "one hand on hip, easy weight on one leg",
                "scared": "eyes wide, both hands raised in front of his chest",
            },
        },
    ],
    "settings": [
        {
            "id": "ship_deck_dawn",
            "description": "The deck of the diving ship Ariadne at dawn — the launching point of every expedition.",
            "art_prompt": (
                "The wooden deck of a modern small dive-research ship at dawn, "
                "viewed from amidships. Coils of orange rope, scuba tanks lined "
                "up in a rack, a yellow inflatable RIB lashed to the rail, a "
                "small wooden chart table under a canvas awning, dive gear "
                "draped over a bench. The sea is mirror-flat and lavender-pink "
                "in the dawn light; a thin mist drifts low over the water. "
                "Empty, anticipatory."
            ),
        },
        {
            "id": "deep_trench",
            "description": "The black water of an oceanic trench, far from any light — where the descent begins.",
            "art_prompt": (
                "A vast underwater chasm in deep ocean water, viewed from above "
                "looking down into total darkness. The cliffs of the trench fade "
                "from slate-blue at the top into pure black. A few faint amber "
                "bioluminescent specks drift in the dark. No light source except "
                "a single distant glow far below. Vast, cold, ancient."
            ),
        },
        {
            "id": "nautilus_bridge",
            "description": "The brass-and-mahogany bridge of the Nautilus, lit by amber gas-lamps.",
            "art_prompt": (
                "The interior bridge of a Victorian-era ornate submarine, all "
                "polished mahogany panelling and tarnished brass. A large "
                "ship's wheel mounted on a brass pedestal in the centre. "
                "Glass-fronted dials and gauges inlaid into the walls. "
                "Circular porthole windows showing dark deep water outside. "
                "Amber gas-lamp light pools warmly over leather-bound charts on "
                "a central table. Empty, atmospheric, hushed."
            ),
        },
        {
            "id": "atlantis_ruins",
            "description": "The sunken plaza of Atlantis — pale marble overgrown with coral and kelp.",
            "art_prompt": (
                "The submerged plaza of an ancient sunken city, viewed in deep "
                "blue water. Pale weathered marble columns lean at angles, "
                "draped with red and purple coral and long kelp fronds. A "
                "broken statue of a robed figure missing its head sits on a "
                "tilted pedestal. Shoals of small silver fish drift through. "
                "Sunlight filters down in pale shifting beams from far above. "
                "Vast, silent, beautiful."
            ),
        },
        {
            "id": "monster_lair",
            "description": "A flooded undersea cavern where the Monster of the Deep makes its home.",
            "art_prompt": (
                "A vast underwater rock cavern lit by a small cluster of "
                "bioluminescent fungi clinging to the ceiling, casting cold "
                "blue-green light. The cavern floor is strewn with broken ship "
                "hulls and the bleached bones of huge sea creatures. Massive "
                "claw-marks score the walls. Dark water fills the chamber; the "
                "ceiling vanishes into shadow. Empty (the monster is offscreen), "
                "menacing, primeval."
            ),
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
        # Optional — if present, used to seed the root scene's visual stage so
        # the very first page already has a background. Pick an id from the
        # settings list above (and any characters present at the very start).
        "stage": {"setting": "ship_deck_dawn", "characters_present": []},
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
                "content": (
                    "You only output valid JSON for an interactive visual-novel "
                    "story. Two things matter most:\n"
                    "  1. Narrative fields (description, characters[].description, "
                    "worldview, themes, initial_state) shape how the story plays.\n"
                    "  2. Visual fields (art_style, characters[].art_prompt, "
                    "characters[].poses, settings[].art_prompt) are fed verbatim "
                    "to a Nano Banana image model. They MUST be richly specific: "
                    "anchored to concrete visible objects (outfit fabric, hair "
                    "colour, scar locations, lighting palette, exact framing). "
                    "Generic prose like 'a mysterious cottage' will produce "
                    "unusable art. Match the level of detail in the example. "
                    "(/no_think)"
                ),
            },
            {
                "role": "user",
                "content": f"Output the complete json (ONLY JSON) for interactive story quest with the following description: {example_description}.",
            },
            {"role": "assistant", "content": json.dumps(story_example)},
            {
                "role": "user",
                "content": (
                    f"Output the complete json (ONLY JSON) for interactive story "
                    f"quest with the following description: {description}. "
                    "Include EVERY field shown in the example: title, description, "
                    "art_style, main_character, characters (with art_prompt, "
                    "position, poses for each), settings (4-6 entries, each with "
                    "id/description/art_prompt), emojis, worldview, themes, "
                    "initial_state, first_introduction_scene. "
                    "In initial_state.relationships include ONLY characters "
                    "present at the very start (a companion etc.); others get "
                    "added when the player meets them. "
                    "Settings ids are lowercase_snake_case slugs; pick 4-6 "
                    "locations that the story will plausibly visit. "
                    "Art prompts MUST be as detailed as the example's — describe "
                    "outfits with fabric + colour, hair + eye colour + age. "
                    "Skip art_prompt for main_character (player POV is never "
                    "shown on screen).\n\n"
                    "CRITICAL CHARACTER ART_PROMPT RULE: characters[].art_prompt "
                    "MUST describe ONLY the character — face, body, hair, "
                    "clothing, distinguishing physical features. It must NEVER "
                    "include lighting, environment, scene context, or anything "
                    "spatial behind the character (no 'lit by hearthfire', no "
                    "'behind her a pine forest', no 'amber dusk through the "
                    "window'). Those belong in settings[].art_prompt or "
                    "art_style. Reason: each character is rendered on a plain "
                    "white sprite sheet across five poses; any scene context in "
                    "the prompt makes the image generator paint a backdrop, "
                    "which then bleeds between figures and breaks sprite "
                    "extraction. Keep character prompts 100% character-only."
                ),
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


# Matches the inline stage tokens in scene prose: {{enter:X}}, {{enter:X/expr}},
# {{exit:X}}, {{expression:X/expr}}, {{setting:X}}. Order-preserving via finditer.
_STAGE_TOKEN_RE = re.compile(r"\{\{(enter|exit|expression|setting):([^}]+)\}\}")


def _end_of_scene_state(scene: Scene) -> Tuple[List[dict], Optional[str]]:
    """Replay a scene's inline tokens to compute who is on stage / where, at the
    very end of the scene's text.

    The model is given this as a continuity hint when generating the NEXT scene,
    so it doesn't drop characters who were clearly mid-conversation. Without
    this, the model frequently emits an empty `characters_present` for scene
    N+1 even when its prose continues seamlessly from scene N (the "Known
    limitation" called out in CLAUDE.md).
    """
    if not scene or not scene.stage or not scene.text:
        return [], None
    roster: List[dict] = []
    for entry in (scene.stage.get("characters_present") or []):
        if isinstance(entry, str):
            roster.append({"name": entry, "expression": "neutral"})
        elif isinstance(entry, dict) and entry.get("name"):
            roster.append({
                "name": entry["name"],
                "expression": entry.get("expression") or "neutral",
            })
    setting = scene.stage.get("setting")

    for m in _STAGE_TOKEN_RE.finditer(scene.text):
        kind, body = m.group(1), m.group(2).strip()
        if kind == "setting":
            if body:
                setting = body
        elif kind == "enter":
            name, _, expr = body.partition("/")
            name = name.strip()
            expr = expr.strip() or "neutral"
            if not name:
                continue
            roster = [r for r in roster if r["name"] != name]
            roster.append({"name": name, "expression": expr})
        elif kind == "exit":
            name = body.strip()
            roster = [r for r in roster if r["name"] != name]
        elif kind == "expression":
            name, _, expr = body.partition("/")
            name, expr = name.strip(), expr.strip()
            if not name or not expr:
                continue
            for r in roster:
                if r["name"] == name:
                    r["expression"] = expr
    return roster, setting


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
            "Available CHARACTERS for stage.characters_present and the inline "
            "tokens below (omit any not visibly on-screen). The protagonist is "
            "ALWAYS the POV and MUST NEVER appear in either. Use at most 2 "
            "characters on stage at the same time."
        )
        for name in sprites_map:
            lines.append(f"  - {name}")
        lines.append(
            "\nSTAGE TIMING — sprites AND backgrounds should change with the prose, "
            "not stay glued through the whole scene. `stage.characters_present` is "
            "ONLY the page-1 roster, and `stage.setting` is ONLY the page-1 background. "
            "STRICT RULES:\n"
            "  - If you use `{{enter:Name}}` anywhere in the text, that character MUST "
            "NOT be in `stage.characters_present` — the enter token means they walk on "
            "at that moment, so they can't also be there from the start. If the "
            "protagonist is alone before anyone arrives, leave `characters_present` empty.\n"
            "  - CONTINUITY ACROSS SCENES: if your new scene's prose continues "
            "directly from where the previous scene left off (same room, no time skip, "
            "conversation still active), `stage.characters_present` MUST include "
            "whoever was on stage at the end of that previous scene — otherwise the "
            "sprite vanishes mid-conversation. The per-scene CONTINUITY HINT below "
            "tells you who and where; honour it unless your prose explicitly moves "
            "the camera elsewhere or skips ahead in time.\n"
            "  - If the scene's prose crosses LOCATIONS (e.g. cottage -> path -> "
            "lighthouse), `stage.setting` is the FIRST location and you MUST drop "
            "`{{setting:X}}` tokens to swap the background as the prose moves. Don't "
            "pick the final location as `stage.setting` if pages 1-2 happen elsewhere.\n"
            "After page 1, embed inline tokens INSIDE the text to walk the roster + "
            "background forward:\n"
            "  {{enter:Name}}              - Name walks on, neutral expression\n"
            "  {{enter:Name/expression}}    - Name walks on with a specific expression\n"
            "  {{exit:Name}}                - Name leaves the stage\n"
            "  {{expression:Name/expression}} - Name (already on stage) changes mood\n"
            "  {{setting:setting_id}}       - swap the background to that setting\n"
            "Valid expressions: angry, sad, smiling, neutral, scared.\n"
            "Tokens are stripped before the reader sees the page — place each one at "
            "the EXACT moment of the change. Examples:\n"
            "  - Scene opens with Anouk alone, Iwan knocks and enters scared:\n"
            "      stage: {\"setting\": \"cottage_interior_night\", \"characters_present\": []}\n"
            "      text:  \"You sit by the fire, alone.{{break}}A knock at the door.\n"
            "             {{break}}{{enter:Iwan/scared}}Iwan steps in, soaked through.\"\n"
            "  - A scene that crosses locations (cottage -> cliffs -> lighthouse door):\n"
            "      stage: {\"setting\": \"cottage_interior_night\", \"characters_present\": []}\n"
            "      text:  \"You wind the scarf around your neck and step out into the dark.\n"
            "             {{break}}{{setting:cliffs_storm}}The path is muddy and treacherous,\n"
            "             the lighthouse beam sweeping overhead.\n"
            "             {{break}}{{setting:lighthouse_exterior}}You reach the keeper's door\n"
            "             and raise your hand to knock.\n"
            "             {{break}}{{enter:Iwan/neutral}}He answers almost immediately.\"\n"
        )
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
    # Continuity hint: tell the model who was on stage / where at the end of
    # the previous scene so it doesn't accidentally drop the cast. See
    # _end_of_scene_state. Only emitted when the story has a manifest (no
    # point hinting about sprites in an unvisualised story).
    if (story.character_sprites or story.backgrounds) and scenes:
        roster_end, setting_end = _end_of_scene_state(scenes[-1])
        if roster_end or setting_end:
            hint_parts = []
            if roster_end:
                hint_parts.append(
                    "on stage: "
                    + ", ".join(f"{r['name']} ({r['expression']})" for r in roster_end)
                )
            if setting_end:
                hint_parts.append(f"setting: {setting_end}")
            instruction = (
                "CONTINUITY HINT — at the very end of the previous scene, "
                + "; ".join(hint_parts)
                + ". If your new scene continues seamlessly (same beat, no "
                "time skip), your stage.setting and stage.characters_present "
                "should reflect that starting point — NOT empty. If you DO "
                "want a fresh beat (time skip, location change, characters "
                "dispersed), pick the appropriate setting + roster and ignore "
                "this hint.\n\n"
                + instruction
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
