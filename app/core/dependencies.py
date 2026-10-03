from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.services.supabase import supabase_admin


async def get_current_client(
    user: dict = Depends(get_current_user),
):
    response = (
        supabase_admin
        .table("clients")
        .select("*")
        .eq("user_id", user["id"])
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado.",
        )

    return response.data[0]
