from fastapi import Depends

from app.core.security import get_current_user


async def current_user(
    user: dict = Depends(get_current_user),
):
    return user
