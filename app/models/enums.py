import enum


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class TransactionType(str, enum.Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"


class PaymentProvider(str, enum.Enum):
    STRIPE = "STRIPE"
    PAYPAL = "PAYPAL"
    RAZORPAY = "RAZORPAY"


class Currency(str, enum.Enum):
    USD = "USD"
    INR = "INR"
    EUR = "EUR"
