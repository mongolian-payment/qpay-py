"""QPay SDK type definitions.

All request and response types are defined as dataclasses with snake_case
field names following Python conventions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QPayConfig:
    """Configuration for the QPay client."""

    username: str
    """QPay API username."""

    password: str
    """QPay API password."""

    endpoint: str
    """QPay API base endpoint (e.g. https://merchant.qpay.mn/v2)."""

    callback: str
    """Callback URL that QPay will call after payment."""

    invoice_code: str
    """Invoice code assigned by QPay."""

    merchant_id: str
    """Merchant ID assigned by QPay."""


@dataclass
class CreateInvoiceInput:
    """Input for creating an invoice."""

    sender_code: str
    """Sender code identifier."""

    sender_branch_code: str
    """Sender branch code."""

    receiver_code: str
    """Receiver code identifier."""

    description: str
    """Invoice description."""

    amount: float
    """Invoice amount."""

    callback_param: Optional[Dict[str, str]] = None
    """Optional callback query parameters."""


@dataclass
class QPayDeeplink:
    """Deeplink for a bank/wallet app."""

    name: str
    """Bank/wallet name."""

    description: str
    """Human-readable description."""

    logo: str
    """Logo URL."""

    link: str
    """Deep link URL."""


@dataclass
class QPayInvoiceResponse:
    """Response from creating an invoice."""

    invoice_id: str
    """Invoice ID."""

    qpay_short_url: str
    """Short URL for the invoice."""

    qr_text: str
    """QR code text content."""

    qr_image: str
    """Base64-encoded QR image."""

    urls: List[QPayDeeplink] = field(default_factory=list)
    """Array of bank/wallet deep links."""


@dataclass
class QPayInvoiceGetResponse:
    """Response from getting invoice details."""

    allow_exceed: bool
    """Whether amount can be exceeded."""

    allow_partial: bool
    """Whether partial payment is allowed."""

    callback_url: str
    """Callback URL."""

    discount_amount: float
    """Discount amount."""

    enable_expiry: bool
    """Whether expiry is enabled."""

    expiry_date: str
    """Expiry date."""

    gross_amount: float
    """Gross amount."""

    invoice_description: str
    """Invoice description."""

    invoice_due_date: Any
    """Invoice due date."""

    invoice_id: str
    """Invoice ID."""

    invoice_status: str
    """Invoice status."""

    maximum_amount: float
    """Maximum allowed amount."""

    minimum_amount: float
    """Minimum allowed amount."""

    note: str
    """Note."""

    sender_branch_code: str
    """Sender branch code."""

    sender_branch_data: str
    """Sender branch data."""

    sender_invoice_no: str
    """Sender invoice number."""

    surcharge_amount: float
    """Surcharge amount."""

    tax_amount: float
    """Tax amount."""

    total_amount: float
    """Total amount."""


@dataclass
class QPayPaymentRow:
    """A single payment row."""

    payment_id: str
    """Payment ID."""

    payment_status: str
    """Payment status: NEW, FAILED, PAID, REFUNDED."""

    payment_date: Any
    """Payment date."""

    payment_fee: str
    """Payment fee."""

    payment_amount: str
    """Payment amount."""

    payment_currency: str
    """Payment currency."""

    payment_wallet: str
    """Payment wallet."""

    transaction_type: str
    """Transaction type."""


@dataclass
class QPayPaymentCheckResponse:
    """Response from checking payment status."""

    count: int
    """Total number of matching payments."""

    paid_amount: float
    """Total paid amount."""

    rows: List[QPayPaymentRow] = field(default_factory=list)
    """Payment rows."""


@dataclass
class CheckPaymentOptions:
    """Options for checking payment status."""

    invoice_id: str
    """Invoice ID to check."""

    page_number: int = 1
    """Page number (default: 1)."""

    page_limit: int = 100
    """Page limit (default: 100)."""


@dataclass
class CancelPaymentOptions:
    """Options for cancelling a payment."""

    callback_url: Optional[str] = None
    """Callback URL override."""

    note: Optional[str] = None
    """Note/reason for cancellation."""
