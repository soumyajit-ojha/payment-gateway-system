from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.services.payment_service import payment_service
from app.routers.deps import get_current_client
from app.models.client import ClientApp
from app.models.transaction import Transaction
from app.providers.factory import PaymentProviderFactory

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


@router.post("/{transaction_id}/refund")
async def refund_payment(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: ClientApp = Depends(get_current_client),
):
    """
    Allows a client app to refund a specific transaction.
    Verification: Ensures the transaction belongs to the requesting client.
    """
    # 1. Find transaction and verify ownership
    tx = await db.get(Transaction, transaction_id)

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.client_app_id != current_client.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to refund this transaction",
        )

    if tx.status != "SUCCESS":
        raise HTTPException(
            status_code=400, detail=f"Cannot refund transaction in {tx.status} state"
        )

    try:
        # 2. Get Provider implementation and process refund
        provider = PaymentProviderFactory.get_provider_by_name(tx.provider)
        result = await provider.refund(tx.provider_transaction_id, float(tx.amount))

        # 3. Update DB
        tx.status = "REFUNDED"
        tx.provider_metadata = {
            "refund_info": result,
            "previous_meta": tx.provider_metadata,
        }
        await db.commit()

        return {"status": "refunded", "refund_id": result.get("id")}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{provider_tx_id}/sync")
async def sync_status(provider_tx_id: str, db: AsyncSession = Depends(get_db)):
    """
    Manually pulls the latest status from the provider (Stripe/Razorpay).
    Useful if a webhook was missed or delayed.
    """
    # 1. Get transaction
    # tx = await db.get(Transaction, provider_tx_id)
    query = select(Transaction).where(
        Transaction.provider_transaction_id == provider_tx_id
    )
    result = await db.execute(query)
    tx = result.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # --- IMMUTABILITY CHECK ---
    # If the transaction is already SUCCESS or REFUNDED, do not change it!
    # These are "Terminal States".
    if tx.status in ["SUCCESS", "REFUNDED"]:
        return {
            "transaction_id": provider_tx_id,
            "status": tx.status,
            "message": "Transaction is already in a final state.",
        }

    try:
        provider = PaymentProviderFactory.get_provider_by_name(tx.provider)
        new_status = await provider.get_status(tx.provider_transaction_id)

        # Only update if the status is actually different
        if tx.status != new_status:
            tx.status = new_status
            await db.commit()

        return {
            "transaction_id": provider_tx_id,
            "status": new_status,
            "synced_from_provider": True,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sync failed: {str(e)}")
