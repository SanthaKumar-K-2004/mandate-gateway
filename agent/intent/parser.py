"""
S02.3 — AI Intent Parser & Arithmetic Verification Engine.

Parses raw model/tool payloads into CartItemProposal objects, validates quantities, prices,
and verifies strict line-item subtotal arithmetic.
"""

from __future__ import annotations

import json
from typing import Any, List

from agent.intent.errors import IntentErrorCode, IntentValidationError
from agent.intent.security import PromptInjectionDefense
from apps.api.contracts.transaction import CartItemProposal
from apps.api.domain.types import Currency

MAX_PAYLOAD_BYTES: int = 64 * 1024  # 64 KB
MAX_ITEMS_PER_INTENT: int = 50
MAX_ITEM_QUANTITY: int = 1000
MAX_SINGLE_ITEM_PRICE_PAISE: int = 1_000_000_00  # ₹10,00,000 in paise
MAX_TOTAL_AMOUNT_PAISE: int = 5_000_000_00  # ₹50,00,000 in paise


class AgentIntentParser:
    """
    Parser & Math Verification Engine converting untrusted agent payloads into valid cart proposals.
    """

    @classmethod
    def parse_item(cls, item_data: dict[str, Any], default_merchant_id: str) -> CartItemProposal:
        """
        Parse a single line item dictionary, scan catalog text for poisoning,
        and verify line-item subtotal arithmetic.
        """
        if not isinstance(item_data, dict):
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Line item payload must be a dictionary, got {type(item_data).__name__}.",
            )

        # 1. Scan Catalog Text for Prompt Poisoning
        PromptInjectionDefense.scan_catalog_poisoning(item_data)

        # 2. Extract & Sanitize Identifiers and Names
        raw_pid = item_data.get("product_id") or item_data.get("sku")
        raw_mid = item_data.get("merchant_id") or default_merchant_id
        raw_name = item_data.get("name") or item_data.get("item_name")

        if (
            not raw_pid
            or not str(raw_pid).strip()
            or not raw_mid
            or not str(raw_mid).strip()
            or not raw_name
            or not str(raw_name).strip()
        ):
            raise IntentValidationError(
                IntentErrorCode.MISSING_MANDATORY_FIELD,
                "Line item missing required fields (product_id, merchant_id, or name).",
            )

        pid = str(raw_pid).strip()
        mid = str(raw_mid).strip()
        name = PromptInjectionDefense.sanitize_text(str(raw_name))
        category = PromptInjectionDefense.sanitize_text(str(item_data.get("category") or "general"))

        # 3. Parse & Validate Quantity
        raw_qty = item_data.get("quantity", 1)
        try:
            qty = int(raw_qty)
        except (ValueError, TypeError):
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Invalid quantity value: {raw_qty!r}.",
            )

        if qty <= 0 or qty > MAX_ITEM_QUANTITY:
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Quantity {qty} violates allowed range (1 .. {MAX_ITEM_QUANTITY}).",
            )

        # 4. Parse & Validate Unit Price
        raw_price = (
            item_data.get("unit_price_paise")
            or item_data.get("price_paise")
            or item_data.get("price")
        )
        if raw_price is None:
            raise IntentValidationError(
                IntentErrorCode.MISSING_MANDATORY_FIELD,
                "Line item missing unit_price_paise.",
            )

        try:
            unit_price = int(raw_price)
        except (ValueError, TypeError):
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Invalid unit price value: {raw_price!r}.",
            )

        if unit_price <= 0 or unit_price > MAX_SINGLE_ITEM_PRICE_PAISE:
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Unit price {unit_price} paise violates allowed range (1 .. {MAX_SINGLE_ITEM_PRICE_PAISE}).",
            )

        # 5. Arithmetic Line-Item Subtotal Verification
        expected_subtotal = qty * unit_price
        raw_subtotal = item_data.get("subtotal_paise")

        if raw_subtotal is not None:
            try:
                provided_subtotal = int(raw_subtotal)
            except (ValueError, TypeError):
                raise IntentValidationError(
                    IntentErrorCode.INVALID_LINE_ITEM_MATH,
                    f"Invalid subtotal paise value: {raw_subtotal!r}.",
                )

            if provided_subtotal != expected_subtotal:
                raise IntentValidationError(
                    IntentErrorCode.INVALID_LINE_ITEM_MATH,
                    f"Line-item subtotal mismatch for product {pid!r}: "
                    f"expected {qty} * {unit_price} = {expected_subtotal} paise, got {provided_subtotal} paise.",
                )

        return CartItemProposal(
            product_id=pid,
            merchant_id=mid,
            name=name,
            category=category,
            quantity=qty,
            unit_price_paise=unit_price,
            currency=Currency.INR,
            subtotal_paise=expected_subtotal,
        )

    @classmethod
    def parse_intent_payload(
        cls,
        payload: dict[str, Any],
        default_merchant_id: str = "",
    ) -> List[CartItemProposal]:
        """
        Parse untrusted intent dictionary, validate size, scan authority injection,
        parse items, and verify total cart arithmetic.
        """
        if not isinstance(payload, dict):
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Intent payload must be a dictionary, got {type(payload).__name__}.",
            )

        # 1. Payload Size Check
        try:
            raw_bytes = len(json.dumps(payload).encode("utf-8"))
            if raw_bytes > MAX_PAYLOAD_BYTES:
                raise IntentValidationError(
                    IntentErrorCode.INTENT_SIZE_EXCEEDED,
                    f"Payload size ({raw_bytes} bytes) exceeds limit ({MAX_PAYLOAD_BYTES} bytes).",
                )
        except IntentValidationError:
            raise
        except Exception as e:
            raise IntentValidationError(
                IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                f"Failed to serialize payload to JSON: {e}",
            )

        # 2. Authority Injection Check
        PromptInjectionDefense.scan_authority_injection(payload)

        # 3. Currency Validation
        currency_str = str(payload.get("currency", "INR")).upper()
        if currency_str != "INR":
            raise IntentValidationError(
                IntentErrorCode.UNAUTHORIZED_CURRENCY,
                f"Unauthorized currency {currency_str!r}. Only 'INR' is supported.",
            )

        # 4. Extract Items List
        items_raw = payload.get("items") or payload.get("cart") or payload.get("line_items")
        if not items_raw or not isinstance(items_raw, list):
            # Attempt fallback single-item payload format
            if "product_id" in payload or "price_paise" in payload or "amount_paise" in payload:
                items_raw = [payload]
            else:
                raise IntentValidationError(
                    IntentErrorCode.MISSING_MANDATORY_FIELD,
                    "Intent payload must contain a non-empty 'items' list.",
                )

        if len(items_raw) > MAX_ITEMS_PER_INTENT:
            raise IntentValidationError(
                IntentErrorCode.INTENT_SIZE_EXCEEDED,
                f"Item count ({len(items_raw)}) exceeds limit ({MAX_ITEMS_PER_INTENT}).",
            )

        merchant_id = str(payload.get("merchant_id") or default_merchant_id).strip()

        # 5. Parse Each Line Item & Verify Math
        parsed_items: List[CartItemProposal] = []
        calculated_total_paise = 0

        for idx, raw_item in enumerate(items_raw):
            if isinstance(raw_item, dict):
                parsed = cls.parse_item(raw_item, merchant_id)
                parsed_items.append(parsed)
                calculated_total_paise += parsed.quantity * parsed.unit_price_paise
            else:
                raise IntentValidationError(
                    IntentErrorCode.MALFORMED_INTENT_PAYLOAD,
                    f"Item at index {idx} must be a dictionary, got {type(raw_item).__name__}.",
                )

        # Add optional tax and shipping
        tax_paise = int(payload.get("tax_paise", 0))
        shipping_paise = int(payload.get("shipping_paise", 0))
        calculated_grand_total = calculated_total_paise + tax_paise + shipping_paise

        # Verify against overall payload total if provided
        provided_total = (
            payload.get("total_paise")
            or payload.get("amount_paise")
            or payload.get("total_amount_paise")
        )
        if provided_total is not None:
            try:
                provided_total_int = int(provided_total)
                if (
                    provided_total_int != calculated_grand_total
                    and provided_total_int != calculated_total_paise
                ):
                    raise IntentValidationError(
                        IntentErrorCode.INVALID_LINE_ITEM_MATH,
                        f"Overall cart total mismatch: calculated items subtotal {calculated_grand_total} paise, "
                        f"got payload total {provided_total_int} paise.",
                    )
            except (ValueError, TypeError):
                raise IntentValidationError(
                    IntentErrorCode.INVALID_LINE_ITEM_MATH,
                    f"Invalid payload total_paise value: {provided_total!r}.",
                )

        if calculated_grand_total > MAX_TOTAL_AMOUNT_PAISE:
            raise IntentValidationError(
                IntentErrorCode.INTENT_SIZE_EXCEEDED,
                f"Total cart amount ({calculated_grand_total} paise) exceeds limit ({MAX_TOTAL_AMOUNT_PAISE} paise).",
            )

        return parsed_items
