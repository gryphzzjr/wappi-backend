from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_client
from app.services.supabase import supabase


router = APIRouter(
    prefix="/bots",
    tags=["Bots"],
)


class CreateBotRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    model: str = Field(default="gemini", max_length=50)


class UpdateBotRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=50)


@router.get("")
async def list_bots(
    client: dict = Depends(get_current_client),
):
    try:
        response = (
            supabase
            .table("bots")
            .select(
                "id, name, description, status, model, "
                "conversations_count, created_at, updated_at"
            )
            .eq("client_id", client["id"])
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "bots": response.data or [],
        }

    except Exception as error:
        print("Erro ao listar bots:", error)

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar os bots.",
        )


@router.post("")
async def create_bot(
    data: CreateBotRequest,
    client: dict = Depends(get_current_client),
):
    try:
        response = (
            supabase
            .table("bots")
            .insert(
                {
                    "client_id": client["id"],
                    "name": data.name.strip(),
                    "description": data.description.strip(),
                    "model": data.model.strip(),
                    "status": "offline",
                    "conversations_count": 0,
                }
            )
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível criar o bot.",
            )

        return {
            "message": "Bot criado com sucesso.",
            "bot": response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Erro ao criar bot:", error)

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
        response = (
            supabase
            .table("bots")
            .select(
                "id, name, description, status, model, "
                "conversations_count, created_at, updated_at"
            )
            .eq("id", str(bot_id))
            .eq("client_id", client["id"])
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Bot não encontrado.",
            )

        return {
            "bot": response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Erro ao buscar bot:", error)

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
        updates = data.model_dump(exclude_unset=True)

        if not updates:
            raise HTTPException(
                status_code=400,
                detail="Nenhum campo foi enviado para atualização.",
            )

        if "name" in updates and updates["name"] is not None:
            updates["name"] = updates["name"].strip()

        if "description" in updates and updates["description"] is not None:
            updates["description"] = updates["description"].strip()

        if "model" in updates and updates["model"] is not None:
            updates["model"] = updates["model"].strip()

        response = (
            supabase
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
        print("Erro ao atualizar bot:", error)

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
        response = (
            supabase
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
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Erro ao excluir bot:", error)

        raise HTTPException(
            status_code=500,
            detail="Não foi possível excluir o bot.",
        )
