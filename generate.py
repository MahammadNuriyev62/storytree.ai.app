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
        "relationships": {"Taro": 60, "Captain Nemo": 10, "Maria": 0},
        "flags": {"found_atlantis": False},
    },
    "first_introduction_scene": {
        "text": "Iroh the Diver is preparing for his dive into the depths of the ocean. He is excited and nervous, knowing that he is about to embark on an adventure of a lifetime.",
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
                "(include the same fields as previously, but matching the new description)",
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

# The exact JSON shape every scene generation must return.
OUTPUT_SCHEMA = (
    '{"text": "<scene prose, second person>", '
    '"pacing": "setup|rising|climax|resolution", '
    '"state": {"stats": {"<name>": <number>}, "inventory": ["<item>"], '
    '"relationships": {"<character>": <int -100..100>}, "flags": {"<name>": <bool>}}, '
    '"state_changes": ["<short human-readable change, e.g. \'Found a brass key\' or \'Health -10\'>"], '
    '"choices": [{"text": "<choice>", "loading_text": "<in-character anticipation>", '
    '"is_wrong": <bool>, "is_final": <bool>}]}'
)


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

    story_json = {k: v for k, v in story.model_dump().items() if k != "initial_state"}
    story_json["difficulty"] = difficulty

    system = (
        "You are a master interactive storyteller. Story metadata:\n"
        f"{story_json}\n\n"
        "PERSISTENT WORLD STATE — you maintain state across scenes:\n"
        "- stats: named numbers (e.g. health, gold, oxygen)\n"
        "- inventory: list of item names the player carries\n"
        "- relationships: character name -> integer standing (-100 hostile .. 100 devoted)\n"
        "- flags: named booleans for story events that have happened\n"
        "Each scene you MUST return the FULL updated state (carry over unchanged "
        "values verbatim) plus a short 'state_changes' list describing what changed.\n\n"
        f"PACING — aim for a narrative arc of roughly {target} scenes, but YOU decide "
        "when the story resolves; end earlier or later as the story demands. Report the "
        "current phase via 'pacing' (setup -> rising -> climax -> resolution). As the arc "
        'nears its end, mark a concluding choice with "is_final": true.\n\n'
        f"Some choices may be 'wrong' dead-ends according to difficulty: {difficulty}.\n"
        "Write in the second person, present tense, from the main character's view.\n"
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
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    {
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
                ),
            }
        )

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
    elif selected_choice.is_wrong:
        is_branch_over = True
        instruction = (
            f'The player chose "{selected_choice.text}" — a fatal mistake. Current world state: '
            f"{state_json}. Generate a scene that ends the story due to this wrong decision, with a "
            'single choice like "Game Over". Reflect the failure in the world state.'
        )
    else:
        is_branch_over = False
        instruction = (
            f'The player chose "{selected_choice.text}". Current world state: {state_json}. '
            f"This is roughly scene {depth + 1} of a ~{target}-scene arc. Generate the next scene, "
            "updating the world state to reflect the choice's consequences. Offer 1-3 intriguing "
            f"choices, some 'wrong' per {difficulty} difficulty. If the story is reaching its natural "
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
