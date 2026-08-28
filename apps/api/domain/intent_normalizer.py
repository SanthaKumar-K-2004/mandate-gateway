"""
S01.2 — Commerce Intent Normalization Engine.

Converts untrusted AI/agent commerce proposals into validated, deterministic,
canonical CommerceIntent payloads for downstream gateway evaluation.

Trust Model:
  AI / Agent proposals are UNTRUSTED.
  AI may propose items, merchant_id, quantities, desired purchase, operation, prompt.
  AI MUST NOT grant itself authorization, policy approval, mandate approval,
  budget approval, step-up bypass, or execution permission.

Security Limits:
  - Max raw payload size: 64 KB
  - Max prompt length: 5,000 chars
  - Max identifier length: 255 chars
  - Max line items per cart: 50 items
  - Max single item quantity: 1,000 units
  - Max single item price: 1,000,000,00 paise (₹10,00,000)
  - Max total cart price: 5,000,000,00 paise (₹50,00,000)

Pure Python — zero I/O, zero network calls, zero external side-effects.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.cart import Cart, CartItem
from apps.api.domain.cart_integrity import build_cart_with_hash
from apps.api.domain.intent import CommerceIntent
from apps.api.domain.types import Currency, McpOperation, Region

# ---------------------------------------------------------------------------
# Security & Boundary Constants
# ---------------------------------------------------------------------------

MAX_PAYLOAD_BYTES: int = 64 * 1024  # 64 KB
MAX_RAW_PROMPT_LENGTH: int = 5000
MAX_IDENTIFIER_LENGTH: int = 255
MAX_ITEMS_PER_INTENT: int = 50
MAX_ITEM_QUANTITY: int = 1000
MAX_SINGLE_ITEM_PRICE_PAISE: int = 1_000_000_00  # ₹10,00,000 in paise
MAX_TOTAL_AMOUNT_PAISE: int = 5_000_000_00  # ₹50,00,000 in paise

# Safe identifier character pattern: alphanumeric, hyphen, underscore, colon, dot
IDENTIFIER_REGEX: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_\-\.:]+$")

# Authority claims explicitly forbidden from AI inputs
FORBIDDEN_AUTHORITY_KEYS: set[str] = {
    "authorized",
    "approved",
    "policy_passed",
    "mandate_valid",
    "budget_approved",
    "budget_ok",
    "skip_step_up",
    "skip_policy",
    "override_policy",
    "override_merchant",
    "payment_confirmed",
    "execution_allowed",
    "admin",
    "is_trusted",
    "system",
    "role",
    "security_approved",
}


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Structured Domain Errors
# ---------------------------------------------------------------------------


class IntentNormalizationError(ValueError):
    """Base domain error for intent normalization failures."""

    def __init__(self, message: str, code: str = "INTENT_NORMALIZATION_FAILED") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class IntentStructuralError(IntentNormalizationError):
    """Raised when proposal payload structure is invalid or exceeds bounds."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTENT_STRUCTURAL_INVALID")


class IntentIdentityError(IntentNormalizationError):
    """Raised when identifier format or consistency fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTENT_IDENTITY_INVALID")


class IntentMonetaryError(IntentNormalizationError):
    """Raised when monetary amounts, prices, or currencies are invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTENT_MONETARY_INVALID")


class IntentAmbiguityError(IntentNormalizationError):
    """Raised when proposal contains conflicting or ambiguous data."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTENT_AMBIGUOUS")


class IntentSecurityViolationError(IntentNormalizationError):
    """Raised when proposal attempts unauthorized security overrides or injections."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTENT_SECURITY_VIOLATION")


# ---------------------------------------------------------------------------
# Untrusted Raw DTO (Boundary Representation)
# ---------------------------------------------------------------------------


class UntrustedItemProposal(BaseModel):
    """Raw item proposal input from AI agent."""

    model_config = {"extra": "forbid"}

    product_id: str
    merchant_id: str | None = None
    name: str
    category: str
    quantity: int | float | str
    unit_price_paise: int | float | str
    currency: str | None = None


