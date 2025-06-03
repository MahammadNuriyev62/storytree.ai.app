from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = Field()

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore
