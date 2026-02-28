from openai import AzureOpenAI
from app.interfaces.ai_provider import AIProvider
from app.core.settings import settings

class AzureAIProvider(AIProvider):
    def __init__(self):
        if not settings.azure_openai_api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY not configured")

        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )

        self.deployment = settings.azure_openai_deployment

    async def generate_response(self, message: str, context: dict) -> str:
        messages = [
            {
                "role": "system",
                "content": "Sos un asistente profesional de la empresa. Respondé de forma clara, breve y útil.",
            },
            {
                "role": "user",
                "content": message,
            },
        ]

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=0.7,
        )

        return response.choices[0].message.content