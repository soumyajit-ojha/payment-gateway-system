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
                new_transaction, gateway_data.get("client_secret")
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Provider Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment provider communication failed",
            )

    @staticmethod
    async def update_transaction_status(
        provider_transaction_id: str, new_status: str, metadata: dict
    ):
        """
        GATEWAY APP: Triggered by Stripe Webhook.
        Updates local DB and notifies SellPhone.
        """
        # 1. Update local Gateway Database
        # (Your code to update local 'transactions' table goes here)
        logger.info(f"Transaction {provider_transaction_id} updated to {new_status}")

        # 2. Extract the identifier we sent to Stripe
        # In Stripe, this is stored in metadata
        external_order_id = metadata.get("metadata", {}).get("external_order_id")

        if not external_order_id:
            logger.error(f"Missing external_order_id for TX {provider_transaction_id}")
            return

        # 3. If Succeeded, call SellPhone's Webhook
        if new_status == "succeeded":
            await PaymentGatewayService.notify_sellphone_backend(
                external_order_id, "success"
            )
        elif new_status == "failed":
            await PaymentGatewayService.notify_sellphone_backend(
                external_order_id, "failed"
            )

    @staticmethod
    async def notify_client_app(external_order_id: str, status: str):
        """
        Sends a POST request to the calling service to confirm payment.
        """
        # In a real scenario, this URL would come from the ClientApp table.
        # Placeholder for your internal e-commerce webhook URL:
        SELLPHONE_WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/orders/webhook/payment"
        INTERNAL_API_KEY = "pg_bc16c1ef14814ca39eeea71ef3c9f94a"

        async with httpx.AsyncClient() as client:
            payload = {"external_order_id": external_order_id, "status": status}
            headers = {"x-api-key": INTERNAL_API_KEY}

            try:
                response = await client.post(
                    SELLPHONE_WEBHOOK_URL, json=payload, headers=headers, timeout=10.0
                )
                if response.status_code == 200:
                    logger.info(
                        f"SellPhone notified successfully for {external_order_id}"
                    )
                else:
                    logger.error(
                        f"SellPhone notification failed: {response.status_code}"
                    )
            except Exception as e:
                logger.error(f"Failed to reach SellPhone Backend: {str(e)}")

    async def _get_existing_transaction(self, db: AsyncSession, key: str):
        result = await db.execute(
            select(Transaction).where(Transaction.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    def _format_response(
        self, tx: Transaction, client_secret: str = None
    ) -> PaymentResponse:
        return PaymentResponse(
            gateway_transaction_id=tx.id,
            provider_transaction_id=tx.provider_transaction_id,
            client_secret=client_secret,
            status=tx.status,
        )


# Global instance
payment_service = PaymentService()

# what is the value of client_webhook_url and checkout_url
