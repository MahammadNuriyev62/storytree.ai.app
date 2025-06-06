from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc

from db_models import Story, engine

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """🏠 Viral landing page with rotating captions / call-to-action."""
    captions = [
        "✨ Dive into interactive adventures!",
        "🎲 Choose. 🤔 Regret. 🔄 Replay.",
        "📖 Your story, your rules.",
        "🌍 Explore lost worlds.",
        "🦸 Become the hero of your own tale.",
        "🔥 Every choice matters.",
    ]
    highlights = [
        # "🔥 Trending: Lost Temple of Zandar",
        "💡 Tip: Revisit and reshape your story endings!",
        "🎉 Community: Share your favorite paths.",
    ]
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "captions": captions, "highlights": highlights},
    )


@router.get("/stories", response_class=HTMLResponse)
async def list_stories(request: Request):
    """Grid of all stories, newest first."""
    with Session(engine) as session:
        stories = session.exec(select(Story).order_by(desc(Story.id))).all()
    return templates.TemplateResponse(
        "stories.html",
        {"request": request, "stories": stories},
    )


@router.get("/stories/{story_id}", response_class=HTMLResponse)
async def story_details(request: Request, story_id: int):
    """Details page: title, blurb, resume-or-start buttons, metadata."""
    with Session(engine) as session:
        story: Optional[Story] = session.get(Story, story_id)
        if story is None:
            raise HTTPException(404, "Story not found")
    return templates.TemplateResponse(
        "story_details.html",
        {"request": request, "story": story},
    )


@router.get("/stories/{story_id}/play", response_class=HTMLResponse)
async def play_story(request: Request, story_id: int):
    """Main reader / choice UI."""
    with Session(engine) as session:
        story: Optional[Story] = session.get(Story, story_id)
        if story is None:
            raise HTTPException(404, "Story not found")
    return templates.TemplateResponse(
        "play.html",
        {"request": request, "story": story},
    )


@router.get("/create", response_class=HTMLResponse)
async def create_story_form(request: Request):
    """Story creation form."""
    return templates.TemplateResponse(
        "create.html",
        {"request": request},
    )
