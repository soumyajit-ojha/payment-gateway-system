import razorpay
from fastapi.concurrency import run_in_threadpool
from app.providers.base import BasePaymentProvider
from app.core.config import settings
from app.core.logging import logger

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class RazorpayProvider(BasePaymentProvider):
    async def create_order(self, payment):
        try:
            # Razorpay works in paise (1.00 INR = 100)
            amount_in_paise = int(payment.amount * 100)

            data = {
                "amount": amount_in_paise,
                "currency": payment.currency.upper(),
                "receipt": payment.external_order_id,
                "notes": {"idempotency_key": payment.idempotency_key},
            }

            order = await run_in_threadpool(client.order.create, data=data)

            return {
                "provider_transaction_id": order["id"],
                "checkout_url": None,  # Razorpay usually uses a JS snippet on the frontend
                "raw_response": order,
            }
        except Exception as e:
            logger.info(f"Razorpay Order Creation Failed: {str(e)}")
            raise

    async def verify_webhook(self, payload, headers):
        # Razorpay signature verification logic
        pass
