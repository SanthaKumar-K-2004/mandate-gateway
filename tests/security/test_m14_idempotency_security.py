"""
M14 Security Tests — Idempotency Key Context Binding, Payload Tamper Defense & Replay Isolation
"""

import unittest
from db.repository.execution_attempt_repository import compute_payload_fingerprint


class TestM14IdempotencySecurity(unittest.TestCase):
    """Test payload fingerprint calculation and idempotency security invariant guarantees."""

    def test_canonical_payload_fingerprint_deterministic(self) -> None:
        p1 = {"b": 2, "a": 1, "c": [1, 2, 3]}
        p2 = {"a": 1, "c": [1, 2, 3], "b": 2}

        fp1 = compute_payload_fingerprint(p1)
        fp2 = compute_payload_fingerprint(p2)

        self.assertEqual(fp1, fp2)

    def test_modified_payload_changes_fingerprint(self) -> None:
        p1 = {"merchant_id": "mer_1", "amount_paise": 1000}
        p2 = {"merchant_id": "mer_1", "amount_paise": 5000}

        fp1 = compute_payload_fingerprint(p1)
        fp2 = compute_payload_fingerprint(p2)

        self.assertNotEqual(fp1, fp2)


if __name__ == "__main__":
    unittest.main()
