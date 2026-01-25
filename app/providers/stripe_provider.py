import stripe
from typing import Dict, Any
from fastapi.concurrency import run_in_threadpool
from app.providers.base import BasePaymentProvider
from app.core.config import settings
from app.core.logging import logger

# import json   # local testing without signature verification

# Configure Stripe Key globally
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeProvider(BasePaymentProvider):
    async def create_order(self, payment) -> Dict[str, Any]:
        """
        Creates a Stripe PaymentIntent.
        Wrapped in run_in_threadpool because stripe-python is blocking.
        """
        try:
            amount_in_cents = int(payment.amount * 100)

            # Using run_in_threadpool prevents the blocking Stripe call
            # from freezing the FastAPI event loop
            intent = await run_in_threadpool(
                stripe.PaymentIntent.create,
                amount=amount_in_cents,
                currency=payment.currency.lower(),
                metadata={
                    "idempotency_key": payment.idempotency_key,
                    "external_order_id": payment.external_order_id,
                },
            )

            return {
                "provider_transaction_id": intent.id,
                "client_secret": intent.client_secret,
                "raw_response": intent,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Order Creation Failed: {str(e)}")
            raise ValueError(f"Provider Error: {e.user_message or str(e)}")

    async def verify_webhook(self, payload: bytes, headers: dict) -> Dict[str, Any]:
        """
        Verifies the signature and parses the Stripe Event.
        """
        sign_header = headers.get("stripe-signature")
        try:
            # CPU-bound hashing: run_in_threadpool keeps the event loop free
            event = await run_in_threadpool(
                stripe.Webhook.construct_event,
                payload,
                sign_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )

            obj = event["data"]["object"]

            # Step 1: Extract the Correct ID (Always target the pi_...)
            if event["type"].startswith("payment_intent"):
                provider_tx_id = obj["id"]  # The pi_... ID
            elif event["type"].startswith("charge"):
                provider_tx_id = obj.get(
                    "payment_intent"
                )  # Get pi_... from charge object
            else:
                provider_tx_id = obj.get("id")

            # Step 2: Map Statuses (Added charge.succeeded here)
            status_mapping = {
                "payment_intent.succeeded": "SUCCESS",
                "charge.succeeded": "SUCCESS",
                "payment_intent.payment_failed": "FAILED",
                "charge.failed": "FAILED",
                "payment_intent.canceled": "FAILED",
                "payment_intent.processing": "PENDING",
            }

            return {
                "provider_tx_id": provider_tx_id,
                "status": status_mapping.get(event["type"], "PENDING"),
                "raw_data": event,
            }
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe signature verification failed: {str(e)}")
            raise ValueError("Invalid signature")
        except Exception as e:
            logger.error(f"Webhook parsing error: {str(e)}")
            raise ValueError("Webhook processing failed")

    async def get_status(self, provider_tx_id: str) -> str:
        """
        Retrieves the latest status directly from Stripe.
        Used for manual sync or when webhooks are delayed.
        """
        try:
            intent = await run_in_threadpool(
                stripe.PaymentIntent.retrieve, provider_tx_id
            )

            # Mapping based on Stripe's PaymentIntent status lifecycle
            status_mapping = {
                "succeeded": "SUCCESS",
                "requires_payment_method": "PENDING",
                "canceled": "FAILED",
                "processing": "PENDING",
                "requires_action": "PENDING",  # Waiting for 3D Secure
                "requires_confirmation": "PENDING",
            }
            return status_mapping.get(intent.status, "PENDING")
        except stripe.error.StripeError as e:
            logger.error(f"Stripe status sync failed for {provider_tx_id}: {str(e)}")
            return "PENDING"  # Fallback to current state

    async def refund(self, provider_tx_id: str, amount: float) -> Dict[str, Any]:
        """
        Issues a refund to the customer's card via Stripe.
        """
        try:
            amount_in_cents = int(amount * 100)

            refund = await run_in_threadpool(
                stripe.Refund.create,
                payment_intent=provider_tx_id,
                amount=amount_in_cents,
            )

            return {
                "id": refund.id,
                "status": refund.status,  # usually 'succeeded' or 'pending'
                "raw_response": refund,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Refund Failed for {provider_tx_id}: {str(e)}")
            raise ValueError(f"Refund Failed: {e.user_message or str(e)}")


# ============= TO TEST LOCALLY WITHOUT SIGNATURE VERIFICATION =====================
# async def verify_webhook(self, payload: bytes, headers: dict) -> Dict[str, Any]:
#     try:
#         # --- COMMENT OUT THE REAL VERIFICATION ---
#         # event = await run_in_threadpool(
#         #     stripe.Webhook.construct_event,
#         #     payload,
#         #     headers.get("stripe-signature"),
#         #     settings.STRIPE_WEBHOOK_SECRET,
#         # )

#         # --- ADD THIS MOCK LINE INSTEAD ---
#         event = json.loads(payload)
#         # ------------------------------------------

#         obj = event["data"]["object"]

#         if event["type"].startswith("payment_intent"):
#             provider_tx_id = obj["id"]
#         elif event["type"].startswith("charge"):
#             provider_tx_id = obj.get("payment_intent")
#         else:
#             provider_tx_id = obj.get("id")

#         status_mapping = {
#             "payment_intent.succeeded": "SUCCESS",
#             "charge.succeeded": "SUCCESS",
#             # ... keep your existing mapping ...
#         }

#         return {
#             "provider_tx_id": provider_tx_id,
#             "status": status_mapping.get(event["type"], "PENDING"),
#             "raw_data": event,
#         }
#     except Exception as e:
#         logger.error(f"Webhook parsing error: {str(e)}")
#         raise ValueError("Webhook processing failed")
