from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: Optional[str] = Field(default=None)
    db_name: str = Field(default="database.db")

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore
