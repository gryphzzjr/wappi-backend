from typing import Any

import httpx

from app.core.config import settings


MERCADO_PAGO_API = "https://api.mercadopago.com"


class MercadoPagoError(Exception):
    pass


async def create_subscription(
    *,
    email: str,
    external_reference: str,
    amount: float,
) -> dict[str, Any]:
    access_token = settings.mercado_pago_access_token

    if not access_token:
        raise MercadoPagoError(
            "Mercado Pago não está configurado. "
            "Defina o Access Token no ambiente da API."
        )

    payload = {
        "reason": "Wappi Pro",
        "external_reference": external_reference,
        "payer_email": email,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": amount,
            "currency_id": "BRL",
        },
        "back_url": f"{settings.APP_URL}/checkout/retorno",
        "status": "pending",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{MERCADO_PAGO_API}/preapproval",
            json=payload,
            headers=headers,
        )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.is_error:
        detail = data.get("message") or data.get("error")

        raise MercadoPagoError(
            detail or "O Mercado Pago recusou a criação da assinatura."
        )

    return data


async def get_subscription(subscription_id: str) -> dict[str, Any]:
    access_token = settings.mercado_pago_access_token

    if not access_token:
        raise MercadoPagoError(
            "Mercado Pago não está configurado."
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{MERCADO_PAGO_API}/preapproval/{subscription_id}",
            headers=headers,
        )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.is_error:
        detail = data.get("message") or data.get("error")

        raise MercadoPagoError(
            detail or "Não foi possível consultar a assinatura."
        )

    return data
