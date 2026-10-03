from typing import Any

import httpx

from app.core.config import settings


class GroqError(Exception):
    pass


def get_api_keys() -> list[str]:
    keys = []

    if settings.GROQ_API_KEY:
        keys.append(settings.GROQ_API_KEY)

    if settings.GROQ_API_KEYS:
        keys.extend(
            key.strip()
            for key in settings.GROQ_API_KEYS.split(",")
            if key.strip()
        )

    return list(dict.fromkeys(keys))


async def generate_response(
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    keys = get_api_keys()

    if not keys:
        raise GroqError(
            "Nenhuma chave do Groq foi configurada."
        )

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    if history:
        for item in history:
            role = item.get("role")
            text = item.get("text")

            if not text:
                continue

            if role not in {"user", "assistant"}:
                continue

            messages.append(
                {
                    "role": role,
                    "content": text,
                }
            )

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    last_error: str | None = None

    for api_key in keys:
        payload: dict[str, Any] = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.is_error:
                last_error = (
                    data.get("error", {}).get("message")
                    or "Erro desconhecido no Groq."
                )
                continue

            choices = data.get("choices") or []

            if not choices:
                last_error = "O Groq não retornou nenhuma resposta."
                continue

            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
            )

            if content:
                return content.strip()

            last_error = "O Groq retornou uma resposta vazia."

        except httpx.HTTPError as error:
            last_error = str(error)

    raise GroqError(
        f"Falha ao gerar resposta com Groq: {last_error}"
    )
