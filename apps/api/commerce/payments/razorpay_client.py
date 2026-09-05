"""
S01.12 — First-Class Razorpay Test-Mode Connector Client.

Provides direct, production-grade integration with Razorpay REST API (v1).
Supports order creation, payment fetching, payment capture, HMAC-SHA256 signature
verification for checkouts & webhooks, and deterministic mock mode when credentials
are omitted during dev/testing.
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


from apps.api.config.types import SecretString
from apps.api.commerce.payments.models import (
    PaymentState,
    RazorpayMode,
    RazorpayPaymentDetails,
    RazorpayTestOrder,
)


class RazorpayClientError(Exception):
    """Base exception for Razorpay Client errors with safe redacted messaging."""

    def __init__(
        self, message: str, code: Optional[str] = None, status_code: Optional[int] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class RazorpayClient:
    """
    Razorpay API Client implementing official v1 endpoints.

    Base URL: https://api.razorpay.com/v1
    Mode: Explicit test mode by default (RAZORPAY_MODE=test).
    """

    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(
        self,
        key_id: Optional[SecretString] = None,
        key_secret: Optional[SecretString] = None,
        webhook_secret: Optional[SecretString] = None,
        mode: Optional[RazorpayMode] = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        env_mode_str = os.environ.get("RAZORPAY_MODE", "test").lower()
        self.mode = mode or (RazorpayMode.LIVE if env_mode_str == "live" else RazorpayMode.TEST)

        k_id = key_id if key_id is not None else SecretString(os.environ.get("RAZORPAY_KEY_ID", ""))
        k_sec = (
            key_secret
            if key_secret is not None
            else SecretString(os.environ.get("RAZORPAY_KEY_SECRET", ""))
        )
        wh_sec = (
            webhook_secret
            if webhook_secret is not None
            else SecretString(os.environ.get("RAZORPAY_WEBHOOK_SECRET", ""))
        )

        self._key_id = k_id
        self._key_secret = k_sec
        self._webhook_secret = wh_sec
        self._timeout = timeout_seconds

        # In-memory mock store for mock execution when API keys are not provided
        self._mock_orders: Dict[str, RazorpayTestOrder] = {}
        self._mock_payments: Dict[str, RazorpayPaymentDetails] = {}

    @property
    def is_configured(self) -> bool:
        """Returns True if explicit Razorpay key credentials are provided."""
        return bool(self._key_id.get_secret_value() and self._key_secret.get_secret_value())

    def _get_auth_header(self) -> str:
        creds = f"{self._key_id.get_secret_value()}:{self._key_secret.get_secret_value()}"
        encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"

    def _http_request(
        self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise RazorpayClientError(
                "Razorpay credentials are not configured.", code="UNCONFIGURED"
            )

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._get_auth_header(),
        }

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                res: Dict[str, Any] = json.loads(resp_body)
                return res

        except urllib.error.HTTPError as err:
            body_str = err.read().decode("utf-8") if err.fp else ""
            err_json = {}
            try:
                err_json = json.loads(body_str)
            except Exception:
                pass

            err_info = err_json.get("error", {})
            msg = err_info.get("description", f"HTTP {err.code} error from Razorpay API.")
            code = err_info.get("code", "HTTP_ERROR")
            raise RazorpayClientError(msg, code=code, status_code=err.code)
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            msg = "Connection error while reaching Razorpay API."
            if "timed out" in str(err).lower() or isinstance(err, TimeoutError):
                msg = "Razorpay API request timed out."
            raise RazorpayClientError(msg, code="NETWORK_ERROR")
        except Exception:
            raise RazorpayClientError(
                "Unexpected error communicating with Razorpay.", code="INTERNAL_ERROR"
            )

    # -------------------------------------------------------------------------
    # Order API
    # -------------------------------------------------------------------------
    def create_test_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str = "",
        notes: Optional[Dict[str, Any]] = None,
    ) -> RazorpayTestOrder:
        """
        Creates a Razorpay Test Mode Order.
        `amount_paise` MUST be an integer representing minor units (e.g. 29900 for ₹299).
        """
        if not isinstance(amount_paise, int) or amount_paise <= 0:
            raise RazorpayClientError(
                "Amount must be a positive integer in minor units (paise).", code="INVALID_AMOUNT"
            )

        currency = currency.upper()
        notes = notes or {}

        if self.is_configured:
            payload = {
                "amount": amount_paise,
                "currency": currency,
                "receipt": receipt,
                "notes": notes,
            }
            res = self._http_request("POST", "orders", payload)
            return RazorpayTestOrder(
                order_id=res["id"],
                amount_paise=res["amount"],
                currency=res["currency"],
                receipt=res.get("receipt", receipt),
                status=res.get("status", "created"),
                created_at=res.get("created_at", int(time.time())),
                notes=res.get("notes", notes),
                mode=self.mode,
            )

        # Mock Fallback Path for unconfigured test environments
        order_id = f"order_test_{receipt[:12] if receipt else int(time.time())}"
        mock_order = RazorpayTestOrder(
            order_id=order_id,
            amount_paise=amount_paise,
            currency=currency,
            receipt=receipt,
            status="created",
            created_at=int(time.time()),
            notes=notes,
            mode=RazorpayMode.TEST,
        )
        self._mock_orders[order_id] = mock_order
        return mock_order

    def fetch_order(self, order_id: str) -> RazorpayTestOrder:
        """Fetch order details by order_id."""
        if self.is_configured:
            res = self._http_request("GET", f"orders/{order_id}")
            return RazorpayTestOrder(
                order_id=res["id"],
                amount_paise=res["amount"],
                currency=res["currency"],
                receipt=res.get("receipt", ""),
                status=res.get("status", "created"),
                created_at=res.get("created_at", int(time.time())),
                notes=res.get("notes", {}),
                mode=self.mode,
            )

        if order_id in self._mock_orders:
            return self._mock_orders[order_id]
        raise RazorpayClientError(
            f"Order {order_id} not found.", code="ORDER_NOT_FOUND", status_code=404
        )

    # -------------------------------------------------------------------------
    # Payment API
    # -------------------------------------------------------------------------
    def fetch_payment(self, payment_id: str) -> RazorpayPaymentDetails:
        """Fetch payment details by payment_id."""
        if self.is_configured:
            res = self._http_request("GET", f"payments/{payment_id}")
            return RazorpayPaymentDetails(
                payment_id=res["id"],
                order_id=res.get("order_id", ""),
                amount_paise=res["amount"],
                currency=res["currency"],
                status=res["status"],
                method=res.get("method", "card"),
                email=res.get("email", ""),
                contact=res.get("contact", ""),
                created_at=res.get("created_at", int(time.time())),
                notes=res.get("notes", {}),
                error_code=res.get("error_code"),
                error_description=res.get("error_description"),
            )

        if payment_id in self._mock_payments:
            return self._mock_payments[payment_id]

        if "unknown" in payment_id.lower() or "invalid" in payment_id.lower():
            return RazorpayPaymentDetails(
                payment_id=payment_id,
                order_id=f"order_{payment_id}",
                amount_paise=29900,
                currency="INR",
                status="unknown",
                method="card",
                email="buyer@example.com",
                contact="+919876543210",
                created_at=int(time.time()),
            )

        if "failed" in payment_id.lower():
            return RazorpayPaymentDetails(
                payment_id=payment_id,
                order_id=f"order_{payment_id}",
                amount_paise=29900,
                currency="INR",
                status="failed",
                method="card",
                email="buyer@example.com",
                contact="+919876543210",
                created_at=int(time.time()),
            )

        # Return default mock payment for simulation
        return RazorpayPaymentDetails(
            payment_id=payment_id,
            order_id=f"order_{payment_id}",
            amount_paise=29900,
            currency="INR",
            status="captured",
            method="card",
            email="buyer@example.com",
            contact="+919876543210",
            created_at=int(time.time()),
        )

    def capture_payment(
        self, payment_id: str, amount_paise: int, currency: str = "INR"
    ) -> RazorpayPaymentDetails:
        """Capture an authorized payment."""
        if not isinstance(amount_paise, int) or amount_paise <= 0:
            raise RazorpayClientError(
                "Capture amount must be a positive integer in minor units.", code="INVALID_AMOUNT"
            )

        if self.is_configured:
            payload = {"amount": amount_paise, "currency": currency.upper()}
            res = self._http_request("POST", f"payments/{payment_id}/capture", payload)
            return RazorpayPaymentDetails(
                payment_id=res["id"],
                order_id=res.get("order_id", ""),
                amount_paise=res["amount"],
                currency=res["currency"],
                status=res["status"],
                method=res.get("method", "card"),
                email=res.get("email", ""),
                contact=res.get("contact", ""),
                created_at=res.get("created_at", int(time.time())),
                notes=res.get("notes", {}),
            )

        # Mock capture
        p_details = RazorpayPaymentDetails(
            payment_id=payment_id,
            order_id=f"order_{payment_id}",
            amount_paise=amount_paise,
            currency=currency.upper(),
            status="captured",
            method="card",
            email="buyer@example.com",
            contact="+919876543210",
            created_at=int(time.time()),
        )
        self._mock_payments[payment_id] = p_details
        return p_details

    # -------------------------------------------------------------------------
    # Signature Verification
    # -------------------------------------------------------------------------
    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify checkout payment signature: HMAC-SHA256(order_id + '|' + payment_id, secret).
        """
        if not order_id or not payment_id or not signature:
            return False

        secret = self._key_secret.get_secret_value()
        if not secret:
            # Deterministic mock verification if secret is not set
            return signature.startswith("sig_valid_") or signature == f"mock_sig_{order_id[:8]}"

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(
        self, body: bytes | str, signature: str, secret: Optional[str] = None
    ) -> bool:
        """
        Verify Razorpay webhook signature: HMAC-SHA256(body, webhook_secret).
        """
        if not signature:
            return False

        sec = (
            secret or self._webhook_secret.get_secret_value() or self._key_secret.get_secret_value()
        )
        if not sec:
            # Mock verification when secret not set
            return signature.startswith("whsig_valid_") or signature == "mock_webhook_signature"

        body_bytes = body.encode("utf-8") if isinstance(body, str) else body
        expected = hmac.new(sec.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    # -------------------------------------------------------------------------
    # Status Mapping
    # -------------------------------------------------------------------------
    def get_payment_status(self, payment_id: str) -> PaymentState:
        """Fetch payment status and return provider-neutral PaymentState enum."""
        try:
            p = self.fetch_payment(payment_id)
            return PaymentState.from_razorpay_status(p.status)
        except Exception:
            return PaymentState.UNKNOWN

    def get_order_status(self, order_id: str) -> PaymentState:
        """Fetch order status and return provider-neutral PaymentState enum."""
        try:
            o = self.fetch_order(order_id)
            return PaymentState.from_razorpay_status(o.status)
        except Exception:
            return PaymentState.UNKNOWN
