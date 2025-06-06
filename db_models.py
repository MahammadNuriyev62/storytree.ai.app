from typing import Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.types import JSON


# --- Pydantic BaseModel for JSON data ---
class Character(BaseModel):
    name: str
    role: str
    traits: List[str]
    description: str


# --- SQLModel Table Definitions ---


class Story(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    emojis: List[str] = Field(sa_column=Column(JSON))
    user_given_description: str
    title: str
    themes: List[str] = Field(sa_column=Column(JSON))
    main_characters: List[Character] = Field(sa_column=Column(JSON))
    characters: List[Character] = Field(sa_column=Column(JSON))
    worldview: Dict[str, str] = Field(sa_column=Column(JSON))
    choices_weights: Dict[int, float] = Field(sa_column=Column(JSON))

    scenes: List["Scene"] = Relationship(
        back_populates="story",
    )
    n_scenes: int = Field(ge=1)
    difficulty: float = Field(default=0.2, ge=0, le=1)


class Scene(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: Optional[str] = Field(default=None, nullable=True)

    story_id: int = Field(foreign_key="story.id")
    story: Story = Relationship(back_populates="scenes")

    # This Scene is the *next_scene* for a Choice (its parent_choice)
    # The FK is Choice.next_scene_id
    parent_choice: Optional["Choice"] = Relationship(
        back_populates="next_scene",
        sa_relationship_kwargs={"foreign_keys": "[Choice.next_scene_id]"},
    )

    # This Scene is the *scene* for many Choices
    # The FK is Choice.scene_id
    choices: List["Choice"] = Relationship(
        back_populates="scene",
        sa_relationship_kwargs={
            "foreign_keys": "[Choice.scene_id]",
        },
    )


class Choice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    loading_text: str

    scene_id: int = Field(foreign_key="scene.id")
    # This Choice belongs to one Scene. Uses scene_id.
    scene: Scene = Relationship(
        back_populates="choices",
        sa_relationship_kwargs={"foreign_keys": "[Choice.scene_id]"},
    )

    next_scene_id: Optional[int] = Field(
        default=None,
        foreign_key="scene.id",
        nullable=True,
        index=True,  # <-- ensure we index this column!
    )
    # This Choice leads to one next_scene. Uses next_scene_id.
    next_scene: Optional[Scene] = Relationship(
        back_populates="parent_choice",
        sa_relationship_kwargs={"foreign_keys": "[Choice.next_scene_id]"},
    )
    is_wrong: bool = Field(default=False, nullable=False)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

SQLModel.metadata.create_all(engine)
