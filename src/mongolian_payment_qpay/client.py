"""QPay V2 API clients (sync and async).

Provides :class:`QPayClient` for synchronous usage and
:class:`AsyncQPayClient` for asynchronous usage. Both share
identical method signatures.
"""

import base64
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, quote

import httpx

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

# ---------------------------------------------------------------------------
# Wire-format helpers (private)
# ---------------------------------------------------------------------------


def _build_invoice_request(
    config: QPayConfig,
    input_: CreateInvoiceInput,
) -> Dict[str, Any]:
    """Build the wire-format request body for invoice creation."""
    callback_url = config.callback
    if input_.callback_param:
        callback_url = f"{callback_url}?{urlencode(input_.callback_param)}"

    return {
        "invoice_code": config.invoice_code,
        "sender_invoice_no": input_.sender_code,
        "sender_branch_code": input_.sender_branch_code,
        "invoice_receiver_code": input_.receiver_code,
        "invoice_description": input_.description,
        "amount": input_.amount,
        "callback_url": callback_url,
    }


def _build_check_payment_request(options: CheckPaymentOptions) -> Dict[str, Any]:
    """Build the wire-format request body for payment check."""
    return {
        "object_id": options.invoice_id,
        "object_type": "INVOICE",
        "offset": {
            "page_number": options.page_number,
            "page_limit": options.page_limit,
        },
    }


def _build_cancel_payment_request(
    config: QPayConfig,
    options: Optional[CancelPaymentOptions],
) -> Dict[str, Any]:
    """Build the wire-format request body for payment cancellation."""
    return {
        "callback_url": (options.callback_url if options and options.callback_url else config.callback),
        "note": (options.note if options and options.note else ""),
    }


# ---------------------------------------------------------------------------
# Wire -> SDK mappers (private)
# ---------------------------------------------------------------------------


def _map_invoice_response(wire: Dict[str, Any]) -> QPayInvoiceResponse:
    return QPayInvoiceResponse(
        invoice_id=wire["invoice_id"],
        qpay_short_url=wire["qPay_shortUrl"],
        qr_text=wire["qr_text"],
        qr_image=wire["qr_image"],
        urls=[
            QPayDeeplink(
                name=u["name"],
                description=u["description"],
                logo=u["logo"],
                link=u["link"],
            )
            for u in wire.get("urls", [])
        ],
    )


def _map_invoice_get_response(wire: Dict[str, Any]) -> QPayInvoiceGetResponse:
    return QPayInvoiceGetResponse(
        allow_exceed=wire["allow_exceed"],
        allow_partial=wire["allow_partial"],
        callback_url=wire["callback_url"],
        discount_amount=wire["discount_amount"],
        enable_expiry=wire["enable_expiry"],
        expiry_date=wire["expiry_date"],
        gross_amount=wire["gross_amount"],
        invoice_description=wire["invoice_description"],
        invoice_due_date=wire["invoice_due_date"],
        invoice_id=wire["invoice_id"],
        invoice_status=wire["invoice_status"],
        maximum_amount=wire["maximum_amount"],
        minimum_amount=wire["minimum_amount"],
        note=wire["note"],
        sender_branch_code=wire["sender_branch_code"],
        sender_branch_data=wire["sender_branch_data"],
        sender_invoice_no=wire["sender_invoice_no"],
        surcharge_amount=wire["surcharge_amount"],
        tax_amount=wire["tax_amount"],
        total_amount=wire["total_amount"],
    )


def _map_payment_row(wire: Dict[str, Any]) -> QPayPaymentRow:
    return QPayPaymentRow(
        payment_id=wire["payment_id"],
        payment_status=wire["payment_status"],
        payment_date=wire["payment_date"],
        payment_fee=wire["payment_fee"],
        payment_amount=wire["payment_amount"],
        payment_currency=wire["payment_currency"],
        # Note: intentional typo from the QPay API ("payemnt_wallet")
        payment_wallet=wire["payemnt_wallet"],
        transaction_type=wire["transaction_type"],
    )


