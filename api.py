import traceback
from typing import Any, List, Optional, Tuple, cast
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Response, UploadFile
from sqlmodel import Session, select, exists
from chatbots.chatbot import ChatBot
from generate import (
    EMPTY_STATE,
    continue_story_branch,
    generate_description,
    generate_story_metadata,
)
from db_models import Story, Scene, Choice, engine
from models import CreateStory, SceneDto, StoriesDto, StoryDetailsDto

# Both story-creation AND per-scene narrative now go through Sonnet 4.6.
# We used to keep scenes on Haiku 4.5 for snappiness; the trade-off no longer
# made sense once stories with literary register (L'Étranger, The Lighthouse
# in Winter) landed — Sonnet's prose density, character voice, and
# world-state continuity are noticeably better per scene. ~2-3× slower per
# click (15-30s vs 5-15s), but the user is reading slowly anyway.
light_weight_chatbot = ChatBot(model_name="o4-mini")
heavy_weight_chatbot = ChatBot(model_name="o4-mini")

router = APIRouter()


def _normalize_roster(raw) -> list[dict]:
    """Coerce a `characters_present` list into the canonical [{name, expression}].

    The metadata generator occasionally emits bare strings — observed for
    story 7's root scene, where `["Elena Ferri"]` made the frontend look up
    `(undefined).name` and silently drop the sprite. Bare strings become
    `{name, expression: "neutral"}`; anything else non-dict is discarded.
    """
    out: list[dict] = []
    for entry in raw or []:
        if isinstance(entry, str):
            out.append({"name": entry, "expression": "neutral"})
        elif isinstance(entry, dict) and entry.get("name"):
            out.append(entry)
    return out


