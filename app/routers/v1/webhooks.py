from fastapi import APIRouter, Request, Header, HTTPException, Depends
from app.providers.factory import PaymentProviderFactory
from app.tasks.payment_tasks import update_transaction_status_task
from app.core.logging import logger

router = APIRouter()


@router.post("/{provider}")
async def handle_webhook(provider: str, request: Request):
    """
    Unified Webhook Listener.
    Routes: /api/v1/webhooks/stripe, /api/v1/webhooks/razorpay
    """
    # 1. Get raw body and headers
    payload = await request.body()
    headers = dict(request.headers)

    # 2. Get the correct provider implementation
    try:
        # Note: We need a slight variation of the factory to get provider by name
        provider_impl = PaymentProviderFactory.get_provider_by_name(provider)
    except Exception:
        raise HTTPException(status_code=404, detail="Provider not found")

    # 3. Verify the signature
    try:
        verified_data = await provider_impl.verify_webhook(payload, headers)
    except ValueError as e:
        logger.error(f"Webhook verification failed for {provider}: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 4. Offload processing to Celery (Async)
    # We pass the data to Celery and return 200 OK immediately
    update_transaction_status_task.delay(
        provider_tx_id=verified_data["provider_tx_id"],
        status=verified_data["status"],
        raw_data=verified_data["raw_data"],
    )

    return {"status": "received"}
