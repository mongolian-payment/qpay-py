"""QPay SDK configuration loading from environment variables."""

import os
from typing import Dict, List

from .types import QPayConfig


def load_config_from_env() -> QPayConfig:
    """Load QPay configuration from environment variables.

    Expected environment variables:
        - ``QPAY_USERNAME`` -- QPay API username
        - ``QPAY_PASSWORD`` -- QPay API password
        - ``QPAY_ENDPOINT`` -- QPay API base URL (e.g. https://merchant.qpay.mn/v2)
        - ``QPAY_CALLBACK`` -- Callback URL for payment notifications
        - ``QPAY_INVOICE_CODE`` -- Invoice code assigned by QPay
        - ``QPAY_MERCHANT_ID`` -- Merchant ID assigned by QPay

    Returns:
        A populated :class:`QPayConfig` instance.

    Raises:
        ValueError: If any required environment variable is missing.
    """
    required: Dict[str, str] = {
        "username": "QPAY_USERNAME",
        "password": "QPAY_PASSWORD",
        "endpoint": "QPAY_ENDPOINT",
        "callback": "QPAY_CALLBACK",
        "invoice_code": "QPAY_INVOICE_CODE",
        "merchant_id": "QPAY_MERCHANT_ID",
    }

    config: Dict[str, str] = {}
    missing: List[str] = []

    for key, env_var in required.items():
        value = os.environ.get(env_var)
        if not value:
            missing.append(env_var)
        else:
            config[key] = value

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return QPayConfig(**config)
