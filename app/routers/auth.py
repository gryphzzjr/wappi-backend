from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core.security import get_current_user
from app.services.supabase import supabase, supabase_admin


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=30)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(data: RegisterRequest):
    try:
        response = supabase.auth.sign_up(
            {
                "email": data.email,
                "password": data.password,
                "options": {
                    "data": {
                        "name": data.name.strip(),
                        "phone": data.phone,
                    }
                },
            }
        )

        user = response.user
        session = response.session

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível criar a conta.",
            )

        client_response = (
            supabase_admin
            .table("clients")
            .select("*")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )

        if not client_response.data:
            raise HTTPException(
                status_code=500,
                detail="Usuário criado, mas o cliente não foi encontrado.",
            )

        client = client_response.data[0]

        if data.phone:
            phone_response = (
                supabase_admin
                .table("clients")
                .update(
                    {
                        "phone": data.phone,
                    }
                )
                .eq("user_id", user.id)
                .execute()
            )

            if phone_response.data:
                client = phone_response.data[0]

        return {
            "message": "Conta criada com sucesso.",
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "client": client,
            "session": (
                session.model_dump()
                if session
                else None
            ),
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Erro no cadastro:", error)

        error_message = str(error).lower()

        if (
            "already registered" in error_message
            or "already exists" in error_message
        ):
            raise HTTPException(
                status_code=400,
                detail="Este e-mail já está cadastrado.",
            )

        raise HTTPException(
            status_code=400,
            detail="Não foi possível criar a conta.",
        )


@router.post("/login")
async def login(data: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": data.email,
                "password": data.password,
            }
        )

        user = response.user
        session = response.session

        if not user or not session:
            raise HTTPException(
                status_code=401,
                detail="E-mail ou senha inválidos.",
            )

        client_response = (
            supabase_admin
            .table("clients")
            .select("*")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )

        if not client_response.data:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado.",
            )

        return {
            "message": "Login realizado com sucesso.",
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "client": client_response.data[0],
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_in": session.expires_in,
                "expires_at": session.expires_at,
                "token_type": session.token_type,
            },
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Erro no login:", error)

        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha inválidos.",
        )


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
):
    try:
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
                status_code=404,
                detail="Cliente não encontrado.",
            )

        return {
            "user": user,
            "client": response.data[0],
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Erro ao buscar usuário:", error)

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar os dados da conta.",
        )
