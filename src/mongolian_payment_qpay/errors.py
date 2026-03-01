"""QPay SDK error types."""

from typing import Any, Optional


class QPayError(Exception):
    """Custom error class for QPay API errors.

    Includes the HTTP status code and raw response body when available.

    Attributes:
        status_code: The HTTP status code, if available.
        response: The raw response body, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response
