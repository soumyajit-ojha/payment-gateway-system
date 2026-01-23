from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.models.transaction import Transaction
from app.models.enums import TransactionStatus
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.providers.factory import PaymentProviderFactory
from app.core.logging import logger


class PaymentService:
    async def initiate_payment(
        self, db: AsyncSession, client_id: int, data: PaymentInitiate
    ) -> PaymentResponse:
        # 1. Idempotency Check (Database Level)
        # Check if this idempotency key was already used
        existing_tx = await self._get_existing_transaction(db, data.idempotency_key)
        if existing_tx:
            logger.warning(f"Idempotency hit for key: {data.idempotency_key}")
            return self._format_response(existing_tx)

        # 2. Get Provider Implementation via Factory
        # If currency is INR, Factory gives Razorpay. Else, Stripe.
        provider_impl = PaymentProviderFactory.get_provider(data.currency)

        # 3. Create initial record in our DB (Status: PENDING)
        new_transaction = Transaction(
            client_app_id=client_id,
            external_order_id=data.external_order_id,
            external_customer_id=data.external_customer_id,
            amount=data.amount,
            currency=data.currency,
            provider=data.provider,  # Based on routing logic
            idempotency_key=data.idempotency_key,
            status=TransactionStatus.PENDING,
        )

        db.add(new_transaction)
        await db.flush()  # Gets us the ID without committing the whole transaction yet

        try:
            # 4. Call the External Gateway (Stripe/Razorpay)
            logger.info(f"Calling provider for order {data.external_order_id}")
            gateway_data = await provider_impl.create_order(data)

            # 5. Update record with Gateway's ID and Metadata
            new_transaction.provider_transaction_id = gateway_data[
                "provider_transaction_id"
            ]
            new_transaction.provider_metadata = gateway_data["raw_response"]

            await db.commit()
            logger.info(
                f"Payment initiated successfully: {new_transaction.provider_transaction_id}"
            )

            return self._format_response(
                new_transaction, gateway_data.get("checkout_url")
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to initiate payment with provider: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment provider communication failed",
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
            checkout_url=checkout_url or "https://checkout.internal.com/status",
            status=tx.status,
        )

    async def update_transaction_status(
        self, provider_transaction_id: str, new_status: str, metadata: dict
    ):
        """This runs in the background to finalize the payment"""
        # We create a new session because this runs in a background thread
        async with AsyncSessionLocal() as db:
            query = (
                update(Transaction)
                .where(Transaction.provider_transaction_id == provider_transaction_id)
                .values(status=new_status, provider_metadata=metadata)
            )
            await db.execute(query)
            await db.commit()
            logger.info(
                f"Transaction {provider_transaction_id} updated to {new_status}"
            )


# Global instance
payment_service = PaymentService()
