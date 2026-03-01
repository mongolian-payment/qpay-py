"""QPay payment gateway SDK for Python.

Provides synchronous and asynchronous clients for the QPay V2 API.

Example::

    from mongolian_payment_qpay import QPayClient, QPayConfig, CreateInvoiceInput

    client = QPayClient(QPayConfig(
        username="MY_USERNAME",
        password="MY_PASSWORD",
        endpoint="https://merchant.qpay.mn/v2",
        callback="https://example.com/callback",
        invoice_code="MY_INVOICE_CODE",
        merchant_id="MY_MERCHANT_ID",
    ))

    invoice = client.create_invoice(CreateInvoiceInput(
        sender_code="SENDER",
        sender_branch_code="BRANCH",
        receiver_code="RECEIVER",
        description="Test payment",
        amount=1000,
    ))
"""

from .client import AsyncQPayClient, QPayClient
from .config import load_config_from_env
from .errors import QPayError
from .types import (
    CancelPaymentOptions,
    CheckPaymentOptions,
    CreateInvoiceInput,
    QPayConfig,
    QPayDeeplink,
    QPayInvoiceGetResponse,
    QPayInvoiceResponse,
    QPayPaymentCheckResponse,
    QPayPaymentRow,
)

__all__ = [
    "AsyncQPayClient",
    "CancelPaymentOptions",
    "CheckPaymentOptions",
    "CreateInvoiceInput",
    "load_config_from_env",
    "QPayClient",
    "QPayConfig",
    "QPayDeeplink",
    "QPayError",
    "QPayInvoiceGetResponse",
    "QPayInvoiceResponse",
    "QPayPaymentCheckResponse",
    "QPayPaymentRow",
]
