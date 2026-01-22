from app.models.enums import Currency, PaymentProvider
from app.providers.stripe_provider import StripeProvider
from app.providers.razorpay_provider import RazorpayProvider


class PaymentProviderFactory:
    @staticmethod
    def get_provider(currency: str):
        """
        Logic: Route based on currency.
        INR goes to Razorpay, everything else to Stripe.
        """
        if currency.upper() == Currency.INR:
            return RazorpayProvider()
        return StripeProvider()
