from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Annotated, Dict, List, cast
from config import settings
from chatbot import ChatBot
from generate import generate_description, generate_story_metadata

PyObjectId = Annotated[str, BeforeValidator(str)]


class Model(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


# Pydantic models
class StoryMetadata(BaseModel):
    choices_probabilities: Dict[str, str] = Field(
        description="A dictionary mapping choice IDs to their probabilities. "
        "The sum of all probabilities must be 1.0.",
        default={"3": "0.1", "2": "0.2"},
    )
    description: str = Field(
        description="A brief description of the story. "
        "This will be used to generate the story metadata.",
        min_length=10,
        default="In the heart of a forgotten jungle, a rogue archaeologist discovers a hidden temple filled with ancient scrolls that reveal a lost kingdom and a powerful artifact. Alongside a cunning thief and a haunted historian, they must outwit a ruthless cult and uncover the truth behind the kingdom'''s disappearance.",
    )
    n_scenes: int = Field(
        default=5,
        ge=1,
        description="Length of the story in scenes. Must be at least 1.",
    )


class Character(BaseModel):
    name: str
    role: str
    traits: List[str]
    description: str


class Story(Model):
    id: PyObjectId = cast(PyObjectId, Field(alias="_id", default=None))
    title: str
    description: str
    metadata: StoryMetadata
    main_characters: List[Character]
    characters: List[Character]
    worldview: Dict[str, str]
    themes: List[str]


class ChoiceCreate(BaseModel):
    text: str
    scene_id: str
    next_scene_id: str


class SceneCreate(BaseModel):
    story_id: str
    description: str
    choices: List[ChoiceCreate]


class Scene(BaseModel):
    id: str
    story_id: str
    description: str


# MongoDB connection
client = AsyncIOMotorClient(settings.mongodb_url)
db = client["story_db"]

# FastAPI app
app = FastAPI()

light_weight_chatbot = ChatBot(model_name="qwen3:1.7b")
height_weight_chatbot = ChatBot(model_name="qwen3:8b")


# Endpoints
@app.get("/stories/description")
async def generate_story_description():
    description = await generate_description(light_weight_chatbot)
    return {"description": description}


@app.post("/stories", response_model=Story, response_model_by_alias=False)
async def create_story(data: StoryMetadata):
    story_metadata = await generate_story_metadata(
        light_weight_chatbot,
        data.description,
    )

    story = Story(
        metadata=data,
        title=story_metadata["title"],
        description=story_metadata["description"],
        characters=story_metadata["characters"],
        main_characters=[story_metadata["main_character"]],
        worldview=story_metadata["worldview"],
        themes=story_metadata["themes"],
    )
    result = await db["stories"].insert_one(
        story.model_dump(by_alias=True, exclude={"id"})
    )
    story.id = str(result.inserted_id)
    return story


@app.get("/stories/{story_id}", response_model=Story)
async def get_story(story_id: str):
    story = await db["stories"].find_one({"_id": ObjectId(story_id)})
    if story:
        return Story(id=str(story["_id"]), title=story["title"])
    raise HTTPException(status_code=404, detail="Story not found")


@app.post("/scenes", response_model=Scene)
async def create_scene(scene: SceneCreate):
    scene_dict = {
        "story_id": ObjectId(scene.story_id),
        "description": scene.description,
        "choices": [
            {"text": c.text, "next_scene_id": ObjectId(c.next_scene_id)}
            for c in scene.choices
        ],
    }
    result = await db["scenes"].insert_one(scene_dict)
    return Scene(
        id=str(result.inserted_id),
        story_id=scene.story_id,
        description=scene.description,
        choices=scene.choices,
    )


@app.get("/scenes/{scene_id}", response_model=Scene)
async def get_scene(scene_id: str):
    scene = await db["scenes"].find_one({"_id": ObjectId(scene_id)})
    if scene:
        choices = [
            ChoiceCreate(text=c["text"], next_scene_id=str(c["next_scene_id"]))
            for c in scene["choices"]
        ]
        return Scene(
            id=str(scene["_id"]),
            story_id=str(scene["story_id"]),
            description=scene["description"],
            choices=choices,
        )
    raise HTTPException(status_code=404, detail="Scene not found")