def _map_payment_check_response(
    wire: Dict[str, Any],
) -> QPayPaymentCheckResponse:
    return QPayPaymentCheckResponse(
        count=wire["count"],
        paid_amount=wire["paid_amount"],
        rows=[_map_payment_row(r) for r in wire.get("rows", [])],
    )


def _basic_auth_header(username: str, password: str) -> str:
    """Return the Basic auth header value."""
    credentials = base64.b64encode(
        f"{username}:{password}".encode()
    ).decode()
    return f"Basic {credentials}"


# ---------------------------------------------------------------------------
# Token storage mixin
# ---------------------------------------------------------------------------

_MARGIN_SECONDS = 60


class _TokenStore:
    """Shared token state used by both sync and async clients."""

    def __init__(self) -> None:
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._refresh_expires_at: float = 0.0

    def _set_tokens(self, data: Dict[str, Any]) -> None:
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        now = time.time()
        self._token_expires_at = now + (data["expires_in"] - _MARGIN_SECONDS)
        self._refresh_expires_at = now + (data["refresh_expires_in"] - _MARGIN_SECONDS)

    def _token_valid(self) -> bool:
        return bool(self._access_token and time.time() < self._token_expires_at)

    def _refresh_valid(self) -> bool:
        return bool(self._refresh_token and time.time() < self._refresh_expires_at)


# ---------------------------------------------------------------------------
# Sync Client
# ---------------------------------------------------------------------------


class QPayClient(_TokenStore):
    """Synchronous QPay V2 API client.

    Handles authentication (login + token refresh), invoice management,
    and payment operations.

    Example::

        from mongolian_payment_qpay import QPayClient

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

    Args:
        config: QPay configuration.
    """

    def __init__(self, config: QPayConfig) -> None:
        super().__init__()
        self.config = config
        self._client = httpx.Client()

    # -- Auth ---------------------------------------------------------------

    def _auth(self) -> str:
        if self._token_valid():
            return self._access_token  # type: ignore[return-value]
        if self._refresh_valid():
            return self._refresh()
        return self._login()

    def _login(self) -> str:
        res = self._client.post(
            f"{self.config.endpoint}/auth/token",
            headers={
                "Authorization": _basic_auth_header(self.config.username, self.config.password),
                "Content-Type": "application/json",
            },
        )
        if res.status_code >= 400:
            body = res.text
            raise QPayError(
                f"QPay login failed ({res.status_code})",
                status_code=res.status_code,
                response=body,
            )
        data = res.json()
        self._set_tokens(data)
        return self._access_token  # type: ignore[return-value]

    def _refresh(self) -> str:
        res = self._client.post(
            f"{self.config.endpoint}/auth/refresh",
            headers={
                "Authorization": f"Bearer {self._refresh_token}",
                "Content-Type": "application/json",
            },
        )
        if res.status_code >= 400:
            return self._login()
        data = res.json()
        self._set_tokens(data)
        return self._access_token  # type: ignore[return-value]

    # -- HTTP helper --------------------------------------------------------

    def _request(self, method: str, path: str, body: Any = None) -> Any:
        token = self._auth()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.endpoint}{path}"

        kwargs: Dict[str, Any] = {"headers": headers}
        if body is not None:
            kwargs["json"] = body

        res = self._client.request(method, url, **kwargs)

        # 204 No Content
        if res.status_code == 204:
            return None

        content_type = res.headers.get("content-type", "")
        if "application/json" in content_type:
            response_body = res.json()
        else:
            response_body = res.text

        if res.status_code >= 400:
            raise QPayError(
                f"QPay API error: {method} {path} ({res.status_code})",
                status_code=res.status_code,
                response=response_body,
            )
        return response_body

    # -- Invoice operations -------------------------------------------------

    def create_invoice(self, input_: CreateInvoiceInput) -> QPayInvoiceResponse:
        """Create a new invoice.

        Args:
            input_: Invoice creation parameters.

        Returns:
            The created invoice with QR code and deep links.
        """
        wire_body = _build_invoice_request(self.config, input_)
        wire = self._request("POST", "/invoice", wire_body)
        return _map_invoice_response(wire)

    def get_invoice(self, invoice_id: str) -> QPayInvoiceGetResponse:
        """Get invoice details by ID.

        Args:
            invoice_id: The invoice ID.

        Returns:
            Invoice details.
        """
        wire = self._request("GET", f"/invoice/{quote(invoice_id, safe='')}")
        return _map_invoice_get_response(wire)

    def cancel_invoice(self, invoice_id: str) -> None:
        """Cancel an invoice by ID.

        Args:
            invoice_id: The invoice ID to cancel.
        """
        self._request("DELETE", f"/invoice/{quote(invoice_id, safe='')}")

    # -- Payment operations -------------------------------------------------

    def get_payment(self, payment_id: str) -> QPayPaymentRow:
        """Get payment details by ID.

        Args:
            payment_id: The payment ID.

        Returns:
            Payment details.
        """
        wire = self._request("GET", f"/payment/get/{quote(payment_id, safe='')}")
        return _map_payment_row(wire)

    def check_payment(self, options: CheckPaymentOptions) -> QPayPaymentCheckResponse:
        """Check payment status for an invoice.

        Args:
            options: Check payment options including invoice_id and pagination.

        Returns:
            Payment check response with count, paid amount, and payment rows.
        """
        wire_body = _build_check_payment_request(options)
        wire = self._request("POST", "/payment/check", wire_body)
        return _map_payment_check_response(wire)

    def cancel_payment(self, options: Optional[CancelPaymentOptions] = None) -> None:
        """Cancel a payment.

        Args:
            options: Cancel payment options.
        """
        wire_body = _build_cancel_payment_request(self.config, options)
        self._request("DELETE", "/payment/cancel", wire_body)

    def refund_payment(self, payment_id: str) -> None:
        """Refund a payment by ID.

        Args:
            payment_id: The payment ID to refund.
        """
        self._request("DELETE", f"/payment/refund/{quote(payment_id, safe='')}")


# ---------------------------------------------------------------------------
# Async Client
# ---------------------------------------------------------------------------


