import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.db.session import AsyncSessionLocal
from app.models.transaction import Transaction
from app.models.enums import TransactionStatus
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.providers.factory import PaymentProviderFactory
from app.core.logging import logger


class PaymentService:
    async def initiate_payment(
        self, db: AsyncSession, client_id: int, data: PaymentInitiate
    ) -> PaymentResponse:
        """Starts the payment flow with Stripe/Razorpay"""
        # 1. Idempotency Check
        existing_tx = await self._get_existing_transaction(db, data.idempotency_key)
        if existing_tx:
            logger.warning(f"Idempotency hit for key: {data.idempotency_key}")
            return self._format_response(existing_tx)

        # 2. Get Provider Implementation via Factory
        provider_impl = PaymentProviderFactory.get_provider(data.currency)

        # 3. Create initial record in our DB (Status: PENDING)
        new_transaction = Transaction(
            client_app_id=client_id,
            external_order_id=data.external_order_id,
            external_customer_id=data.external_customer_id,
            amount=data.amount,
            currency=data.currency,
            provider=data.provider,
            idempotency_key=data.idempotency_key,
            status=TransactionStatus.PENDING,
        )

        db.add(new_transaction)
        await db.flush()

        try:
            # 4. Call the External Gateway
            logger.info(f"Calling provider for order {data.external_order_id}")
            gateway_data = await provider_impl.create_order(data)

            # 5. Update record with Gateway's ID
            new_transaction.provider_transaction_id = gateway_data[
                "provider_transaction_id"
            ]
            new_transaction.provider_metadata = gateway_data["raw_response"]

            await db.commit()
            logger.info(f"Payment initiated: {new_transaction.provider_transaction_id}")

            return self._format_response(
                new_transaction, gateway_data.get("checkout_url")
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Provider Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment provider communication failed",
            )

    async def update_transaction_status(
        self, provider_transaction_id: str, new_status: str, metadata: dict
    ):
        """
        Runs in BackgroundTasks.
        Updates DB and then notifies the E-commerce app.
        """
        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch the full transaction record
                stmt = select(Transaction).where(
                    Transaction.provider_transaction_id == provider_transaction_id
                )
                result = await db.execute(stmt)
                tx = result.scalar_one_or_none()

                if not tx:
                    logger.error(f"Tx not found: {provider_transaction_id}")
                    return

                # 2. Check if status is already updated (Webhook Idempotency)
                if tx.status == new_status:
                    logger.info(
                        f"Tx {provider_transaction_id} already in state {new_status}"
                    )
                    return

                # 3. Update the transaction
                tx.status = new_status
                tx.provider_metadata = metadata
                await db.commit()
                await db.refresh(tx)

                logger.info(
                    f"Background Update Success: {provider_transaction_id} is now {new_status}"
                )

                # 4. Notify the external E-commerce/Client App
                await self.notify_client_app(tx)
            except Exception as e:
                logger.error(
                    f"Background Update Failed: {provider_transaction_id} is now {new_status}"
                )

    async def notify_client_app(self, transaction: Transaction):
        """
        Sends a POST request to the calling service to confirm payment.
        """
        # In a real scenario, this URL would come from the ClientApp table.
        # Placeholder for your internal e-commerce webhook URL:
        client_webhook_url = "https://your-ecommerce-app.com/api/payment-callback"

        payload = {
            "external_order_id": transaction.external_order_id,
            "status": transaction.status,
            "amount": str(transaction.amount),
            "currency": str(transaction.currency),
            "gateway_ref": transaction.provider_transaction_id,
        }

        async with httpx.AsyncClient() as client:
            try:
                # We use a 5s timeout to ensure our background task doesn't hang
                response = await client.post(
                    client_webhook_url, json=payload, timeout=5.0
                )
                response.raise_for_status()
                logger.info(
                    f"Notification sent to client for {transaction.external_order_id}"
                )
            except Exception as e:
                logger.error(
                    f"Client notification failed for {transaction.external_order_id}: {str(e)}"
                )

    async def _get_existing_transaction(self, db: AsyncSession, key: str):
        result = await db.execute(
            select(Transaction).where(Transaction.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    def _format_response(
        self, tx: Transaction, checkout_url: str = None
    ) -> PaymentResponse:
        return PaymentResponse(
            gateway_transaction_id=tx.id,
            provider_transaction_id=tx.provider_transaction_id,
            checkout_url=checkout_url or "https://yourgateway.com/status",
            status=tx.status,
        )


# Global instance
payment_service = PaymentService()

# what is the value of client_webhook_url and checkout_url