class UntrustedProposalPayload(BaseModel):
    """
    Boundary DTO representing an untrusted AI proposal.

    Forbids extra unknown authority fields.
    """

    model_config = {"extra": "forbid"}

    buyer_id: str
    merchant_id: str
    mandate_id: str
    raw_prompt: str
    items: list[UntrustedItemProposal]
    operation: str = "create_order"
    currency: str = "INR"
    region: str = "IN"
    tax_paise: int | float | str = 0
    shipping_paise: int | float | str = 0
    total_paise: int | float | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Output DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NormalizedCommerceProposal:
    """
    Canonical output of S01.2 Intent Normalization.

    Contains validated CommerceIntent and canonical Cart snapshot ready
    for downstream S01.3 Merchant Policy evaluation.
    """

    intent: CommerceIntent
    cart: Cart
    normalized_at: datetime = field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Engine Implementation
# ---------------------------------------------------------------------------


class IntentNormalizer:
    """
    Deterministic Commerce Intent Normalizer.

    Transforms untrusted AI proposal dicts/strings into a canonical CommerceIntent.
    No I/O, no network, 100% pure deterministic pipeline.
    """

    @classmethod
    def normalize(
        cls,
        raw_input: dict[str, Any] | str | UntrustedProposalPayload,
    ) -> NormalizedCommerceProposal:
        """
        Execute the 9-stage normalization pipeline on raw_input.

        Raises:
            IntentNormalizationError (or subclasses) if validation fails.
        """
        # --------------------------------------------------------------
        # Stage 1: Structural & Authority Rejection Check
        # --------------------------------------------------------------
        raw_dict = cls._parse_and_validate_structure(raw_input)
        cls._scan_for_authority_injections(raw_dict)

        # --------------------------------------------------------------
        # Stage 2: Buyer, Merchant & Mandate Identity Validation
        # --------------------------------------------------------------
        buyer_id = cls._validate_identifier(raw_dict.get("buyer_id"), field_name="buyer_id")
        merchant_id = cls._validate_identifier(
            raw_dict.get("merchant_id"), field_name="merchant_id"
        )
        mandate_id = cls._validate_identifier(raw_dict.get("mandate_id"), field_name="mandate_id")

        # Prompt string sanitization (treated strictly as inert data)
        raw_prompt = cls._sanitize_prompt(raw_dict.get("raw_prompt"))

        # --------------------------------------------------------------
        # Stage 3: Currency & Region Validation
        # --------------------------------------------------------------
        currency_str = raw_dict.get("currency", "INR")
        currency = cls._validate_currency(currency_str)

        region_str = raw_dict.get("region", "IN")
        region = cls._validate_region(region_str)

        # --------------------------------------------------------------
        # Stage 4: Operation Validation
        # --------------------------------------------------------------
        operation = cls._validate_operation(raw_dict.get("operation", "create_order"))

        # --------------------------------------------------------------
        # Stage 5: Items & Cart Validation
        # --------------------------------------------------------------
        raw_items = raw_dict.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise IntentStructuralError("Proposal must contain at least one line item.")
        if len(raw_items) > MAX_ITEMS_PER_INTENT:
            raise IntentStructuralError(
                f"Line item count ({len(raw_items)}) exceeds maximum limit of {MAX_ITEMS_PER_INTENT}."
            )

        validated_items: list[CartItem] = []
        for idx, raw_item in enumerate(raw_items):
            item = cls._validate_item(
                raw_item, index=idx, parent_merchant_id=merchant_id, parent_currency=currency
            )
            validated_items.append(item)

        # Sort items deterministically by product_id
        validated_items.sort(key=lambda i: i.product_id)

        # --------------------------------------------------------------
        # Stage 6: Monetary Totals & Calculation Checks
        # --------------------------------------------------------------
        tax_paise = cls._validate_integer_amount(
            raw_dict.get("tax_paise", 0), field_name="tax_paise"
        )
        shipping_paise = cls._validate_integer_amount(
            raw_dict.get("shipping_paise", 0), field_name="shipping_paise"
        )

        items_subtotal = sum(item.subtotal_paise() for item in validated_items)
        computed_total = items_subtotal + tax_paise + shipping_paise

        if computed_total > MAX_TOTAL_AMOUNT_PAISE:
            raise IntentMonetaryError(
                f"Computed total amount ({computed_total} paise) exceeds maximum allowed limit "
                f"of {MAX_TOTAL_AMOUNT_PAISE} paise (₹{MAX_TOTAL_AMOUNT_PAISE / 100:,.2f})."
            )

        declared_total = raw_dict.get("total_paise")
        if declared_total is not None:
            declared_val = cls._validate_integer_amount(declared_total, field_name="total_paise")
            if declared_val != computed_total:
                raise IntentAmbiguityError(
                    f"Declared total_paise ({declared_val}) does not match computed total "
                    f"({computed_total} paise = items {items_subtotal} + tax {tax_paise} + shipping {shipping_paise})."
                )

        # --------------------------------------------------------------
        # Stage 7: Canonical Cart Construction
        # --------------------------------------------------------------
        canonical_cart = build_cart_with_hash(
            merchant_id=merchant_id,
            mandate_id=mandate_id,
            currency=currency,
            items=tuple(validated_items),
            tax_paise=tax_paise,
            shipping_paise=shipping_paise,
            total_paise=computed_total,
        )

        # --------------------------------------------------------------
        # Stage 8: Metadata Sanitization
        # --------------------------------------------------------------
        raw_meta = raw_dict.get("metadata", {})
        clean_metadata = cls._sanitize_metadata(raw_meta)
        clean_metadata["operation"] = operation.value

        # --------------------------------------------------------------
        # Stage 9: Canonical CommerceIntent Construction
        # --------------------------------------------------------------
        target_category = (
            validated_items[0].category if len(validated_items) == 1 else "multi-category"
        )

        canonical_intent = CommerceIntent(
            buyer_id=buyer_id,
            raw_prompt=raw_prompt,
            target_category=target_category,
            target_merchant_id=merchant_id,
            max_budget_paise=computed_total,
            currency=currency,
            region=region,
            metadata=clean_metadata,
        )

        return NormalizedCommerceProposal(
            intent=canonical_intent,
            cart=canonical_cart,
        )

    # ------------------------------------------------------------------
    # Helper Pipeline Methods
    # ------------------------------------------------------------------

    @classmethod
    def _parse_and_validate_structure(
        cls, raw_input: dict[str, Any] | str | UntrustedProposalPayload
    ) -> dict[str, Any]:
        """Convert input to raw dictionary and check payload size bounds."""
        if isinstance(raw_input, UntrustedProposalPayload):
            return raw_input.model_dump()

        if isinstance(raw_input, str):
            if len(raw_input.encode("utf-8")) > MAX_PAYLOAD_BYTES:
                raise IntentStructuralError(
                    f"Payload size exceeds maximum allowed limit of {MAX_PAYLOAD_BYTES} bytes."
                )
            try:
                parsed = json.loads(raw_input)
            except Exception as ex:
                raise IntentStructuralError(f"Malformed JSON payload: {ex}") from ex
            if not isinstance(parsed, dict):
                raise IntentStructuralError("JSON payload must be an object.")
            return parsed

        if isinstance(raw_input, dict):
            # Check string representation size
            try:
                serialized = json.dumps(raw_input)
                if len(serialized.encode("utf-8")) > MAX_PAYLOAD_BYTES:
                    raise IntentStructuralError(
                        f"Payload size exceeds maximum allowed limit of {MAX_PAYLOAD_BYTES} bytes."
                    )
            except TypeError as ex:
                raise IntentStructuralError(
                    f"Payload dictionary contains non-serializable objects: {ex}"
                ) from ex
            return raw_input

        raise IntentStructuralError(
            f"Unsupported proposal payload type: {type(raw_input).__name__}."
        )

    @classmethod
    def _scan_for_authority_injections(cls, data: dict[str, Any], path: str = "") -> None:
        """Scan recursive payload dict keys for forbidden authority claims."""
        for k, v in data.items():
            if k == "metadata":
                continue  # metadata is sanitized separately via _sanitize_metadata
            key_clean = str(k).strip().lower()
            current_path = f"{path}.{k}" if path else str(k)
            if key_clean in FORBIDDEN_AUTHORITY_KEYS:
                raise IntentSecurityViolationError(
                    f"Proposal contains unauthorized authority claim key '{k}' at path '{current_path}'."
                )
            if isinstance(v, dict):
                cls._scan_for_authority_injections(v, path=current_path)
            elif isinstance(v, list):
                for idx, elem in enumerate(v):
                    if isinstance(elem, dict):
                        cls._scan_for_authority_injections(elem, path=f"{current_path}[{idx}]")

    @classmethod
    def _validate_identifier(cls, value: Any, *, field_name: str) -> str:
        """Validate string identifier bounds and character safety."""
        if value is None or not isinstance(value, str):
            raise IntentIdentityError(f"Field '{field_name}' must be a non-empty string.")
        val_clean = value.strip()
        if not val_clean:
            raise IntentIdentityError(f"Field '{field_name}' cannot be empty or whitespace.")
        if len(val_clean) > MAX_IDENTIFIER_LENGTH:
            raise IntentIdentityError(
                f"Field '{field_name}' length ({len(val_clean)}) "
                f"exceeds maximum allowed limit of {MAX_IDENTIFIER_LENGTH}."
            )
        if not IDENTIFIER_REGEX.match(val_clean):
            raise IntentIdentityError(
                f"Field '{field_name}' contains unsafe characters. Allowed pattern: [a-zA-Z0-9_\\-\\.:]."
            )
        return val_clean

    @classmethod
    def _sanitize_prompt(cls, prompt: Any) -> str:
        """Sanitize raw prompt string. Treats natural language as inert data."""
        if prompt is None or not isinstance(prompt, str):
            raise IntentStructuralError("Field 'raw_prompt' must be a non-empty string.")
        clean = prompt.strip()
        if not clean:
            raise IntentStructuralError("Field 'raw_prompt' cannot be empty.")
        if len(clean) > MAX_RAW_PROMPT_LENGTH:
            raise IntentStructuralError(
                f"Field 'raw_prompt' length ({len(clean)}) exceeds maximum allowed limit of {MAX_RAW_PROMPT_LENGTH}."
            )
        return clean

    @classmethod
    def _validate_currency(cls, val: Any) -> Currency:
        """Validate and return explicit Currency enum."""
        if not isinstance(val, str) or not val.strip():
            raise IntentMonetaryError("Currency must be an explicit ISO string (e.g., 'INR').")
        try:
            return Currency(val.strip().upper())
        except ValueError:
            supported = ", ".join(c.value for c in Currency)
            raise IntentMonetaryError(
                f"Unsupported currency '{val}'. Supported currencies: {supported}."
            )

    @classmethod
    def _validate_region(cls, val: Any) -> Region:
        """Validate and return Region enum."""
        if not isinstance(val, str) or not val.strip():
            raise IntentStructuralError("Region must be a non-empty string (e.g., 'IN').")
        try:
            return Region(val.strip().upper())
        except ValueError:
            supported = ", ".join(r.value for r in Region)
            raise IntentStructuralError(
                f"Unsupported region '{val}'. Supported regions: {supported}."
            )

    @classmethod
    def _validate_operation(cls, val: Any) -> McpOperation:
        """Validate and return controlled McpOperation enum."""
        if not isinstance(val, str) or not val.strip():
            raise IntentStructuralError("Operation must be a non-empty string.")
        val_clean = val.strip().lower()
        for op in McpOperation:
            if op.value == val_clean:
                return op
        supported = ", ".join(o.value for o in McpOperation)
        raise IntentStructuralError(
            f"Unsupported MCP operation '{val}'. Allowed operations: {supported}."
        )

    @classmethod
    def _validate_integer_amount(cls, val: Any, *, field_name: str) -> int:
        """
        Validate integer monetary amount in paise.

        Rejects floats, NaN, infinity, negative values, and non-integer strings.
        """
        if isinstance(val, float):
            raise IntentMonetaryError(
                f"Field '{field_name}' must be an exact integer paise amount, "
                "floats are forbidden to prevent rounding errors."
            )
        if isinstance(val, str):
            val_clean = val.strip()
            if not val_clean.isdigit():
                raise IntentMonetaryError(
                    f"Field '{field_name}' contains non-integer value '{val}'."
                )
            int_val = int(val_clean)
        elif isinstance(val, int) and not isinstance(val, bool):
            int_val = val
        else:
            raise IntentMonetaryError(f"Field '{field_name}' must be an integer paise amount.")

        if int_val < 0:
            raise IntentMonetaryError(f"Field '{field_name}' cannot be negative.")
        return int_val

    @classmethod
    def _validate_item(
        cls,
        raw_item: Any,
        *,
        index: int,
        parent_merchant_id: str,
        parent_currency: Currency,
    ) -> CartItem:
        """Validate a single item proposal dictionary."""
        if not isinstance(raw_item, dict):
            raise IntentStructuralError(f"Line item at index {index} must be an object.")

        cls._scan_for_authority_injections(raw_item, path=f"items[{index}]")

        product_id = cls._validate_identifier(
            raw_item.get("product_id"), field_name=f"items[{index}].product_id"
        )

        item_merchant_id = raw_item.get("merchant_id")
        if item_merchant_id is not None:
            clean_item_merchant = cls._validate_identifier(
                item_merchant_id, field_name=f"items[{index}].merchant_id"
            )
            if clean_item_merchant != parent_merchant_id:
                raise IntentAmbiguityError(
                    f"Item '{product_id}' merchant_id '{clean_item_merchant}' conflicts "
                    f"with proposal merchant_id '{parent_merchant_id}'."
                )
        else:
            clean_item_merchant = parent_merchant_id

        name_val = raw_item.get("name")
        if not isinstance(name_val, str) or not name_val.strip():
            raise IntentStructuralError(f"Item at index {index} missing valid 'name' string.")
        name_clean = name_val.strip()
        if len(name_clean) > 500:
            raise IntentStructuralError(
                f"Item at index {index} 'name' length ({len(name_clean)}) exceeds limit of 500."
            )

        cat_val = raw_item.get("category")
        if not isinstance(cat_val, str) or not cat_val.strip():
            raise IntentStructuralError(f"Item at index {index} missing valid 'category' string.")
        category_clean = cat_val.strip().lower()
        if len(category_clean) > 100:
            raise IntentStructuralError(
                f"Item at index {index} 'category' length ({len(category_clean)}) exceeds limit of 100."
            )

        quantity = cls._validate_integer_amount(
            raw_item.get("quantity"), field_name=f"items[{index}].quantity"
        )
        if quantity <= 0:
            raise IntentMonetaryError(f"Item '{product_id}' quantity must be >= 1.")
        if quantity > MAX_ITEM_QUANTITY:
            raise IntentMonetaryError(
                f"Item '{product_id}' quantity ({quantity}) exceeds maximum limit of {MAX_ITEM_QUANTITY}."
            )

        unit_price_paise = cls._validate_integer_amount(
            raw_item.get("unit_price_paise"), field_name=f"items[{index}].unit_price_paise"
        )
        if unit_price_paise > MAX_SINGLE_ITEM_PRICE_PAISE:
            raise IntentMonetaryError(
                f"Item '{product_id}' unit price ({unit_price_paise} paise) exceeds limit "
                f"of {MAX_SINGLE_ITEM_PRICE_PAISE} paise."
            )

        item_curr_str = raw_item.get("currency")
        if item_curr_str is not None:
            item_currency = cls._validate_currency(item_curr_str)
            if item_currency is not parent_currency:
                raise IntentAmbiguityError(
                    f"Item '{product_id}' currency '{item_currency.value}' conflicts "
                    f"with proposal currency '{parent_currency.value}'."
                )

        return CartItem(
            product_id=product_id,
            merchant_id=clean_item_merchant,
            name=name_clean,
            category=category_clean,
            quantity=quantity,
            unit_price_paise=unit_price_paise,
            currency=parent_currency,
        )

    @classmethod
    def _sanitize_metadata(cls, raw_meta: Any) -> dict[str, Any]:
        """Sanitize metadata dictionary, stripping non-primitive or unsafe keys."""
        if not isinstance(raw_meta, dict):
            return {}
        clean: dict[str, Any] = {}
        for k, v in raw_meta.items():
            if not isinstance(k, str):
                continue
            key_clean = k.strip()
            if key_clean.lower() in FORBIDDEN_AUTHORITY_KEYS:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean[key_clean] = v
            elif isinstance(v, dict):
                clean[key_clean] = cls._sanitize_metadata(v)
        return clean
