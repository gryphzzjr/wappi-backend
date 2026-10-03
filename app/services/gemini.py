import httpx

from app.core.config import settings


class GeminiError(Exception):
    pass


async def generate_response(
    *,
    bot: dict,
    message: str,
) -> str:
    api_key = settings.GEMINI_API_KEY

    if not api_key:
        raise GeminiError(
            "GEMINI_API_KEY não configurada."
        )

    model = (
        bot.get("model")
        or settings.GEMINI_MODEL
        or "gemini-3.1-flash-lite"
    )

    if model in {
        "gemini",
        "default",
        "google",
    }:
        model = (
            settings.GEMINI_MODEL
            or "gemini-3.1-flash-lite"
        )

    if model.startswith("models/"):
        model = model.removeprefix("models/")

    bot_name = bot.get("name") or "Wappi"

    description = (
        bot.get("description")
        or "Você é um assistente virtual de atendimento."
    )

    system_instruction = (
        f'Você é o assistente virtual do bot "{bot_name}".\n\n'
        f"Instruções do bot:\n"
        f"{description}\n\n"
        "Responda diretamente ao cliente pelo WhatsApp.\n"
        "Seja natural, educado e objetivo.\n"
        "Não diga que você é uma inteligência artificial, "
        "a menos que o cliente pergunte.\n"
        "Não invente informações que não estejam nas instruções."
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system_instruction,
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": message,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    print(
        f"Chamando Gemini com modelo: {model}"
    )

    try:
        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
    except httpx.HTTPError as error:
        raise GeminiError(
            f"Erro de conexão com o Gemini: {error}"
        ) from error

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.is_error:
        error_data = data.get("error", {})

        detail = (
            error_data.get("message")
            or f"HTTP {response.status_code}"
        )

        raise GeminiError(
            f"Gemini recusou a solicitação: {detail}"
        )

    candidates = data.get("candidates") or []

    if not candidates:
        raise GeminiError(
            "O Gemini não retornou nenhuma resposta."
        )

    candidate = candidates[0]
    content = candidate.get("content") or {}
    parts = content.get("parts") or []

    response_text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict)
    ).strip()

    if not response_text:
        raise GeminiError(
            "O Gemini retornou uma resposta vazia."
        )

    return response_text
