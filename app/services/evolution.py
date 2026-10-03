from typing import Any

import httpx

from app.core.config import settings


class EvolutionAPIError(Exception):
    """Erro relacionado à Evolution API."""


class EvolutionAPI:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }

    async def create_instance(
        self,
        instance_name: str,
        webhook_url: str,
    ) -> dict[str, Any]:
        payload = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True,
            "webhook": {
                "url": webhook_url,
                "byEvents": False,
                "base64": False,
                "events": [
                    "MESSAGES_UPSERT",
                    "CONNECTION_UPDATE",
                ],
            },
        }

        url = f"{self.base_url}/instance/create"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                )

            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.is_error:
                detail = (
                    data.get("message")
                    or data.get("error")
                    or f"HTTP {response.status_code}"
                )

                raise EvolutionAPIError(
                    f"Evolution API recusou a criação da instância: {detail}"
                )

            return data

        except httpx.HTTPError as error:
            raise EvolutionAPIError(
                f"Não foi possível conectar à Evolution API: {error}"
            ) from error

    async def send_text(
        self,
        instance_name: str,
        number: str,
        text: str,
    ) -> dict[str, Any]:
        payload = {
            "number": number,
            "text": text,
        }

        url = (
            f"{self.base_url}/message/sendText/"
            f"{instance_name}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                )

            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.is_error:
                detail = (
                    data.get("message")
                    or data.get("error")
                    or f"HTTP {response.status_code}"
                )

                raise EvolutionAPIError(
                    f"Evolution API recusou o envio: {detail}"
                )

            return data

        except httpx.HTTPError as error:
            raise EvolutionAPIError(
                f"Não foi possível enviar mensagem pela Evolution API: {error}"
            ) from error

    async def get_instance(
        self,
        instance_name: str,
    ) -> dict[str, Any]:
        url = (
            f"{self.base_url}/instance/connectionState/"
            f"{instance_name}"
        )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    url,
                    headers=self._headers(),
                )

            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.is_error:
                detail = (
                    data.get("message")
                    or data.get("error")
                    or f"HTTP {response.status_code}"
                )

                raise EvolutionAPIError(
                    f"Não foi possível consultar a instância: {detail}"
                )

            return data

        except httpx.HTTPError as error:
            raise EvolutionAPIError(
                f"Não foi possível conectar à Evolution API: {error}"
            ) from error


evolution = EvolutionAPI()
