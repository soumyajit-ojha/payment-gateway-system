from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.services.payment_service import payment_service
from app.routers.deps import get_current_client  # Our Security Layer
from app.models.client import ClientApp

router = APIRouter()


@router.post(
    "/initiate", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED
)
async def create_payment(
    payload: PaymentInitiate,
    db: AsyncSession = Depends(get_db),
    current_client: ClientApp = Depends(get_current_client),
):
    """
    Unified endpoint to start a payment.
    Routes to Stripe/Razorpay based on currency.
    """
    return await payment_service.initiate_payment(
        db=db, client_id=current_client.id, data=payload
    )
