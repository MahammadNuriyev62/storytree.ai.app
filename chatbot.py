from ollama import AsyncClient
from ollama import ChatResponse

client = AsyncClient()


class ChatBot:
    def __init__(self, model_name="qwen3:1.7b"):
        self.model_name = model_name

    async def prompt(self, messages):
        response: ChatResponse = await client.chat(
            model=self.model_name,
            messages=messages,
        )
        return response["message"]["content"]
