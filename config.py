from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)
    db_name: str = Field(default="database.db")

    class Config:
        env_file = ".env"
        extra = "ignore"  # tolerate unknown env vars (e.g. local-only secrets)


settings = Settings()  # type: ignore
