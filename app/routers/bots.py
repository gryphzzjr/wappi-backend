from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_current_client
from app.services.evolution import EvolutionAPIError, evolution
from app.services.supabase import supabase_admin


router = APIRouter(
    prefix="/bots",
    tags=["Bots"],
)


BOT_SELECT = (
    "id, name, description, status, "
    "system_prompt, model, conversations_count, "
    "instance_name, created_at, updated_at"
)


class CreateBotRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    description: str = Field(
        default="",
        max_length=500,
    )

    model: str = Field(
        default="gemini-3.1-flash-lite",
        max_length=100,
    )


class UpdateBotRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    model: str | None = Field(
        default=None,
        max_length=100,
    )

    system_prompt: str | None = None


def generate_instance_name() -> str:
    return f"wappi-{uuid4().hex[:12]}"


def get_webhook_url() -> str:
    return (
        settings.WEBHOOK_URL.rstrip("/")
        + "/webhooks/evolution"
    )


async def find_bot(
    bot_id: UUID,
    client_id: str,
) -> dict:
    response = (
        supabase_admin
        .table("bots")
        .select(BOT_SELECT)
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


@router.get("")
async def list_bots(
    client: dict = Depends(get_current_client),
):
    try:
        response = (
            supabase_admin
            .table("bots")
            .select(BOT_SELECT)
            .eq("client_id", client["id"])
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return {
            "bots": response.data or [],
        }

    except Exception as error:
        print(
            "Erro ao listar bots:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar os bots.",
        )


@router.post("")
async def create_bot(
    data: CreateBotRequest,
    client: dict = Depends(get_current_client),
):
    instance_name = generate_instance_name()

    bot_id = None
    connection_created = False
    evolution_created = False

    name = data.name.strip()
    description = data.description.strip()
    model = data.model.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="O nome do bot não pode estar vazio.",
        )

    if not model:
        model = "gemini-3.1-flash-lite"

    try:
        print(
            f"Criando bot: {name}"
        )

        print(
            f"Instância: {instance_name}"
        )

        bot_response = (
            supabase_admin
            .table("bots")
            .insert(
                {
                    "client_id": client["id"],
                    "name": name,
                    "description": description,
                    "model": model,
                    "status": "offline",
                    "conversations_count": 0,
                    "instance_name": instance_name,
                }
            )
            .execute()
        )

        if not bot_response.data:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível criar o bot.",
            )

        bot = bot_response.data[0]
        bot_id = bot["id"]

        print(
            f"Bot criado no Supabase: {bot_id}"
        )

        webhook_url = get_webhook_url()

        print(
            f"Webhook: {webhook_url}"
        )

        try:
            evolution_response = (
                await evolution.create_instance(
                    instance_name=instance_name,
                    webhook_url=webhook_url,
                )
            )

            evolution_created = True

        except EvolutionAPIError as error:
            print(
                "Erro ao criar instância no Evolution:",
                error,
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "Não foi possível criar "
                    "a instância no Evolution API."
                ),
            )

        print(
            "Instância criada no Evolution:"
        )

        print(
            evolution_response
        )

        try:
            connection_response = (
                supabase_admin
                .table("whatsapp_connections")
                .insert(
                    {
                        "client_id": client["id"],
                        "bot_id": bot_id,
                        "name": instance_name,
                        "status": "disconnected",
                        "metadata": {},
                    }
                )
                .execute()
            )

            if not connection_response.data:
                raise Exception(
                    "A conexão não foi criada."
                )

            connection_created = True

        except Exception as error:
            print(
                "Erro ao criar conexão:",
                error,
            )

            try:
                await evolution.delete_instance(
                    instance_name
                )
            except Exception as evolution_error:
                print(
                    "Erro ao remover instância:",
                    evolution_error,
                )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Não foi possível criar "
                    "a conexão do WhatsApp."
                ),
            )

        connection = connection_response.data[0]

        return {
            "message": "Bot criado com sucesso.",
            "bot": bot,
            "instance": {
                "name": instance_name,
                "webhook_url": webhook_url,
            },
            "connection": connection,
            "evolution": evolution_response,
        }

    except HTTPException:
        if bot_id and not connection_created:
            try:
                if evolution_created:
                    await evolution.delete_instance(
                        instance_name
                    )
            except Exception as cleanup_error:
                print(
                    "Erro ao limpar instância:",
                    cleanup_error,
                )

            try:
                (
                    supabase_admin
                    .table("bots")
                    .delete()
                    .eq("id", bot_id)
                    .execute()
                )
            except Exception as cleanup_error:
                print(
                    "Erro ao limpar bot:",
                    cleanup_error,
                )

        raise

    except Exception as error:
        print(
            "Erro ao criar bot:",
            error,
        )

        if bot_id:
            try:
                (
                    supabase_admin
                    .table("whatsapp_connections")
                    .delete()
                    .eq("bot_id", bot_id)
                    .execute()
                )
            except Exception as cleanup_error:
                print(
                    "Erro ao limpar conexão:",
                    cleanup_error,
                )

            try:
                await evolution.delete_instance(
                    instance_name
                )
            except Exception as evolution_error:
                print(
                    "Erro ao limpar instância:",
                    evolution_error,
                )

            try:
                (
                    supabase_admin
                    .table("bots")
                    .delete()
                    .eq("id", bot_id)
                    .execute()
                )
            except Exception as cleanup_error:
                print(
                    "Erro ao limpar bot:",
                    cleanup_error,
                )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível criar o bot.",
        )


