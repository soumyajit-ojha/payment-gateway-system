from app.models.enums import Currency, PaymentProvider
from app.providers.stripe_provider import StripeProvider
from app.providers.razorpay_provider import RazorpayProvider


class PaymentProviderFactory:
    @staticmethod
    def get_provider(currency: str):
        """Used during Payment Initiation (routes by currency)"""
        if currency.upper() == Currency.INR:
            return RazorpayProvider()
        return StripeProvider()

    @staticmethod
    def get_provider_by_name(name: str):
        """Used during Webhooks (routes by provider name)"""
        name = name.lower()
        if name == "stripe":
            return StripeProvider()
        elif name == "razorpay":
            return RazorpayProvider()
        raise ValueError(f"Unknown provider: {name}")