class AsyncQPayClient(_TokenStore):
    """Asynchronous QPay V2 API client.

    Handles authentication (login + token refresh), invoice management,
    and payment operations. All methods are async.

    Example::

        import asyncio
        from mongolian_payment_qpay import AsyncQPayClient

        async def main():
            client = AsyncQPayClient(QPayConfig(
                username="MY_USERNAME",
                password="MY_PASSWORD",
                endpoint="https://merchant.qpay.mn/v2",
                callback="https://example.com/callback",
                invoice_code="MY_INVOICE_CODE",
                merchant_id="MY_MERCHANT_ID",
            ))

            invoice = await client.create_invoice(CreateInvoiceInput(
                sender_code="SENDER",
                sender_branch_code="BRANCH",
                receiver_code="RECEIVER",
                description="Test payment",
                amount=1000,
            ))

        asyncio.run(main())

    Args:
        config: QPay configuration.
    """

    def __init__(self, config: QPayConfig) -> None:
        super().__init__()
        self.config = config
        self._client = httpx.AsyncClient()

    # -- Auth ---------------------------------------------------------------

    async def _auth(self) -> str:
        if self._token_valid():
            return self._access_token  # type: ignore[return-value]
        if self._refresh_valid():
            return await self._refresh()
        return await self._login()

    async def _login(self) -> str:
        res = await self._client.post(
            f"{self.config.endpoint}/auth/token",
            headers={
                "Authorization": _basic_auth_header(self.config.username, self.config.password),
                "Content-Type": "application/json",
            },
        )
        if res.status_code >= 400:
            body = res.text
            raise QPayError(
                f"QPay login failed ({res.status_code})",
                status_code=res.status_code,
                response=body,
            )
        data = res.json()
        self._set_tokens(data)
        return self._access_token  # type: ignore[return-value]

    async def _refresh(self) -> str:
        res = await self._client.post(
            f"{self.config.endpoint}/auth/refresh",
            headers={
                "Authorization": f"Bearer {self._refresh_token}",
                "Content-Type": "application/json",
            },
        )
        if res.status_code >= 400:
            return await self._login()
        data = res.json()
        self._set_tokens(data)
        return self._access_token  # type: ignore[return-value]

    # -- HTTP helper --------------------------------------------------------

    async def _request(self, method: str, path: str, body: Any = None) -> Any:
        token = await self._auth()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.endpoint}{path}"

        kwargs: Dict[str, Any] = {"headers": headers}
        if body is not None:
            kwargs["json"] = body

        res = await self._client.request(method, url, **kwargs)

        # 204 No Content
        if res.status_code == 204:
            return None

        content_type = res.headers.get("content-type", "")
        if "application/json" in content_type:
            response_body = res.json()
        else:
            response_body = res.text

        if res.status_code >= 400:
            raise QPayError(
                f"QPay API error: {method} {path} ({res.status_code})",
                status_code=res.status_code,
                response=response_body,
            )
        return response_body

    # -- Invoice operations -------------------------------------------------

    async def create_invoice(self, input_: CreateInvoiceInput) -> QPayInvoiceResponse:
        """Create a new invoice.

        Args:
            input_: Invoice creation parameters.

        Returns:
            The created invoice with QR code and deep links.
        """
        wire_body = _build_invoice_request(self.config, input_)
        wire = await self._request("POST", "/invoice", wire_body)
        return _map_invoice_response(wire)

    async def get_invoice(self, invoice_id: str) -> QPayInvoiceGetResponse:
        """Get invoice details by ID.

        Args:
            invoice_id: The invoice ID.

        Returns:
            Invoice details.
        """
        wire = await self._request("GET", f"/invoice/{quote(invoice_id, safe='')}")
        return _map_invoice_get_response(wire)

    async def cancel_invoice(self, invoice_id: str) -> None:
        """Cancel an invoice by ID.

        Args:
            invoice_id: The invoice ID to cancel.
        """
        await self._request("DELETE", f"/invoice/{quote(invoice_id, safe='')}")

    # -- Payment operations -------------------------------------------------

    async def get_payment(self, payment_id: str) -> QPayPaymentRow:
        """Get payment details by ID.

        Args:
            payment_id: The payment ID.

        Returns:
            Payment details.
        """
        wire = await self._request("GET", f"/payment/get/{quote(payment_id, safe='')}")
        return _map_payment_row(wire)

    async def check_payment(self, options: CheckPaymentOptions) -> QPayPaymentCheckResponse:
        """Check payment status for an invoice.

        Args:
            options: Check payment options including invoice_id and pagination.

        Returns:
            Payment check response with count, paid amount, and payment rows.
        """
        wire_body = _build_check_payment_request(options)
        wire = await self._request("POST", "/payment/check", wire_body)
        return _map_payment_check_response(wire)

    async def cancel_payment(self, options: Optional[CancelPaymentOptions] = None) -> None:
        """Cancel a payment.

        Args:
            options: Cancel payment options.
        """
        wire_body = _build_cancel_payment_request(self.config, options)
        await self._request("DELETE", "/payment/cancel", wire_body)

    async def refund_payment(self, payment_id: str) -> None:
        """Refund a payment by ID.

        Args:
            payment_id: The payment ID to refund.
        """
        await self._request("DELETE", f"/payment/refund/{quote(payment_id, safe='')}")
