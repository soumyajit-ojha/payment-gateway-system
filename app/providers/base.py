from abc import ABC, abstractmethod
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.models.enums import TransactionStatus


class BasePaymentProvider(ABC):
    @abstractmethod
    async def create_order(self, payment: PaymentInitiate) -> dict:
        """Talks to the external API (Stripe/Razorpay/etc)"""
        pass

    @abstractmethod
    async def verify_webhook(self, payload: bytes, headers: dict) -> bool:
        """Verifies the signature of the webhook"""
        pass
