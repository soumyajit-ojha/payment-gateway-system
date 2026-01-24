import stripe

# from fastapi.concurrency import run_in_threadpool
from app.providers.base import BasePaymentProvider
from app.core.config import settings
from app.core.logging import logger

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeProvider(BasePaymentProvider):
    async def create_order(self, payment):
        try:
            # Stripe works in cents (1.00 USD = 100)
            amount_in_cents = int(payment.amount * 100)

            # Use run_in_threadpool because the stripe library is synchronous
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=payment.currency.lower(),
                metadata={
                    "idempotency_key": payment.idempotency_key,
                },
            )

            return {
                "provider_transaction_id": intent.id,
                "raw_response": intent,
            }
        except Exception as e:
            logger.error(f"Stripe Order Creation Failed: {str(e)}")
            raise

    async def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        sig_header = headers.get("stripe-signature")
        try:
            # This verifies the event came from Stripe
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            status_mapping = {
                "payment_intent.succeeded": "SUCCESS",
                "payment_intent.payment_failed": "FAILED",
                "payment_intent.canceled": "FAILED",
            }

            return {
                "provider_tx_id": event["data"]["object"]["id"],
                "status": status_mapping.get(event["type"], "PENDING"),
                "raw_data": event,
            }
        except Exception as e:
            raise ValueError(f"Stripe signature verification failed: {str(e)}")
