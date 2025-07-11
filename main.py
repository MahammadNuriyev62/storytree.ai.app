import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from initialize import init_db
from api import router as api_router
from ui import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


IS_PROD = os.getenv("MODE") == "production"  # pick your own flag / env var

app = FastAPI(
    lifespan=lifespan,
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# Only accept traffic addressed to **your** host names
if IS_PROD:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "storytree.up.railway.app",  # your canonical hostname
            "*.storytree.up.railway.app",  # optional wild-card sub-domains
            "127.0.0.1",
            "localhost",  # keep these for health checks, etc.
        ],
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(ui_router, tags=["ui"])
