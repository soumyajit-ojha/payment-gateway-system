from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.transaction import Transaction
from app.models.enums import PaymentProvider, Currency
from app.schemas.payment import PaymentInitiate
from app.providers.stripe_provider import StripeProvider
from app.providers.razorpay_provider import RazorpayProvider


class PaymentService:
    @staticmethod
    def get_provider(currency: str, requested_provider: PaymentProvider):
        # Dynamic Routing Logic
        if currency == Currency.INR:
            return RazorpayProvider()
        return StripeProvider()

    async def initiate(self, db: AsyncSession, client_id: int, data: PaymentInitiate):
        # 1. Idempotency Check
        stmt = select(Transaction).where(
            Transaction.idempotency_key == data.idempotency_key
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # 2. Select Provider
        provider_impl = self.get_provider(data.currency, data.provider)

        # 3. Create DB Record (Pending)
        db_transaction = Transaction(
            client_app_id=client_id,
            **data.model_dump(exclude={"provider"}),
            provider=data.provider,
            status="PENDING"
        )
        db.add(db_transaction)
        await db.flush()  # Get the ID without committing

        # 4. Call External Provider
        provider_response = await provider_impl.create_order(data)

        # 5. Update with Provider ID and Commit
        db_transaction.provider_transaction_id = provider_response["id"]
        await db.commit()
        return db_transaction
