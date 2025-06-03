from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


class ChatBot:
    def __init__(self, model_name="gpt-4.1-mini") -> None:
        self.model_name = model_name

    async def prompt(self, messages):
        response = await client.responses.create(
            model=self.model_name,
            input=messages,
        )
        return response.output_text
