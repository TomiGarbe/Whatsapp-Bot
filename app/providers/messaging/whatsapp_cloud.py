"""WhatsApp Cloud API messaging provider."""

from __future__ import annotations

import httpx

from app.core.settings import settings
from app.interfaces.messaging_provider import MessagingProvider


class WhatsAppCloudProvider(MessagingProvider):
    """Sends outbound messages through Meta WhatsApp Cloud API."""

    GRAPH_API_BASE_URL = "https://graph.facebook.com"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        phone_number_id: str | None = None,
        api_version: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.access_token = access_token or settings.whatsapp_cloud_access_token
        self.phone_number_id = phone_number_id or settings.whatsapp_cloud_phone_number_id
        self.api_version = api_version or settings.whatsapp_cloud_api_version
        self.timeout_seconds = timeout_seconds

        if not self.access_token:
            raise RuntimeError("WHATSAPP_CLOUD_ACCESS_TOKEN is not configured.")
        if not self.phone_number_id:
            raise RuntimeError(
                "Missing WhatsApp phone_number_id. Configure business.whatsapp_number or "
                "WHATSAPP_CLOUD_PHONE_NUMBER_ID."
            )

    async def send_message(self, user: str, message: str) -> None:
        url = f"{self.GRAPH_API_BASE_URL}/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": user,
            "type": "text",
            "text": {"body": message},
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
