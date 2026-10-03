from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import httpx

from app.core.config import settings


security = HTTPBearer()


SUPABASE_JWKS_URL = (
    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não informado.",
        )

    try:
        header = jwt.get_unverified_header(token)

        algorithm = header.get("alg")
        key_id = header.get("kid")

        if not algorithm:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )

        # =========================================================
        # JWT ASSINADO COM HS256
        # =========================================================

        if algorithm == "HS256":
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={
                    "verify_aud": False,
                },
            )

        # =========================================================
        # JWT ASSINADO COM CHAVE ASSIMÉTRICA
        # =========================================================

        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    SUPABASE_JWKS_URL
                )

            response.raise_for_status()

            jwks = response.json()

            keys = jwks.get("keys", [])

            signing_key = None

            for key in keys:
                if key.get("kid") == key_id:
                    signing_key = key
                    break

            if not signing_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Chave de assinatura do token não encontrada.",
                )

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                options={
                    "verify_aud": False,
                },
            )

        # =========================================================
        # USUÁRIO
        # =========================================================

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token não possui usuário válido.",
            )

        return {
            "id": user_id,
            "email": payload.get("email"),
        }

    except HTTPException:
        raise

    except JWTError as error:
        print("Erro ao validar JWT:", error)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        ) from error

    except httpx.HTTPError as error:
        print("Erro ao buscar chaves do Supabase:", error)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível validar a autenticação.",
        ) from error

    except Exception as error:
        print("Erro inesperado na autenticação:", error)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível validar o token.",
        ) from error
