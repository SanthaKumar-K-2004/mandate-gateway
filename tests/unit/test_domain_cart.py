"""
Unit tests for Cart & cart_hash determinism.
"""

import unittest

from apps.api.domain.cart import Cart, CartItem
from apps.api.domain.cart_integrity import (
    build_cart_with_hash,
    compute_cart_hash,
    verify_cart_integrity,
)
from apps.api.domain.types import Currency


class TestDomainCart(unittest.TestCase):
    """Test Cart line items, total validation, canonical hash determinism, and tamper detection."""

    def setUp(self) -> None:
        self.item1 = CartItem(
            product_id="prod-101",
            merchant_id="merchant-alpha",
            name="Alpha Running Shoes",
            category="footwear",
            quantity=1,
            unit_price_paise=250000,  # ₹2,500
            currency=Currency.INR,
        )
        self.item2 = CartItem(
            product_id="prod-102",
            merchant_id="merchant-alpha",
            name="Sports Socks 3-Pack",
            category="accessories",
            quantity=2,
            unit_price_paise=25000,  # ₹250 x 2 = ₹500
            currency=Currency.INR,
        )

    def test_cart_item_subtotal(self) -> None:
        self.assertEqual(self.item1.subtotal_paise(), 250000)
        self.assertEqual(self.item2.subtotal_paise(), 50000)

    def test_cart_total_validation(self) -> None:
        # Items subtotal = 250000 + 50000 = 300000 paise (₹3,000)
        cart = build_cart_with_hash(
            merchant_id="merchant-alpha",
            mandate_id="mandate-999",
            currency=Currency.INR,
            items=(self.item1, self.item2),
            tax_paise=0,
            shipping_paise=0,
            total_paise=300000,
        )
        self.assertTrue(cart.cart_hash)
        self.assertEqual(len(cart.cart_hash), 64)

    def test_cart_total_mismatch_raises(self) -> None:
        # Declared total 400000 != computed total 300000
        with self.assertRaises(ValueError):
            Cart(
                merchant_id="merchant-alpha",
                mandate_id="mandate-999",
                currency=Currency.INR,
                items=(self.item1, self.item2),
                tax_paise=0,
                shipping_paise=0,
                total_paise=400000,
            )

    def test_cart_hash_determinism(self) -> None:
        # Hashing item1, item2 vs item2, item1 must produce IDENTICAL hashes
        hash1 = compute_cart_hash(
            merchant_id="merchant-alpha",
            mandate_id="mandate-999",
            currency=Currency.INR,
            items=[self.item1, self.item2],
            tax_paise=0,
            shipping_paise=0,
            total_paise=300000,
        )
        hash2 = compute_cart_hash(
            merchant_id="merchant-alpha",
            mandate_id="mandate-999",
            currency=Currency.INR,
            items=[self.item2, self.item1],  # swapped order
            tax_paise=0,
            shipping_paise=0,
            total_paise=300000,
        )
        self.assertEqual(
            hash1, hash2, "Cart hashing must be order-invariant (sorted by product_id)"
        )

    def test_cart_tamper_detection(self) -> None:
        cart = build_cart_with_hash(
            merchant_id="merchant-alpha",
            mandate_id="mandate-999",
            currency=Currency.INR,
            items=(self.item1, self.item2),
            tax_paise=0,
            shipping_paise=0,
            total_paise=300000,
        )
        original_hash = cart.cart_hash

        # Verify integrity succeeds with original hash
        self.assertTrue(verify_cart_integrity(cart, original_hash))

        # Verify integrity fails if approved hash was modified
        self.assertFalse(verify_cart_integrity(cart, "a" * 64))


if __name__ == "__main__":
    unittest.main()
