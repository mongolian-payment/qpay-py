"""Tests for QPayClient and AsyncQPayClient."""

import time
from unittest.mock import MagicMock, patch, AsyncMock

import httpx
import pytest

from mongolian_payment_qpay import (
    AsyncQPayClient,
    CheckPaymentOptions,
    CreateInvoiceInput,
    QPayClient,
    QPayConfig,
    QPayError,
    QPayInvoiceResponse,
    QPayPaymentCheckResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CONFIG = QPayConfig(
    username="test_user",
    password="test_pass",
    endpoint="https://merchant.qpay.mn/v2",
    callback="https://example.com/callback",
    invoice_code="TEST_INVOICE_CODE",
    merchant_id="TEST_MERCHANT_ID",
)

LOGIN_RESPONSE = {
    "token_type": "Bearer",
    "access_token": "access_tok",
    "refresh_token": "refresh_tok",
    "expires_in": 3600,
    "refresh_expires_in": 7200,
    "scope": "profile",
    "not-before-policy": "0",
    "session_state": "abc123",
}

INVOICE_WIRE_RESPONSE = {
    "invoice_id": "inv_123",
    "qPay_shortUrl": "https://qpay.mn/i/inv123",
    "qr_text": "qr-text-data",
    "qr_image": "base64-qr-image",
    "urls": [
        {
            "name": "Khan Bank",
            "description": "Khan Bank payment",
            "logo": "https://qpay.mn/logo/khan.png",
            "link": "khanbank://payment?id=inv_123",
        }
    ],
}

PAYMENT_CHECK_WIRE_RESPONSE = {
    "count": 1,
    "paid_amount": 1000,
    "rows": [
        {
            "payment_id": "pay_456",
            "payment_status": "PAID",
            "payment_date": "2025-01-15T12:00:00",
            "payment_fee": "0",
            "payment_amount": "1000",
            "payment_currency": "MNT",
            "payemnt_wallet": "Khan Bank",
            "transaction_type": "P2P",
        }
    ],
}


def _make_response(
    status_code: int = 200,
    json_data: dict = None,
    text: str = "",
    content_type: str = "application/json",
) -> httpx.Response:
    """Build a fake httpx.Response."""
    if json_data is not None:
        import json as _json

        content = _json.dumps(json_data).encode()
    else:
        content = text.encode()

    return httpx.Response(
        status_code=status_code,
        headers={"content-type": content_type},
        content=content,
        request=httpx.Request("GET", "https://fake"),
    )


# ---------------------------------------------------------------------------
# Sync Client Tests
# ---------------------------------------------------------------------------


class TestQPayClientCreateInvoice:
    """Test QPayClient.create_invoice."""

    def test_create_invoice_success(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        invoice_resp = _make_response(json_data=INVOICE_WIRE_RESPONSE)

        with patch.object(client._client, "post", return_value=login_resp) as mock_post, \
             patch.object(client._client, "request", return_value=invoice_resp) as mock_request:

            result = client.create_invoice(
                CreateInvoiceInput(
                    sender_code="SENDER",
                    sender_branch_code="BRANCH",
                    receiver_code="RECEIVER",
                    description="Test payment",
                    amount=1000,
                )
            )

        assert isinstance(result, QPayInvoiceResponse)
        assert result.invoice_id == "inv_123"
        assert result.qpay_short_url == "https://qpay.mn/i/inv123"
        assert result.qr_text == "qr-text-data"
        assert result.qr_image == "base64-qr-image"
        assert len(result.urls) == 1
        assert result.urls[0].name == "Khan Bank"

    def test_create_invoice_with_callback_params(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        invoice_resp = _make_response(json_data=INVOICE_WIRE_RESPONSE)

        with patch.object(client._client, "post", return_value=login_resp), \
             patch.object(client._client, "request", return_value=invoice_resp) as mock_request:

            client.create_invoice(
                CreateInvoiceInput(
                    sender_code="SENDER",
                    sender_branch_code="BRANCH",
                    receiver_code="RECEIVER",
                    description="Test",
                    amount=500,
                    callback_param={"order_id": "12345"},
                )
            )

        # Verify the callback_url in the request body includes the param
        call_kwargs = mock_request.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "order_id=12345" in body["callback_url"]


class TestQPayClientCheckPayment:
    """Test QPayClient.check_payment."""

    def test_check_payment_success(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        check_resp = _make_response(json_data=PAYMENT_CHECK_WIRE_RESPONSE)

        with patch.object(client._client, "post", return_value=login_resp), \
             patch.object(client._client, "request", return_value=check_resp):

            result = client.check_payment(
                CheckPaymentOptions(invoice_id="inv_123")
            )

        assert isinstance(result, QPayPaymentCheckResponse)
        assert result.count == 1
        assert result.paid_amount == 1000
        assert len(result.rows) == 1
        assert result.rows[0].payment_id == "pay_456"
        assert result.rows[0].payment_status == "PAID"
        assert result.rows[0].payment_wallet == "Khan Bank"


class TestQPayClientAuth:
    """Test auth token refresh logic."""

    def test_reuses_valid_token(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        invoice_resp = _make_response(json_data=INVOICE_WIRE_RESPONSE)

        with patch.object(client._client, "post", return_value=login_resp) as mock_post, \
             patch.object(client._client, "request", return_value=invoice_resp):

            input_ = CreateInvoiceInput(
                sender_code="S", sender_branch_code="B",
                receiver_code="R", description="D", amount=1,
            )
            client.create_invoice(input_)
            client.create_invoice(input_)

        # login should only be called once -- the second call reuses the token
        assert mock_post.call_count == 1

    def test_refreshes_expired_access_token(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        refresh_resp = _make_response(json_data={
            **LOGIN_RESPONSE,
            "access_token": "refreshed_tok",
        })
        invoice_resp = _make_response(json_data=INVOICE_WIRE_RESPONSE)

        input_ = CreateInvoiceInput(
            sender_code="S", sender_branch_code="B",
            receiver_code="R", description="D", amount=1,
        )

        with patch.object(client._client, "post", return_value=login_resp) as mock_post, \
             patch.object(client._client, "request", return_value=invoice_resp):

            # First call -- triggers login
            client.create_invoice(input_)
            assert mock_post.call_count == 1

            # Expire the access token but keep refresh valid
            client._token_expires_at = time.time() - 1

            # Switch mock to return refresh response
            mock_post.return_value = refresh_resp

            # Second call -- should refresh, not login
            client.create_invoice(input_)
            assert mock_post.call_count == 2

            # Verify the refresh endpoint was called
            last_call_url = mock_post.call_args[0][0]
            assert "/auth/refresh" in last_call_url

    def test_full_relogin_when_both_expired(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        invoice_resp = _make_response(json_data=INVOICE_WIRE_RESPONSE)

        input_ = CreateInvoiceInput(
            sender_code="S", sender_branch_code="B",
            receiver_code="R", description="D", amount=1,
        )

        with patch.object(client._client, "post", return_value=login_resp) as mock_post, \
             patch.object(client._client, "request", return_value=invoice_resp):

            client.create_invoice(input_)

            # Expire both tokens
            client._token_expires_at = time.time() - 1
            client._refresh_expires_at = time.time() - 1

            client.create_invoice(input_)
            assert mock_post.call_count == 2

            # Verify the login endpoint was called (not refresh)
            last_call_url = mock_post.call_args[0][0]
            assert "/auth/token" in last_call_url


class TestQPayClientErrors:
    """Test error handling."""

    def test_login_failure_raises_qpay_error(self):
        client = QPayClient(FAKE_CONFIG)

        error_resp = _make_response(
            status_code=401,
            json_data={"error": "unauthorized"},
        )

        with patch.object(client._client, "post", return_value=error_resp):
            with pytest.raises(QPayError) as exc_info:
                client.create_invoice(
                    CreateInvoiceInput(
                        sender_code="S", sender_branch_code="B",
                        receiver_code="R", description="D", amount=1,
                    )
                )

        assert exc_info.value.status_code == 401
        assert "login failed" in str(exc_info.value)

    def test_api_error_raises_qpay_error(self):
        client = QPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        error_resp = _make_response(
            status_code=400,
            json_data={"error": "bad request"},
        )

        with patch.object(client._client, "post", return_value=login_resp), \
             patch.object(client._client, "request", return_value=error_resp):
            with pytest.raises(QPayError) as exc_info:
                client.create_invoice(
                    CreateInvoiceInput(
                        sender_code="S", sender_branch_code="B",
                        receiver_code="R", description="D", amount=1,
                    )
                )

        assert exc_info.value.status_code == 400
        assert "QPay API error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Async Client Tests
# ---------------------------------------------------------------------------


class TestAsyncQPayClientCreateInvoice:
    """Test AsyncQPayClient.create_invoice."""

    async def test_create_invoice_success(self):
        client = AsyncQPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        invoice_resp = _make_response(json_data=INVOICE_WIRE_RESPONSE)

        with patch.object(client._client, "post", return_value=login_resp) as mock_post, \
             patch.object(client._client, "request", return_value=invoice_resp):

            # Make the mocks awaitable
            mock_post.return_value = login_resp
            mock_post.side_effect = None

            # For async client, we need to use AsyncMock
            original_post = client._client.post
            original_request = client._client.request

            async def mock_async_post(*args, **kwargs):
                return login_resp

            async def mock_async_request(*args, **kwargs):
                return invoice_resp

            with patch.object(client._client, "post", side_effect=mock_async_post), \
                 patch.object(client._client, "request", side_effect=mock_async_request):

                result = await client.create_invoice(
                    CreateInvoiceInput(
                        sender_code="SENDER",
                        sender_branch_code="BRANCH",
                        receiver_code="RECEIVER",
                        description="Test payment",
                        amount=1000,
                    )
                )

        assert isinstance(result, QPayInvoiceResponse)
        assert result.invoice_id == "inv_123"
        assert result.qpay_short_url == "https://qpay.mn/i/inv123"
        assert len(result.urls) == 1


class TestAsyncQPayClientCheckPayment:
    """Test AsyncQPayClient.check_payment."""

    async def test_check_payment_success(self):
        client = AsyncQPayClient(FAKE_CONFIG)

        login_resp = _make_response(json_data=LOGIN_RESPONSE)
        check_resp = _make_response(json_data=PAYMENT_CHECK_WIRE_RESPONSE)

        async def mock_async_post(*args, **kwargs):
            return login_resp

        async def mock_async_request(*args, **kwargs):
            return check_resp

        with patch.object(client._client, "post", side_effect=mock_async_post), \
             patch.object(client._client, "request", side_effect=mock_async_request):

            result = await client.check_payment(
                CheckPaymentOptions(invoice_id="inv_123")
            )

        assert isinstance(result, QPayPaymentCheckResponse)
        assert result.count == 1
        assert result.paid_amount == 1000
        assert result.rows[0].payment_id == "pay_456"
