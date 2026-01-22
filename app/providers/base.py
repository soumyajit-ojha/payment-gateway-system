from abc import ABC, abstractmethod
from typing import Dict, Any
from app.schemas.payment import PaymentInitiate


class BasePaymentProvider(ABC):
    @abstractmethod
    async def create_order(self, payment: PaymentInitiate) -> Dict[str, Any]:
        """
        Creates an order/intent in the provider's system.
        Returns a dict containing:
        - provider_transaction_id: The ID from the gateway
        - checkout_url: (Optional) URL to redirect the user
        - raw_response: The full JSON from the provider
        """
        pass

    @abstractmethod
    async def verify_webhook(
        self, payload: bytes, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Verifies the webhook signature and returns the parsed event.
        """
        pass
