from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.services.mercado_pago import (
    MercadoPagoError,
    create_subscription,
    get_subscription,
)


router = APIRouter(
    prefix="/mercado-pago",
    tags=["Mercado Pago"],
)


class CheckoutRequest(BaseModel):
    email: EmailStr

    # Mantemos o valor controlado pela API.
    # O frontend não pode alterar o preço da assinatura.
    plan: str = Field(default="pro")


class CheckoutResponse(BaseModel):
    subscription_id: str
    status: str
    checkout_url: str


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
)
async def create_checkout(data: CheckoutRequest):
    if data.plan != "pro":
        raise HTTPException(
            status_code=400,
            detail="Plano inválido.",
        )

    amount = 99.90

    external_reference = (
        f"WAPPI-PRO-{uuid4().hex}"
    )

    try:
        subscription = await create_subscription(
            email=data.email,
            external_reference=external_reference,
            amount=amount,
        )

    except MercadoPagoError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    subscription_id = subscription.get("id")
    checkout_url = subscription.get("init_point")

    if not subscription_id or not checkout_url:
        raise HTTPException(
            status_code=502,
            detail=(
                "O Mercado Pago criou a assinatura, "
                "mas não retornou o checkout."
            ),
        )

    return CheckoutResponse(
        subscription_id=subscription_id,
        status=subscription.get("status", "pending"),
        checkout_url=checkout_url,
    )


@router.get(
    "/subscriptions/{subscription_id}",
)
async def subscription_status(subscription_id: str):
    try:
        subscription = await get_subscription(
            subscription_id
        )

    except MercadoPagoError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    return {
        "id": subscription.get("id"),
        "status": subscription.get("status"),
        "payer_id": subscription.get("payer_id"),
        "payment_method_id": subscription.get(
            "payment_method_id"
        ),
        "next_payment_date": subscription.get(
            "next_payment_date"
        ),
        "external_reference": subscription.get(
            "external_reference"
        ),
    }
