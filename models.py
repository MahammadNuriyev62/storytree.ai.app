from typing import List, Tuple
from pydantic import BaseModel, Field


class CreateStory(BaseModel):
    choices_weights: List[Tuple[int, float]] = Field(
        description="A dictionary mapping choice IDs to their probabilities. "
        "The sum of all probabilities must be 1.0.",
        default=[(3, 0.1), (2, 0.2), (1, 0.7)],
        examples=[[(3, 0.1), (2, 0.4), (1, 0.5)]],
    )
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
    next_scene_id: int = Field(
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
