from typing import List, Optional
from pydantic import BaseModel, Field

from db_models import Character


class CreateStory(BaseModel):
    description: str = Field(
        description="A brief description of the story. "
        "This will be used to generate the story metadata.",
        min_length=10,
        default="In the heart of a forgotten jungle, a rogue archaeologist discovers a hidden temple filled with ancient scrolls that reveal a lost kingdom and a powerful artifact. Alongside a cunning thief and a haunted historian, they must outwit a ruthless cult and uncover the truth behind the kingdom'''s disappearance.",
    )
    n_scenes: int = Field(
        default=50,
        ge=1,
        description="Length of the story in scenes. Must be at least 1.",
    )
    difficulty: float = Field(
        default=0.2,
        ge=0,
        le=1,
        description="Difficulty of the story, ranging from 0 to 1. "
        "A higher value indicates a more challenging story.",
    )


class ChoiceDto(BaseModel):
    id: int = Field(
        description="The unique identifier for the choice.",
        ge=1,
    )
    text: str = Field(
        description="The text of the choice that the player can make.",
        min_length=1,
    )
    loading_text: str = Field(
        description="Text to display while the next scene is being generated.",
        default="Generating next scene...",
    )
    next_scene_id: Optional[int] = Field(
        description="The ID of the next scene that will be shown if this choice is selected.",
        ge=1,
    )


class SceneDto(BaseModel):
    id: int = Field(
        description="The unique identifier for the scene.",
        ge=1,
    )
    text: str = Field(
        description="The text of the scene, describing the setting, characters, and events.",
        min_length=1,
    )
    choices: List[ChoiceDto] = Field(
        description="A list of choices available in this scene.",
        default_factory=list,
    )

    class Config:
        orm_mode = True


class StoryDto(BaseModel):
    id: int
    title: str
    description: str
    emojis: List[str] = Field(
        description="A list of emojis representing the story.",
        default_factory=list,
        examples=[["🌴", "🗿", "🔍"]],
    )


class StoriesDto(BaseModel):
    stories: List[StoryDto] = Field(
        description="A list of stories.",
        default_factory=list,
    )


class StoryDetailsDto(StoryDto):
    characters: List[Character] = Field(
        description="A list of characters in the story.",
        default_factory=list,
        examples=[
            [
                {
                    "name": "Aria",
                    "role": "Protagonist",
                    "traits": ["brave", "curious"],
                    "description": "A young archaeologist with a passion for uncovering ancient secrets.",
                },
                {
                    "name": "Liam",
                    "role": "Antagonist",
                    "traits": ["cunning", "ruthless"],
                    "description": "A rival archaeologist who will stop at nothing to claim the artifact for himself.",
                },
            ]
        ],
    )
    emojis: List[str] = Field(
        description="A list of emojis representing the story.",
        default_factory=list,
        examples=[["🌴", "🗿", "🔍"]],
    )
    main_characters: List[Character] = Field(
        description="A list of main characters in the story.",
        default_factory=list,
        examples=[
            [
                {
                    "name": "Aria",
                    "role": "Protagonist",
                    "traits": ["brave", "curious"],
                    "description": "A young archaeologist with a passion for uncovering ancient secrets.",
                }
            ]
        ],
    )
    worldview: dict = Field(
        description="The worldview of the story, including its setting and rules.",
        default_factory=dict,
        examples=[
            {
                "setting": "A forgotten jungle filled with ancient ruins and hidden dangers.",
                "timePeriod": "Modern day",
                "technologyLevel": "Advanced technology for exploration, but the civilization is ancient.",
                "magicSystem": "The jungle has its own magic, with creatures and phenomena that defy explanation.",
            }
        ],
    )
    themes: List[str] = Field(
        description="The themes explored in the story.",
        default_factory=list,
        examples=[
            ["Exploration", "Adventure", "Discovery", "Mystery", "Transformation"],
        ],
    )
    n_scenes: int = Field(
        description="The total number of scenes in the story.",
        ge=1,
        default=50,
        examples=[50, 100, 200],
    )
