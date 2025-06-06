import json
import random
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


story_example = {
    "title": "Deep under ocean",
    "description": "Story about a deep-sea diver who discovers an ancient civilization and meets interesting creatures.",
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
    ],
    "emojis": ["🌊", "🐠", "🏴‍☠"],
    "worldview": {
        "setting": "The story takes place in the depths of the ocean, where Iroh discovers an ancient civilization and meets interesting creatures.",
        "timePeriod": "Modern day",
        "technologyLevel": "Advanced technology for diving and exploration, but the civilization is ancient.",
        "magicSystem": "The ocean has its own magic, with creatures and phenomena that defy explanation. The civilization has its own ancient magic that is tied to the ocean.",
    },
    "themes": ["Exploration", "Adventure", "Discovery", "Mystery", "Transformation"],
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
                "content": "Output the complete json (ONLY JSON) for interactive story quest with the following description: In the darkest depths of the ocean, Iroh the Diver stumbles upon the ruins of a long-lost civilization and unearths secrets guarded for millennia. Joined by mythical beings and a legendary captain, he must navigate ancient magic, monstrous guardians, and mysterious alliances to uncover the truth of Atlantis.",
            },
            {"role": "assistant", "content": json.dumps(story_example)},
            {
                "role": "user",
                "content": f"Output the complete json for interactive story quest with the following description: {description}",
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


USER_FIRST_MESSAGE_TEMPLATE = (
    "Generate the first scene (1/{n_scene_total}) with 1 choice!"
)
USER_MESSAGE_TEMPLATE = (
    'Player proceeds with "{choice}". '
    "Generate next scene ({n_scene}/{n_scene_total}) with {n_choices} ({n_wrong} of which are wrong) choice(s)!"
)
USER_FINAL_MESSAGE_TEMPLATE = (
    'Player proceeds with "{choice}". '
    "Generate final scene ({n_scene}/{n_scene_total}) with 1 choice to end the story!"
)
USER_FINAL_MESSAGE_DISASTER_TEMPLATE = (
    'Player proceeds with "{choice}". '
    "Generate scene ({n_scene}/{n_scene_total}) which ends the story abruptly due to an unexpected disaster! Add 1 choice to end the story, something like 'The End' or 'Game Over'."
)


async def continue_story_branch(
    chatbot: ChatBot, story: Story, scenes: List[Scene], choices: List[Choice]
) -> Tuple[dict, bool]:
    messages = [
        {
            "role": "system",
            "content": (
                "You're best story teller. Given the story metadata:\n"
                f"{story.model_dump()}\n\n(/no_think)\n"
                f"You will create a story with {story.n_scenes} scenes.\n"
                "IMPORTANT: you output only valid json of the following format:\n"
                '{"text": "<scene description>", "choices": [{"text": "<choice description>", "loading_text": "<your thoughts>"}, ...]}'
            ),
        },
    ]

    _scenes = scenes + [None]
    _choices = [None] + choices

    for i, (scene, selected_choice) in enumerate(zip(_scenes, _choices)):
        if selected_choice is None:  # i == 0:
            messages.append(
                {
                    "role": "user",
                    "content": USER_FIRST_MESSAGE_TEMPLATE.format(
                        n_scene_total=story.n_scenes
                    ),
                }
            )
        elif i == story.n_scenes - 1:
            messages.append(
                {
                    "role": "user",
                    "content": USER_FINAL_MESSAGE_TEMPLATE.format(
                        choice=selected_choice.text,
                        n_scene=i + 1,
                        n_scene_total=story.n_scenes,
                    ),
                }
            )
        elif scene:
            messages.append(
                {
                    "role": "user",
                    "content": USER_MESSAGE_TEMPLATE.format(
                        choice=selected_choice.text,
                        n_scene=i + 1,
                        n_scene_total=story.n_scenes,
                        n_choices=len(scene.choices),
                        n_wrong=len([c for c in scene.choices if c.is_wrong]),
                    ),
                }
            )

        if scene:
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "text": scene.text,
                            "choices": [
                                {
                                    "text": c.text,
                                    "loading_text": c.loading_text,
                                    "is_wrong": c.is_wrong,
                                }
                                for c in scene.choices
                            ],
                        }
                    ),
                }
            )
        else:
            if i != len(_scenes) - 1:
                raise ValueError(
                    f"Scene {i + 1} is None, but it should not be. Scenes: {len(_scenes)} (actually {len(scenes)})"
                )

    selected_choice = choices[-1]

    is_branch_over = False

    if len(_scenes) == story.n_scenes:
        is_branch_over = True
        messages.append(
            {
                "role": "user",
                "content": USER_FINAL_MESSAGE_TEMPLATE.format(
                    choice=selected_choice.text,
                    n_scene=len(_scenes),
                    n_scene_total=story.n_scenes,
                ),
            }
        )
    elif selected_choice.is_wrong:
        is_branch_over = True
        messages.append(
            {
                "role": "user",
                "content": USER_FINAL_MESSAGE_DISASTER_TEMPLATE.format(
                    choice=selected_choice.text,
                    n_scene=len(_scenes),
                    n_scene_total=story.n_scenes,
                ),
            }
        )
    else:
        is_branch_over = False
        n_choices = int(
            random.choices(
                list(story.choices_weights.keys()),
                weights=list(story.choices_weights.values()),
                k=1,
            )[0]
        )
        n_wrong = len(
            [random.random() < story.difficulty for _ in range(n_choices - 1)]
        )
        messages.append(
            {
                "role": "user",
                "content": USER_MESSAGE_TEMPLATE.format(
                    choice=selected_choice.text,
                    n_scene=len(_scenes),
                    n_scene_total=story.n_scenes,
                    n_choices=n_choices,
                    n_wrong=n_wrong,
                ),
            }
        )

    response = await chatbot.prompt(messages)

    for _ in range(10):
        try:
            return json.loads(response), is_branch_over
        except json.JSONDecodeError as e:
            messages.append({"role": "assistant", "content": response})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The json you output is invalid. \n{e}\n Retry!\n"
                        '{"text": "<scene description>", "choices": [{"text": "<choice description>", "loading_text": "<your thoughts>"}, ...]}'
                    ),
                }
            )
            response = await chatbot.prompt(messages)
    raise ValueError(
        f"Failed to parse response after 10 attempts: {response}\nMessages: {messages}"
    )
