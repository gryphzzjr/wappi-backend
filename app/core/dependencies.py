from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.services.supabase import supabase_admin


async def current_user(
    user: dict = Depends(get_current_user),
) -> dict:
    return user


async def get_current_client(
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Retorna o cliente Wappi associado ao usuário autenticado.

    Esta dependency apenas resolve o cliente.
    Regras de assinatura, expiração, permissões e status
    serão tratadas posteriormente nos respectivos módulos.
    """

    try:
        response = (
            supabase_admin
            .table("clients")
            .select("*")
            .eq("user_id", user["id"])
            .limit(1)
            .execute()
        )

    except Exception as error:
        print("Erro ao buscar cliente:", error)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível carregar o cliente.",
        ) from error

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado.",
        )

    return response.data[0]
