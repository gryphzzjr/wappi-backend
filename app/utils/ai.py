from app.services.gemini import (
    GeminiError,
    generate_response as generate_gemini_response,
)

from app.services.groq import (
    GroqError,
    generate_response as generate_groq_response,
)


class AIError(Exception):
    pass


async def generate_ai_response(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> str:

    normalized_model = model.strip().lower()

    if normalized_model == "groq":
        try:
            return await generate_groq_response(
                system_prompt=system_prompt,
                user_message=user_message,
                history=history,
            )

        except GroqError as error:
            raise AIError(str(error)) from error

    try:
        return await generate_gemini_response(
            system_prompt=system_prompt,
            user_message=user_message,
            history=history,
        )

    except GeminiError as gemini_error:
        try:
            return await generate_groq_response(
                system_prompt=system_prompt,
                user_message=user_message,
                history=history,
            )

        except GroqError as groq_error:
            raise AIError(
                "Gemini e Groq falharam. "
                f"Gemini: {gemini_error}. "
                f"Groq: {groq_error}"
            ) from groq_error
