"""
S01.1 — Money Value Object.

An immutable, strongly-typed, paise-based monetary value.

Key design decisions:
- All amounts are stored as integer paise (₹1 = 100 paise) to avoid
  floating-point rounding errors in financial calculations.
- Currency is part of the value object — cross-currency arithmetic raises.
- Arithmetic operations return new Money instances (immutable).
- Negative money is not permitted (raises ValueError).
- Maximum safe paise value prevents integer overflow in downstream checks.

This module has zero imports from the rest of the application.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.api.domain.types import Currency

# Maximum single transaction amount: ₹10,00,000 (10 lakh) in paise.
# Prevents integer overflow and unrealistic mandate values.
_MAX_PAISE: int = 100_000_000  # ₹10,00,000


@dataclass(frozen=True, slots=True)
class Money:
    """
    Immutable monetary value pinned to a single Currency.

    Attributes:
        paise: Non-negative integer amount in paise (₹1 = 100 paise).
        currency: Currency enum member.

    Examples:
        >>> m = Money.of_rupees(3000, Currency.INR)  # ₹3,000
        >>> m.paise
        300000
        >>> m.to_rupees()
        3000.0
    """

    paise: int
    currency: Currency

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        if not isinstance(self.paise, int):
            raise TypeError(f"paise must be int, got {type(self.paise).__name__}")
        if self.paise < 0:
            raise ValueError(f"Money amount cannot be negative: {self.paise} paise")
        if self.paise > _MAX_PAISE:
            raise ValueError(
                f"Money amount {self.paise} paise exceeds maximum {_MAX_PAISE} paise "
                f"(₹{_MAX_PAISE // 100:,})"
            )
        if not isinstance(self.currency, Currency):
            raise TypeError(f"currency must be Currency enum, got {type(self.currency).__name__}")

    @classmethod
    def of_rupees(cls, rupees: int | float, currency: Currency = Currency.INR) -> Money:
        """
        Create a Money instance from a rupee amount.

        Args:
            rupees: Rupee amount (will be converted to paise; must be non-negative).
            currency: Target currency.

        Returns:
            Money instance with paise = int(rupees * 100).

        Raises:
            ValueError: if rupees is negative or produces fractional paise.
        """
        if rupees < 0:
            raise ValueError(f"Rupee amount cannot be negative: {rupees}")
        paise = int(rupees * 100)
        if abs(paise - rupees * 100) > 1e-9:
            raise ValueError(
                f"Rupee amount {rupees} produces fractional paise; " "use integer paise directly."
            )
        return cls(paise=paise, currency=currency)

    @classmethod
    def zero(cls, currency: Currency = Currency.INR) -> Money:
        """Return a zero-valued Money instance."""
        return cls(paise=0, currency=currency)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def to_rupees(self) -> float:
        """Return the amount expressed as rupees (float)."""
        return self.paise / 100.0

    # ------------------------------------------------------------------
    # Arithmetic (immutable — all operations return new Money)
    # ------------------------------------------------------------------

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency is not other.currency:
            raise ValueError(f"Currency mismatch: {self.currency.value} vs {other.currency.value}")

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return Money(paise=self.paise + other.paise, currency=self.currency)

    def __sub__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        result = self.paise - other.paise
        if result < 0:
            raise ValueError(
                f"Subtraction would produce negative Money: "
                f"{self.paise} - {other.paise} = {result} paise"
            )
        return Money(paise=result, currency=self.currency)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.paise <= other.paise

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.paise < other.paise

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.paise >= other.paise

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.paise > other.paise

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.paise == other.paise and self.currency is other.currency

    def __repr__(self) -> str:
        return f"Money(paise={self.paise}, currency={self.currency.value!r})"

    def __str__(self) -> str:
        return (
            f"₹{self.to_rupees():,.2f}"
            if self.currency is Currency.INR
            else f"{self.currency.value} {self.to_rupees():,.2f}"
        )
