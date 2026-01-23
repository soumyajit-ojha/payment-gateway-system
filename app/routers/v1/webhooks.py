from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from app.providers.factory import PaymentProviderFactory
from app.services.payment_service import payment_service
from app.core.logging import logger

router = APIRouter()


@router.post("/{provider}")
async def handle_webhook(
    provider: str, request: Request, background_tasks: BackgroundTasks
):
    # 1. Get raw data from Stripe/Razorpay
    payload = await request.body()
    headers = dict(request.headers)

    # 2. Get the provider (Stripe or Razorpay)
    try:
        provider_impl = PaymentProviderFactory.get_provider_by_name(provider)
    except ValueError as e:
        logger.error(f"Invalid provider: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid provider")

    # 3. Verify the signature (Security check)
    try:
        verified_data = await provider_impl.verify_webhook(payload, headers)
    except Exception as e:
        logger.error(f"Webhook signature mismatch: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 4. Use FastAPI BackgroundTasks to update DB (No Celery needed!)
    background_tasks.add_task(
        payment_service.update_transaction_status,
        provider_transaction_id=verified_data["provider_tx_id"],
        new_status=verified_data["status"],
        metadata=verified_data["raw_data"],
    )

    return {"status": "accepted"}
