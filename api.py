from typing import Any, List, Optional, Tuple, cast
from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from sqlmodel import Session, select, exists
from chatbots.chatbot import ChatBot
from generate import (
    continue_story_branch,
    generate_description,
    generate_story_metadata,
)
from db_models import Story, Scene, Choice, engine
from ml.images.sprite_extractor import extract_sprites_from_sheet
from models import CreateStory, SceneDto, StoriesDto, StoryDetailsDto

light_weight_chatbot = ChatBot()
heavy_weight_chatbot = ChatBot(model_name="o4-mini")

router = APIRouter()


@router.get("/stories/description")
async def generate_story_description():
    description = await generate_description(light_weight_chatbot)
    return {"description": description}


@router.post("/stories", response_model_by_alias=False)
async def create_story(data: CreateStory):
    story_metadata: Any = await generate_story_metadata(
        heavy_weight_chatbot,
        data.description,
    )
    with Session(engine) as session:
        story = Story(
            # root_scene=scene1 # Link the root scene
            title=story_metadata["title"],
            description=story_metadata["description"],
            characters=story_metadata["characters"],
            main_characters=[story_metadata["main_character"]],
            worldview=story_metadata["worldview"],
            themes=story_metadata["themes"],
            user_given_description=data.description,
            n_scenes=data.n_scenes,
            emojis=story_metadata["emojis"],
            difficulty=data.difficulty,
        )
        session.add(story)
        session.commit()

        story_id = cast(int, story.id)

        root_scene = Scene(
            text=story_metadata["first_introduction_scene"]["text"],
            story_id=story_id,
        )

        child_scene = Scene(
            story_id=story_id,
        )

        session.add(root_scene)
        session.add(child_scene)
        session.commit()

        child_scene_id = cast(int, child_scene.id)
        root_scene_id = cast(int, root_scene.id)

        root_choice = Choice(
            loading_text=story_metadata["first_introduction_scene"]["choice"][
                "loading_text"
            ],
            text=story_metadata["first_introduction_scene"]["choice"]["text"],
            next_scene_id=child_scene_id,
            scene_id=root_scene_id,
        )

        session.add(root_choice)
        session.commit()

    with Session(engine) as session:
        story = session.get(Story, story_id)
        if not story:
            raise ValueError("Story not found after creation")
        return story


@router.get(
    "/stories/{story_id}/scene", response_model_by_alias=False, response_model=SceneDto
)
async def get_story(story_id: int, choice_id: Optional[int] = None):
    """
    If choice_id is provided, return that Choice's next_scene.
    Otherwise, return the Scene in this story that has no Choice.next_scene_id → it.
    """
    with Session(engine) as session:
        if choice_id is None:
            stmt = (
                select(Scene)
                .where(Scene.story_id == story_id)
                .where(
                    ~exists(select(Choice.id).where(Choice.next_scene_id == Scene.id))
                )
            )
            result = session.exec(stmt)
            scene = result.one_or_none()
            if scene is None:
                raise ValueError(f"No “root” scene found for story_id={story_id!r}")
            _ = scene.choices
            return scene

        choice = session.get(Choice, choice_id)
        if choice is None:
            raise ValueError(f"No Choice with id={choice_id!r}")

        if choice.next_scene is None:
            raise ValueError(f"No Scene for Choice with id={choice_id!r}")

        print(choice.model_dump())
        if choice.next_scene.text is not None:
            _ = choice.next_scene.choices
            return choice.next_scene

        scene = choice.next_scene

        branch: List[Tuple[Scene, Choice]] = []
        current = scene
        while current.parent_choice is not None:
            parent_choice = current.parent_choice
            parent_scene = parent_choice.scene
            # accumulate (parent_scene, the choice that led to `current`)
            branch.append((parent_scene, parent_choice))
            current = parent_scene
        branch.reverse()

        scenes = [s for s, _ in branch]
        choices_made = [c for _, c in branch]

        story = scene.story

        new_scene_json, is_branch_over = await continue_story_branch(
            light_weight_chatbot,
            story=story,
            scenes=scenes,
            choices=choices_made,
        )

        scene.text = new_scene_json["text"]
        session.add(scene)
        session.commit()
        scene_id = cast(int, scene.id)

        next_scene_ids: List[Optional[int]] = []
        # Check if we are at the second to last scene
        if is_branch_over:
            next_scene_ids = [None] * len(new_scene_json["choices"])
        else:
            child_scenes = [Scene(story_id=story_id) for _ in new_scene_json["choices"]]
            session.add_all(child_scenes)
            session.commit()
            next_scene_ids = [cast(int, cs.id) for cs in child_scenes]

        new_choices = []
        for next_scene_id, choice_json in zip(
            next_scene_ids, new_scene_json["choices"]
        ):
            new_choice = Choice(
                text=choice_json["text"],
                loading_text=choice_json.get("loading_text", "Thinking... 🤔"),
                scene_id=scene_id,
                next_scene_id=next_scene_id,
                is_wrong=choice_json.get("is_wrong", False),
                is_pre_final=choice_json.get("is_final", False),
            )
            new_choices.append(new_choice)
        session.add_all(new_choices)
        session.commit()

        session.refresh(scene)

        _ = scene.choices
        return scene


@router.get("/stories", response_model=StoriesDto)
async def get_stories():
    """Get all stories."""
    with Session(engine) as session:
        stmt = select(Story)
        stories = session.exec(stmt).all()
        return {"stories": stories}


@router.get("/stories/{story_id}", response_model=StoryDetailsDto)
async def get_story_by_id(story_id: int):
    """Get a story by its ID."""
    with Session(engine) as session:
        story = session.get(Story, story_id)
        if not story:
            raise ValueError(f"Story with id={story_id!r} not found")
        return story


@router.post("/extract-sprites")
async def extract_sprites(file: UploadFile = File(...)):
    """Extract sprites from uploaded image and return as zip."""
    try:
        # Read uploaded file
        contents = await file.read()

        # Extract sprites
        zip_data = extract_sprites_from_sheet(contents)

        # Generate safe filename
        base_filename = (
            file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
        )
        # Remove any special characters that might cause issues
        safe_filename = "".join(
            c for c in base_filename if c.isalnum() or c in ("-", "_")
        )[:50]
        if not safe_filename:
            safe_filename = "sprites"

        # Return zip file
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="sprites_{safe_filename}.zip"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
