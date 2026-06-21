# mongolian-payment-qpay

QPay payment gateway SDK for Python (sync + async) — create invoices, check payments, manage refunds.

[![PyPI version](https://img.shields.io/pypi/v/mongolian-payment-qpay.svg)](https://pypi.org/project/mongolian-payment-qpay/)
[![Python versions](https://img.shields.io/pypi/pyversions/mongolian-payment-qpay.svg)](https://pypi.org/project/mongolian-payment-qpay/)
[![license](https://img.shields.io/pypi/l/mongolian-payment-qpay.svg)](./LICENSE)

> Part of the **[mongolian-payment](https://github.com/mongolian-payment)** SDK suite.
> Also available for Node.js: **[@mongolian-payment/qpay](https://www.npmjs.com/package/@mongolian-payment/qpay)** ([source](https://github.com/mongolian-payment/qpay-js)).

## Requirements

- Python >= 3.8 (depends on `httpx`)

## Installation

```bash
pip install mongolian-payment-qpay
```

## Quick Start

```python
from mongolian_payment_qpay import QPayClient, QPayConfig, CreateInvoiceInput

client = QPayClient(QPayConfig(
    username="MY_USERNAME",
    password="MY_PASSWORD",
    endpoint="https://merchant.qpay.mn/v2",
    callback="https://example.com/callback",
    invoice_code="MY_INVOICE_CODE",
    merchant_id="MY_MERCHANT_ID",
))

# Create an invoice
invoice = client.create_invoice(CreateInvoiceInput(
    sender_code="SENDER",
    sender_branch_code="BRANCH",
    receiver_code="RECEIVER",
    description="Test payment",
    amount=1000,
))
print(invoice.invoice_id, invoice.qr_text, invoice.qpay_short_url)

# Check payment status
from mongolian_payment_qpay import CheckPaymentOptions

result = client.check_payment(CheckPaymentOptions(invoice_id=invoice.invoice_id))
print(f"Paid: {result.paid_amount}, Count: {result.count}")
```

### Async

```python
import asyncio
from mongolian_payment_qpay import AsyncQPayClient, QPayConfig, CreateInvoiceInput

async def main():
    async with AsyncQPayClient(QPayConfig(
        username="MY_USERNAME",
        password="MY_PASSWORD",
        endpoint="https://merchant.qpay.mn/v2",
        callback="https://example.com/callback",
        invoice_code="MY_INVOICE_CODE",
        merchant_id="MY_MERCHANT_ID",
    )) as client:
        invoice = await client.create_invoice(CreateInvoiceInput(
            sender_code="SENDER",
            sender_branch_code="BRANCH",
            receiver_code="RECEIVER",
            description="Test payment",
            amount=1000,
        ))
        print(invoice.invoice_id)

asyncio.run(main())
```

## Configuration from Environment Variables

```python
from mongolian_payment_qpay import QPayClient, load_config_from_env

client = QPayClient(load_config_from_env())
```

| Variable            | Description                       |
| ------------------- | --------------------------------- |
| `QPAY_USERNAME`     | QPay API username                 |
| `QPAY_PASSWORD`     | QPay API password                 |
| `QPAY_ENDPOINT`     | API base URL                      |
| `QPAY_CALLBACK`     | Payment notification callback URL |
| `QPAY_INVOICE_CODE` | Invoice code assigned by QPay     |
| `QPAY_MERCHANT_ID`  | Merchant ID assigned by QPay      |

> Never hard-code credentials — load them from the environment or a secrets vault.

## API Reference

`QPayClient` and `AsyncQPayClient` share identical method signatures (the async
client uses `async`/`await`). Authentication is automatic.

| Method | Description |
|--------|-------------|
| `create_invoice(input_)` | Create a new invoice |
| `get_invoice(invoice_id)` | Get invoice details by ID |
| `cancel_invoice(invoice_id)` | Cancel an invoice by ID |
| `check_payment(options)` | Check payment status for an invoice |
| `get_payment(payment_id)` | Get payment details by ID |
| `cancel_payment(options)` | Cancel a payment |
| `refund_payment(payment_id)` | Refund a payment by ID |

## Error Handling

All API errors raise `QPayError`, which includes the HTTP status code and response body:

```python
from mongolian_payment_qpay import QPayError

try:
    client.get_invoice("invalid_id")
except QPayError as err:
    print(err)              # Human-readable message
    print(err.status_code)  # HTTP status code (e.g. 404)
    print(err.response)     # Raw response body
```

## License

MIT
