from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_client
from app.services.supabase import supabase_admin


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


CONVERSATION_FIELDS = (
    "id, client_id, bot_id, connection_id, "
    "external_conversation_id, contact_name, contact_phone, "
    "status, last_message_at, created_at, updated_at"
)


MESSAGE_FIELDS = (
    "id, conversation_id, client_id, bot_id, connection_id, "
    "external_message_id, direction, type, content, topic, extension, "
    "event, private, payload, metadata, media_url, "
    "skip_broadcast, created_at, inserted_at, updated_at"
)


class CreateConversationRequest(BaseModel):
    bot_id: UUID
    connection_id: UUID | None = None
    external_conversation_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    contact_name: str | None = Field(
        default=None,
        max_length=255,
    )
    contact_phone: str | None = Field(
        default=None,
        max_length=50,
    )


class UpdateConversationRequest(BaseModel):
    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    contact_name: str | None = Field(
        default=None,
        max_length=255,
    )
    contact_phone: str | None = Field(
        default=None,
        max_length=50,
    )


def get_client_bot(
    bot_id: UUID,
    client_id: str,
) -> dict:
    response = (
        supabase_admin
        .table("bots")
        .select("id, client_id, name")
        .eq("id", str(bot_id))
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Bot não encontrado.",
        )

    return response.data[0]


def get_conversation(
    conversation_id: UUID,
    client_id: str,
) -> dict:
    response = (
        supabase_admin
        .table("conversations")
        .select(CONVERSATION_FIELDS)
        .eq("id", str(conversation_id))
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Conversa não encontrada.",
        )

    return response.data[0]


@router.get("")
async def list_conversations(
    bot_id: UUID | None = None,
    status: str | None = None,
    client: dict = Depends(get_current_client),
):
    try:
        query = (
            supabase_admin
            .table("conversations")
            .select(CONVERSATION_FIELDS)
            .eq("client_id", client["id"])
        )

        if bot_id:
            get_client_bot(
                bot_id,
                client["id"],
            )

            query = query.eq(
                "bot_id",
                str(bot_id),
            )

        if status:
            query = query.eq(
                "status",
                status,
            )

        response = (
            query
            .order(
                "last_message_at",
                desc=True,
                nullsfirst=False,
            )
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return {
            "conversations": response.data or [],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao listar conversas:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar as conversas.",
        )


@router.post("")
async def create_conversation(
    data: CreateConversationRequest,
    client: dict = Depends(get_current_client),
):
    try:
        get_client_bot(
            data.bot_id,
            client["id"],
        )

        existing_response = (
            supabase_admin
            .table("conversations")
            .select(CONVERSATION_FIELDS)
            .eq("client_id", client["id"])
            .eq("bot_id", str(data.bot_id))
            .eq(
                "external_conversation_id",
                data.external_conversation_id,
            )
            .limit(1)
            .execute()
        )

        if existing_response.data:
            return {
                "message": "Conversa já existe.",
                "conversation": existing_response.data[0],
            }

        conversation_response = (
            supabase_admin
            .table("conversations")
            .insert(
                {
                    "client_id": client["id"],
                    "bot_id": str(data.bot_id),
                    "connection_id": (
                        str(data.connection_id)
                        if data.connection_id
                        else None
                    ),
                    "external_conversation_id": (
                        data.external_conversation_id
                    ),
                    "contact_name": (
                        data.contact_name.strip()
                        if data.contact_name
                        else None
                    ),
                    "contact_phone": (
                        data.contact_phone.strip()
                        if data.contact_phone
                        else None
                    ),
                    "status": "open",
                }
            )
            .execute()
        )

        if not conversation_response.data:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível criar a conversa.",
            )

        return {
            "message": "Conversa criada com sucesso.",
            "conversation": conversation_response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao criar conversa:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível criar a conversa.",
        )


@router.get("/{conversation_id}")
async def get_conversation_by_id(
    conversation_id: UUID,
    client: dict = Depends(get_current_client),
):
    try:
        conversation = get_conversation(
            conversation_id,
            client["id"],
        )

        return {
            "conversation": conversation,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao buscar conversa:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar a conversa.",
        )


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    data: UpdateConversationRequest,
    client: dict = Depends(get_current_client),
):
    try:
        get_conversation(
            conversation_id,
            client["id"],
        )

        updates = data.model_dump(
            exclude_unset=True,
        )

        if not updates:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Nenhum campo foi enviado "
                    "para atualização."
                ),
            )

        if (
            "status" in updates
            and updates["status"] is not None
        ):
            allowed_statuses = {
                "open",
                "pending",
                "resolved",
                "closed",
            }

            if updates["status"] not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Status inválido. "
                        "Use: open, pending, "
                        "resolved ou closed."
                    ),
                )

        if (
            "contact_name" in updates
            and updates["contact_name"] is not None
        ):
            updates["contact_name"] = (
                updates["contact_name"].strip()
            )

        if (
            "contact_phone" in updates
            and updates["contact_phone"] is not None
        ):
            updates["contact_phone"] = (
                updates["contact_phone"].strip()
            )

        response = (
            supabase_admin
            .table("conversations")
            .update(updates)
            .eq("id", str(conversation_id))
            .eq("client_id", client["id"])
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Conversa não encontrada.",
            )

        return {
            "message": "Conversa atualizada com sucesso.",
            "conversation": response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao atualizar conversa:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível atualizar a conversa.",
        )


@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: UUID,
    client: dict = Depends(get_current_client),
):
    try:
        get_conversation(
            conversation_id,
            client["id"],
        )

        response = (
            supabase_admin
            .table("messages")
            .select(MESSAGE_FIELDS)
            .eq(
                "conversation_id",
                str(conversation_id),
            )
            .eq(
                "client_id",
                client["id"],
            )
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return {
            "messages": response.data or [],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao listar mensagens:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar as mensagens.",
        )
