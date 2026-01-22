# from app.core.celery_app import celery_app
# from app.core.logging import logger
# from app.providers.factory import PaymentProviderFactory


# @celery_app.task(
#     name="process_webhook_event",
#     autoretry_for=(Exception,),
#     retry_kwargs={"max_retries": 5},
# )
# def process_webhook_event(provider_name: str, payload: dict):
#     """
#     Background task to process payment success/failure.
#     If this fails, Celery will automatically retry.
#     """
#     logger.info(f"Background processing webhook for {provider_name}")

#     # 1. Update Database Status to SUCCESS or FAILED
#     # 2. Call the E-commerce App's API to notify them: "Order #123 is paid!"
#     # 3. Send receipt emails
#     pass


# @celery_app.task(name="sync_pending_transactions")
# def sync_pending_transactions():
#     """
#     Celery Beat task: Runs every 10 mins.
#     Queries providers for status of PENDING orders.
#     """
#     # 1. Fetch PENDING transactions from DB older than 15 mins
#     # 2. For each, call provider.get_order_status(id)
#     # 3. Update DB accordingly
#     pass


from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.transaction import Transaction
from app.models.enums import TransactionStatus
from sqlalchemy import select, update
import asyncio


@celery_app.task(name="update_transaction_status")
def update_transaction_status_task(provider_tx_id: str, status: str, raw_data: dict):
    """
    Background task to update the database and notify external services.
    We use a helper to run the async logic in the sync Celery worker.
    """

    async def _logic():
        async with AsyncSessionLocal() as db:
            # 1. Update our Database
            stmt = (
                update(Transaction)
                .where(Transaction.provider_transaction_id == provider_tx_id)
                .values(
                    status=(
                        TransactionStatus.SUCCESS
                        if status == "SUCCESS"
                        else TransactionStatus.FAILED
                    ),
                    provider_metadata=raw_data,
                )
                .returning(Transaction)
            )
            result = await db.execute(stmt)
            tx = result.scalar_one_or_none()
            await db.commit()

            if tx:
                # 2. TRIGGER: Notify the E-commerce service
                # Logic: requests.post(tx.client.webhook_url, data={"order_id": tx.external_order_id, ...})
                print(f"NOTIFIED CLIENT: Transaction {tx.id} is {status}")

    # Run the async logic
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_logic())
