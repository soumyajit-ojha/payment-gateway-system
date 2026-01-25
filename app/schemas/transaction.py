from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.enums import TransactionStatus, TransactionType, PaymentProvider


class TransactionRead(BaseModel):
    id: int
    client_app_id: int
    external_order_id: str
    external_customer_id: str
    amount: Decimal
    currency: str
    type: TransactionType
    status: TransactionStatus
    provider: PaymentProvider
    idempotency_key: str
    provider_transaction_id: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None  # Raw JSON from Stripe/PayPal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionUpdate(BaseModel):
    """Used by webhooks to update transaction status"""

    status: TransactionStatus
    provider_transaction_id: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None
