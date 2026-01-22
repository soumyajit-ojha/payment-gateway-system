import stripe
from fastapi.concurrency import run_in_threadpool
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
            intent = await run_in_threadpool(
                stripe.PaymentIntent.create,
                amount=amount_in_cents,
                currency=payment.currency.lower(),
                metadata={
                    "external_order_id": payment.external_order_id,
                    "idempotency_key": payment.idempotency_key,
                },
            )

            return {
                "provider_transaction_id": intent.id,
                "checkout_url": intent.get("next_action"),  # If using Stripe 3DS
                "raw_response": intent,
            }
        except Exception as e:
            logger.error(f"Stripe Order Creation Failed: {str(e)}")
            raise

    async def verify_webhook(self, payload, headers):
        sig_header = headers.get("stripe-signature")
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
