"""
Unit tests for Money value object (S01.1).
"""

import unittest

from apps.api.domain.money import Money
from apps.api.domain.types import Currency


class TestDomainMoney(unittest.TestCase):
    """Test Money immutability, arithmetic, overflow prevention, and currency safety."""

    def test_construction_and_accessors(self) -> None:
        m = Money(paise=300000, currency=Currency.INR)
        self.assertEqual(m.paise, 300000)
        self.assertEqual(m.currency, Currency.INR)
        self.assertEqual(m.to_rupees(), 3000.0)

    def test_of_rupees_factory(self) -> None:
        m = Money.of_rupees(150.50, Currency.INR)
        self.assertEqual(m.paise, 15050)
        self.assertEqual(m.to_rupees(), 150.50)

    def test_negative_money_prohibited(self) -> None:
        with self.assertRaises(ValueError):
            Money(paise=-100, currency=Currency.INR)
        with self.assertRaises(ValueError):
            Money.of_rupees(-10, Currency.INR)

    def test_overflow_protection(self) -> None:
        with self.assertRaises(ValueError):
            Money(paise=200_000_000, currency=Currency.INR)

    def test_addition(self) -> None:
        m1 = Money.of_rupees(100, Currency.INR)
        m2 = Money.of_rupees(50, Currency.INR)
        result = m1 + m2
        self.assertEqual(result.paise, 15000)
        self.assertEqual(result.currency, Currency.INR)

    def test_subtraction(self) -> None:
        m1 = Money.of_rupees(100, Currency.INR)
        m2 = Money.of_rupees(40, Currency.INR)
        result = m1 - m2
        self.assertEqual(result.paise, 6000)

    def test_subtraction_underflow_raises(self) -> None:
        m1 = Money.of_rupees(40, Currency.INR)
        m2 = Money.of_rupees(100, Currency.INR)
        with self.assertRaises(ValueError):
            _ = m1 - m2

    def test_currency_mismatch_raises(self) -> None:
        m1 = Money.of_rupees(100, Currency.INR)
        m2 = Money.of_rupees(100, Currency.USD)
        with self.assertRaises(ValueError):
            _ = m1 + m2
        with self.assertRaises(ValueError):
            _ = m1 - m2
        with self.assertRaises(ValueError):
            _ = m1 < m2

    def test_comparisons(self) -> None:
        m1 = Money.of_rupees(100, Currency.INR)
        m2 = Money.of_rupees(200, Currency.INR)
        m3 = Money.of_rupees(100, Currency.INR)

        self.assertTrue(m1 < m2)
        self.assertTrue(m1 <= m3)
        self.assertTrue(m2 > m1)
        self.assertTrue(m2 >= m1)
        self.assertEqual(m1, m3)
        self.assertNotEqual(m1, m2)


if __name__ == "__main__":
    unittest.main()
