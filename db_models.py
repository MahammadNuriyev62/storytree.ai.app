from typing import Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.types import JSON

from config import settings


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

    # Seed world state at the start of the story (stats / inventory /
    # relationships / flags), derived from the metadata at creation time.
    initial_state: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    # Per-story visual asset manifests. Each value is a dict whose leaves are
    # public `/static/...` URLs the SPA can drop into <img src>. Populated by
    # ml/images/lighthouse_assets.wire_uploads(); None for stories without
    # pre-generated art.
    character_sprites: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    backgrounds: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    scenes: List["Scene"] = Relationship(
        back_populates="story",
    )
    # Soft target length; the model decides the actual ending (with a hard cap).
    n_scenes: int = Field(ge=1)
    difficulty: float = Field(default=0.2, ge=0, le=1)


class Scene(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: Optional[str] = Field(default=None, nullable=True)

    # World state snapshot AS OF this scene (full state after its events),
    # the human-readable changes applied entering it, and the narrative phase.
    state: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    state_changes: Optional[list] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    pacing: Optional[str] = Field(default=None, nullable=True)

    # Visual composition for the SPA: which background + which character
    # sprite(s) and expression(s) to render for this scene. Shape:
    #   {"setting": "<background id>",
    #    "characters_present": [{"name": "Iwan", "expression": "scared"}, ...]}
    # Constrained at generation time to keys present in
    # Story.character_sprites / Story.backgrounds.
    stage: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

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
    is_pre_final: bool = Field(default=False)

    @property
    def is_terminal(self) -> bool:
        """Check if this choice leads to a terminal scene (no next scene)."""
        return self.next_scene_id is None


sqlite_file_name = settings.db_name
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

SQLModel.metadata.create_all(engine)