@router.get("/{bot_id}")
async def get_bot(
    bot_id: UUID,
    client: dict = Depends(get_current_client),
):
    try:
        bot = await find_bot(
            bot_id,
            client["id"],
        )

        return {
            "bot": bot,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao buscar bot:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar o bot.",
        )


@router.patch("/{bot_id}")
async def update_bot(
    bot_id: UUID,
    data: UpdateBotRequest,
    client: dict = Depends(get_current_client),
):
    try:
        await find_bot(
            bot_id,
            client["id"],
        )

        updates = data.model_dump(
            exclude_unset=True
        )

        if not updates:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Nenhum campo foi enviado "
                    "para atualização."
                ),
            )

        if "name" in updates:
            if updates["name"] is not None:
                updates["name"] = (
                    updates["name"].strip()
                )

                if not updates["name"]:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "O nome do bot "
                            "não pode estar vazio."
                        ),
                    )

        if "description" in updates:
            if updates["description"] is not None:
                updates["description"] = (
                    updates["description"].strip()
                )

        if "model" in updates:
            if updates["model"] is not None:
                updates["model"] = (
                    updates["model"].strip()
                )

                if not updates["model"]:
                    updates["model"] = (
                        "gemini-3.1-flash-lite"
                    )

        if "system_prompt" in updates:
            if updates["system_prompt"] is not None:
                updates["system_prompt"] = (
                    updates["system_prompt"].strip()
                )

        response = (
            supabase_admin
            .table("bots")
            .update(updates)
            .eq("id", str(bot_id))
            .eq("client_id", client["id"])
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Bot não encontrado.",
            )

        return {
            "message": "Bot atualizado com sucesso.",
            "bot": response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao atualizar bot:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível atualizar o bot.",
        )


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: UUID,
    client: dict = Depends(get_current_client),
):
    try:
        bot = await find_bot(
            bot_id,
            client["id"],
        )

        instance_name = bot.get(
            "instance_name"
        )

        if instance_name:
            try:
                await evolution.delete_instance(
                    instance_name
                )

                print(
                    f"Instância removida: "
                    f"{instance_name}"
                )

            except Exception as error:
                print(
                    "Aviso ao remover instância:",
                    error,
                )

        try:
            (
                supabase_admin
                .table("whatsapp_connections")
                .delete()
                .eq("bot_id", str(bot_id))
                .eq("client_id", client["id"])
                .execute()
            )

        except Exception as error:
            print(
                "Erro ao remover conexão:",
                error,
            )

        response = (
            supabase_admin
            .table("bots")
            .delete()
            .eq("id", str(bot_id))
            .eq("client_id", client["id"])
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Bot não encontrado.",
            )

        return {
            "message": "Bot excluído com sucesso.",
            "bot_id": str(bot_id),
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao excluir bot:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível excluir o bot.",
        )


@router.get("/{bot_id}/connection")
async def get_bot_connection(
    bot_id: UUID,
    client: dict = Depends(get_current_client),
):
    try:
        await find_bot(
            bot_id,
            client["id"],
        )

        response = (
            supabase_admin
            .table("whatsapp_connections")
            .select("*")
            .eq("bot_id", str(bot_id))
            .eq("client_id", client["id"])
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Conexão do WhatsApp "
                    "não encontrada."
                ),
            )

        return {
            "connection": response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Erro ao buscar conexão:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível carregar "
                "a conexão do WhatsApp."
            ),
        )
