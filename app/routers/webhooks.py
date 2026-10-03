from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.services.evolution import EvolutionAPIError, evolution
from app.services.gemini import GeminiError, generate_response
from app.services.supabase import supabase_admin


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


def extract_message(
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    event = payload.get("event", "")

    if not isinstance(event, str):
        return None

    event = event.upper().replace(".", "_")

    if event != "MESSAGES_UPSERT":
        return None

    data = payload.get("data")

    if isinstance(data, list):
        if not data:
            return None

        message = data[0]

    elif isinstance(data, dict):
        message = data

    else:
        return None

    key = message.get("key") or {}

    if key.get("fromMe") is True:
        return None

    remote_jid = key.get("remoteJid")

    if not remote_jid:
        return None

    message_content = message.get("message") or {}

    text = ""

    conversation = message_content.get("conversation")

    if isinstance(conversation, str):
        text = conversation

    extended_text = message_content.get(
        "extendedTextMessage"
    )

    if isinstance(extended_text, dict):
        text = extended_text.get("text") or ""

    image_message = message_content.get(
        "imageMessage"
    )

    if isinstance(image_message, dict):
        text = image_message.get("caption") or ""

    video_message = message_content.get(
        "videoMessage"
    )

    if isinstance(video_message, dict):
        text = video_message.get("caption") or ""

    text = text.strip()

    if not text:
        return None

    return {
    "text": text,
    "remote_jid": remote_jid,
    "message": message,
    "message_id": key.get("id"),
    "contact_name": (
        key.get("pushName")
        or message.get("pushName")
    ),
}


async def find_bot_by_instance(
    instance_name: str,
) -> dict[str, Any] | None:
    response = (
        supabase_admin
        .table("bots")
        .select(
            "id, client_id, name, description, status, "
            "system_prompt, model, conversations_count, "
            "instance_name, created_at, updated_at"
        )
        .eq(
            "instance_name",
            instance_name,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


async def find_connection_by_bot(
    bot_id: str,
) -> dict[str, Any] | None:
    response = (
        supabase_admin
        .table("whatsapp_connections")
        .select("*")
        .eq(
            "bot_id",
            bot_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


async def find_or_create_conversation(
    bot: dict,
    connection: dict | None,
    remote_jid: str,
    contact_name: str | None = None,
) -> dict:
    client_id = bot["client_id"]
    bot_id = bot["id"]

    response = (
        supabase_admin
        .table("conversations")
        .select(
            "id, client_id, bot_id, connection_id, "
            "external_conversation_id, contact_name, "
            "contact_phone, status, last_message_at, "
            "created_at, updated_at"
        )
        .eq(
            "client_id",
            client_id,
        )
        .eq(
            "bot_id",
            bot_id,
        )
        .eq(
            "external_conversation_id",
            remote_jid,
        )
        .limit(1)
        .execute()
    )

    if response.data:
        conversation = response.data[0]

        updates = {}

        if connection:
            if conversation.get("connection_id") != connection["id"]:
                updates["connection_id"] = connection["id"]

        if contact_name and not conversation.get("contact_name"):
            updates["contact_name"] = contact_name

        if updates:
            updated_response = (
                supabase_admin
                .table("conversations")
                .update(updates)
                .eq(
                    "id",
                    conversation["id"],
                )
                .execute()
            )

            if updated_response.data:
                conversation = updated_response.data[0]

        return conversation

    phone = remote_jid.split("@")[0]

    conversation_response = (
        supabase_admin
        .table("conversations")
        .insert(
            {
                "client_id": client_id,
                "bot_id": bot_id,
                "connection_id": (
                    connection["id"]
                    if connection
                    else None
                ),
                "external_conversation_id": remote_jid,
                "contact_name": contact_name,
                "contact_phone": phone,
                "status": "open",
            }
        )
        .execute()
    )

    if not conversation_response.data:
        raise RuntimeError(
            "Não foi possível criar a conversa."
        )

    return conversation_response.data[0]


async def save_message(
    *,
    bot: dict,
    connection: dict | None,
    conversation: dict,
    message: dict,
    content: str | None,
    direction: str,
    event: str,
    external_message_id: str | None,
) -> dict:
    message_data = {
        "conversation_id": conversation["id"],
        "client_id": bot["client_id"],
        "bot_id": bot["id"],
        "connection_id": (
            connection["id"]
            if connection
            else None
        ),
        "external_message_id": external_message_id,
        "direction": direction,
        "type": "text",
        "content": content,
        "topic": "whatsapp",
        "extension": "evolution",
        "event": event,
        "private": False,
        "payload": message,
        "metadata": {},
        "skip_broadcast": False,
    }

    response = (
        supabase_admin
        .table("messages")
        .insert(message_data)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Não foi possível salvar a mensagem."
        )

    return response.data[0]

@router.post("/evolution")
async def evolution_webhook(
    request: Request,
):
    try:
        payload = await request.json()

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Payload inválido.",
        )

    print()
    print("========== EVOLUTION WEBHOOK ==========")

    event_raw = payload.get("event")

    instance_name = (
        payload.get("instance")
        or payload.get("instanceName")
    )

    print(f"Evento: {event_raw}")
    print(f"Instância: {instance_name}")

    print("=======================================")

    # =========================================================
    # INSTÂNCIA
    # =========================================================

    if not instance_name:
        return {
            "status": "ignored",
            "reason": "Instância não identificada.",
        }

    print(
        f"Instância recebida: {instance_name}"
    )

    # =========================================================
    # NORMALIZA EVENTO
    # =========================================================

    event = event_raw or ""

    if isinstance(event, str):
        event = event.upper().replace(".", "_")

    print(
        f"Evento recebido: {event}"
    )

    # =========================================================
    # CONNECTION.UPDATE
    # =========================================================

    if event == "CONNECTION_UPDATE":
        data = payload.get("data") or {}

        connection_state = data.get("state")

        print(
            f"Estado da conexão: {connection_state}"
        )

        bot = await find_bot_by_instance(
            instance_name
        )

        if not bot:
            print(
                "Bot não encontrado para instância: "
                f"{instance_name}"
            )

            return {
                "status": "ignored",
                "reason": "Bot não encontrado.",
                "instance": instance_name,
            }

        print(
            f"Bot encontrado: {bot['id']}"
        )

        if connection_state == "open":
            bot_status = "online"
            connection_status = "connected"

        else:
            bot_status = "offline"
            connection_status = "disconnected"

        bot_update = (
            supabase_admin
            .table("bots")
            .update({
                "status": bot_status,
            })
            .eq(
                "id",
                bot["id"],
            )
            .execute()
        )

        print(
            f"Status do bot atualizado para: "
            f"{bot_status}"
        )

        connection = await find_connection_by_bot(
            bot["id"]
        )

        if connection:
            (
                supabase_admin
                .table("whatsapp_connections")
                .update({
                    "status": connection_status,
                    "phone_number": (
                        data.get("wuid", "").split("@")[0]
                        if data.get("wuid")
                        else None
                    ),
                })
                .eq(
                    "id",
                    connection["id"],
                )
                .execute()
            )

            print(
                f"Status da conexão atualizado para: "
                f"{connection_status}"
            )

        return {
            "status": "ok",
            "event": event,
            "instance": instance_name,
            "connection_state": connection_state,
            "bot_status": bot_status,
        }

    # =========================================================
    # IGNORA OUTROS EVENTOS
    # =========================================================

    if event != "MESSAGES_UPSERT":
        return {
            "status": "ok",
            "event": event,
            "instance": instance_name,
        }

    # =========================================================
    # EXTRAI MENSAGEM
    # =========================================================

    message_data = extract_message(payload)

    if not message_data:
        return {
            "status": "ignored",
            "reason": "Mensagem sem texto processável.",
        }

    text = message_data["text"]
    remote_jid = message_data["remote_jid"]

    print(
        f"Mensagem recebida: {text}"
    )

    print(
        f"Remetente: {remote_jid}"
    )

    # =========================================================
    # BUSCA BOT
    # =========================================================

    try:
        bot = await find_bot_by_instance(
            instance_name
        )

    except Exception as error:
        print(
            "Erro ao buscar bot:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível localizar o bot.",
        )

    if not bot:
        print(
            "Bot não encontrado para instância: "
            f"{instance_name}"
        )

        return {
            "status": "ignored",
            "reason": "Bot não encontrado.",
            "instance": instance_name,
        }

    print(
        f"Bot encontrado: {bot['id']}"
    )

    print(
        f"Nome do bot: {bot['name']}"
    )

    print(
        f"Cliente: {bot['client_id']}"
    )

    # =========================================================
    # BUSCA CONEXÃO
    # =========================================================

    connection = await find_connection_by_bot(
        bot["id"]
    )

    if not connection:
        print(
            "Conexão não encontrada para instância: "
            f"{instance_name}"
        )

        return {
            "status": "ignored",
            "reason": "Conexão não encontrada.",
            "instance": instance_name,
        }

    print(
        f"Conexão encontrada: {connection['id']}"
    )

    # =========================================================
    # STATUS DO BOT
    # =========================================================

    bot_status = bot.get("status")

    if bot_status not in {
        "online",
        "active",
        "connected",
    }:
        print(
            "Bot ainda não está online. "
            f"Status atual: {bot_status}"
        )

        return {
            "status": "ignored",
            "reason": "Bot offline.",
        }

    print(
        "Bot está online."
    )

    # =========================================================
    # IA
    # =========================================================

    print(
        "Enviando mensagem para IA..."
    )

    try:
        ai_response = await generate_response(
            bot=bot,
            message=text,
        )

    except GeminiError as error:
        print(
            "Erro no Gemini:",
            error,
        )

        return {
            "status": "error",
            "reason": "Erro ao gerar resposta da IA.",
        }

    except Exception as error:
        print(
            "Erro inesperado na IA:",
            error,
        )

        return {
            "status": "error",
            "reason": "Erro interno da IA.",
        }

    if not ai_response:
        print(
            "A IA não retornou uma resposta."
        )

        return {
            "status": "error",
            "reason": "A IA não retornou resposta.",
        }

    print(
        f"Resposta da IA: {ai_response}"
    )

    # =========================================================
    # ENVIA RESPOSTA PELO WHATSAPP
    # =========================================================

    number = remote_jid.split("@")[0]

    try:
        evolution_response = await evolution.send_text(
            instance_name=instance_name,
            number=number,
            text=ai_response,
        )

    except EvolutionAPIError as error:
        print(
            "Erro ao enviar resposta:",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Não foi possível enviar "
                "a resposta pelo WhatsApp."
            ),
        )

    except Exception as error:
        print(
            "Erro inesperado ao enviar resposta:",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Erro interno ao enviar "
                "a resposta pelo WhatsApp."
            ),
        )

    print(
        "Resposta enviada com sucesso."
    )

    # =========================================================
    # ATUALIZA CONTADOR
    # =========================================================

    try:
        current_count = (
            bot.get("conversations_count")
            or 0
        )

        (
            supabase_admin
            .table("bots")
            .update(
                {
                    "conversations_count": (
                        current_count + 1
                    )
                }
            )
            .eq(
                "id",
                bot["id"],
            )
            .execute()
        )

    except Exception as error:
        print(
            "Erro ao atualizar contador:",
            error,
        )

    # =========================================================
    # RESPOSTA FINAL
    # =========================================================

    return {
        "status": "ok",
        "instance": instance_name,
        "bot_id": bot["id"],
        "number": number,
        "response": ai_response,
        "evolution": evolution_response,
    }
