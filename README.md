# mongolian-payment-qpay

QPay payment gateway SDK for Python. Supports both synchronous and asynchronous usage.

This is a Python port of the [QPay JS SDK](https://github.com/mongolian-payment/qpay-js).

## Installation

```bash
pip install mongolian-payment-qpay
```

## Usage

### Sync Client

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

print(invoice.invoice_id)
print(invoice.qr_text)
print(invoice.qpay_short_url)

# Check payment status
from mongolian_payment_qpay import CheckPaymentOptions

result = client.check_payment(CheckPaymentOptions(invoice_id=invoice.invoice_id))
print(f"Paid: {result.paid_amount}, Count: {result.count}")
for row in result.rows:
    print(f"  {row.payment_id}: {row.payment_status}")

# Get invoice details
details = client.get_invoice(invoice.invoice_id)

# Cancel an invoice
client.cancel_invoice(invoice.invoice_id)

# Refund a payment
client.refund_payment("payment_id")
```

### Async Client

```python
import asyncio
from mongolian_payment_qpay import AsyncQPayClient, QPayConfig, CreateInvoiceInput

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

    print(invoice.invoice_id)

asyncio.run(main())
```

### Loading Config from Environment Variables

Set the following environment variables:

| Variable | Description |
|---|---|
| `QPAY_USERNAME` | QPay API username |
| `QPAY_PASSWORD` | QPay API password |
| `QPAY_ENDPOINT` | QPay API base URL (e.g. `https://merchant.qpay.mn/v2`) |
| `QPAY_CALLBACK` | Callback URL for payment notifications |
| `QPAY_INVOICE_CODE` | Invoice code assigned by QPay |
| `QPAY_MERCHANT_ID` | Merchant ID assigned by QPay |

Then load the config:

```python
from mongolian_payment_qpay import QPayClient, load_config_from_env

config = load_config_from_env()
client = QPayClient(config)
```

## API Reference

### QPayClient / AsyncQPayClient

Both clients have identical method signatures. The async client uses `async/await`.

| Method | Description |
|---|---|
| `create_invoice(input_)` | Create a new invoice |
| `get_invoice(invoice_id)` | Get invoice details by ID |
| `cancel_invoice(invoice_id)` | Cancel an invoice by ID |
| `get_payment(payment_id)` | Get payment details by ID |
| `check_payment(options)` | Check payment status for an invoice |
| `cancel_payment(options)` | Cancel a payment |
| `refund_payment(payment_id)` | Refund a payment by ID |

## License

MIT