def _sanitize_stage(stage: Optional[dict], story: Story) -> Optional[dict]:
    """Drop any stage values that don't match the story's asset manifest.

    The model is told the available settings + characters, but we still validate
    server-side so a hallucinated key doesn't reach the SPA as a broken image.
    """
    if not stage or not isinstance(stage, dict):
        return None
    settings_map = story.backgrounds or {}
    sprites_map = story.character_sprites or {}
    setting = stage.get("setting")
    if setting and setting not in settings_map:
        setting = None

    valid_expressions = {"angry", "sad", "smiling", "neutral", "scared"}
    cleaned_chars = []
    for entry in _normalize_roster(stage.get("characters_present")):
        name = entry.get("name")
        expr = entry.get("expression") or "neutral"
        if name in sprites_map and expr in valid_expressions:
            cleaned_chars.append({"name": name, "expression": expr})

    if not setting and not cleaned_chars:
        return None
    return {"setting": setting, "characters_present": cleaned_chars}


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
    initial_state = story_metadata.get("initial_state") or dict(EMPTY_STATE)
    art_style = story_metadata.get("art_style")
    settings_list = story_metadata.get("settings") or []
    # If the LLM produced art prompts, mark the story as `pending` so the SPA
    # can offer a "Generate art" button. Older metadata without art_prompts
    # stays at the default "none".
    has_any_art_prompt = bool(art_style) and (
        any(c.get("art_prompt") for c in story_metadata.get("characters") or [])
        or any(s.get("art_prompt") for s in settings_list)
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
            initial_state=initial_state,
            art_style=art_style,
            settings=settings_list or None,
            art_status="pending" if has_any_art_prompt else "none",
        )
        session.add(story)
        session.commit()

        story_id = cast(int, story.id)

        # Seed the opening scene's stage so the first page already has a
        # background image when art has been generated. Prefer the explicit
        # `stage` from the metadata generator; normalise the shape (the
        # generator occasionally emits bare strings for characters_present;
        # see _normalize_roster) but skip the manifest-validation step in
        # _sanitize_stage — the manifest doesn't exist yet at create-time.
        first_scene_data = story_metadata["first_introduction_scene"]
        explicit_stage = first_scene_data.get("stage")
        if isinstance(explicit_stage, dict):
            explicit_stage = {
                "setting": explicit_stage.get("setting"),
                "characters_present": _normalize_roster(
                    explicit_stage.get("characters_present")
                ),
            }
        fallback_setting = (settings_list[0].get("id") if settings_list else None)
        root_stage = explicit_stage or (
            {"setting": fallback_setting, "characters_present": []}
            if fallback_setting else None
        )

        root_scene = Scene(
            text=first_scene_data["text"],
            story_id=story_id,
            state=initial_state,
            state_changes=[],
            pacing="setup",
            stage=root_stage,
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
async def get_story(
    story_id: int,
    choice_id: Optional[int] = None,
    scene_id: Optional[int] = None,
):
    """
    - scene_id  : direct lookup of an already-generated scene (for deep links).
                  Must belong to this story and have non-null text.
    - choice_id : return (or lazily generate) the Choice's next_scene.
    - neither   : return the story's root scene (no incoming Choice.next_scene_id).
    """
    with Session(engine) as session:
        if scene_id is not None:
            scene = session.get(Scene, scene_id)
            if (
                scene is None
                or scene.story_id != story_id
                or scene.text is None
            ):
                raise HTTPException(
                    status_code=404,
                    detail=f"no generated scene with id={scene_id} in story {story_id}",
                )
            _ = scene.choices
            return scene

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
        scene.state = new_scene_json.get("state")
        scene.state_changes = new_scene_json.get("state_changes", [])
        scene.pacing = new_scene_json.get("pacing")
        scene.stage = _sanitize_stage(new_scene_json.get("stage"), story)
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


@router.get("/stories/{story_id}/tree")
async def get_story_tree(story_id: int):
    """Return the full Scene + Choice tree for the story as nodes + edges.

    Nodes are scenes (including unmaterialised placeholders — `is_generated`
    distinguishes them). Edges are choices: every choice yields one edge
    EXCEPT terminal "The End" choices (next_scene_id is NULL) — those are
    surfaced as `has_terminal_choice: true` on the source node instead, so
    the graph stays a strict scene→scene tree.

    Used by the SPA's `/story/{id}/tree` map view.
    """
    with Session(engine) as session:
        story = session.get(Story, story_id)
        if not story:
            raise HTTPException(status_code=404, detail=f"no story {story_id}")
        scenes: List[Scene] = list(
            session.exec(select(Scene).where(Scene.story_id == story_id)).all()
        )
        scene_ids = [cast(int, s.id) for s in scenes]
        choices: List[Choice] = (
            list(
                session.exec(
                    select(Choice).where(Choice.scene_id.in_(scene_ids))
                ).all()
            )
            if scene_ids
            else []
        )

        terminal_sources = {c.scene_id for c in choices if c.next_scene_id is None}
        nodes = [
            {
                "id": s.id,
                "pacing": s.pacing,
                "is_generated": s.text is not None,
                "has_terminal_choice": s.id in terminal_sources,
                "text_preview": ((s.text or "").split("{{break}}")[0][:120].strip()),
            }
            for s in scenes
        ]
        edges = [
            {
                "choice_id": c.id,
                "from": c.scene_id,
                "to": c.next_scene_id,
                "text": c.text,
                "is_wrong": bool(c.is_wrong),
                "is_pre_final": bool(c.is_pre_final),
            }
            for c in choices
            if c.next_scene_id is not None
        ]
        # Root = the scene with no incoming choice.
        incoming = {c.next_scene_id for c in choices if c.next_scene_id is not None}
        roots = [sid for sid in scene_ids if sid not in incoming]
        root = roots[0] if roots else None
        return {
            "story_id": story_id,
            "title": story.title,
            "root_scene_id": root,
            "nodes": nodes,
            "edges": edges,
        }


def _run_asset_generation(story_id: int) -> None:
    """Background-task body — calls auto_gen and writes back the manifest.

    Runs inside the BackgroundTask scheduler (no request context). All DB
    work uses a fresh Session. Any exception is caught + logged + reflected
    in `Story.art_status='failed'` so the SPA can surface a retry.
    """
    from ml.images.auto_gen import generate_story_assets

    try:
        with Session(engine) as session:
            story = session.get(Story, story_id)
            if story is None:
                print(f"[generate_assets] story {story_id} vanished, abort")
                return
            manifest = generate_story_assets(story)
            story.character_sprites = manifest["character_sprites"]
            story.backgrounds = manifest["backgrounds"]
            story.art_status = "ready"
            session.add(story)
            session.commit()
            print(f"[generate_assets] story {story_id} → ready")
    except Exception as e:
        print(f"[generate_assets] story {story_id} FAILED: {e}")
        traceback.print_exc()
        with Session(engine) as session:
            story = session.get(Story, story_id)
            if story is not None:
                story.art_status = "failed"
                session.add(story)
                session.commit()


@router.post("/stories/{story_id}/generate_assets")
async def trigger_asset_generation(story_id: int, background_tasks: BackgroundTasks):
    """Kick off art generation for a story. Returns immediately.

    Polls happen via `GET /stories/{id}` → `art_status`. Possible states:
    `pending` (waiting), `generating` (in progress), `ready` (done), `failed`.
    """
    with Session(engine) as session:
        story = session.get(Story, story_id)
        if story is None:
            raise HTTPException(status_code=404, detail=f"no story {story_id}")
        if story.art_status == "generating":
            return {"status": "already generating", "art_status": story.art_status}
        if not story.art_style or not (story.settings or story.characters):
            raise HTTPException(
                status_code=400,
                detail=(
                    "story has no art prompts on record — re-create it so the "
                    "metadata generator emits art_prompt/art_style/settings"
                ),
            )
        story.art_status = "generating"
        session.add(story)
        session.commit()
    background_tasks.add_task(_run_asset_generation, story_id)
    return {"status": "queued", "art_status": "generating"}


@router.post("/extract-sprites")
async def extract_sprites(file: UploadFile = File(...)):
    """Extract sprites from uploaded image and return as zip."""
    try:
        # Imported lazily so the app can boot without OpenCV installed.
        from ml.images.sprite_extractor import extract_sprites_from_sheet

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
