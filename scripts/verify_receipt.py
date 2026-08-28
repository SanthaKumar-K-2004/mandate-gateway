#!/usr/bin/env python3
"""
Mandate Gateway — Standalone Action Receipt Verifier CLI
Section S02.6 / Phase 10 (Section 20, PROJECT_CONTEXT.md)

Verifies Ed25519-signed action_receipt.json files offline without database
or network connectivity.

Usage:
    python scripts/verify_receipt.py receipt.json [--public-key <hex_or_base64_pubkey>]

Output format on success (exit 0):
    VALID RECEIPT
    ✓ Signature valid
    ✓ Payload canonical
    ✓ Hash valid
    ✓ Transaction binding valid

Output format on failure (exit 1):
    INVALID RECEIPT
    ✗ Verification failed: <error details>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path if running as script
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from apps.api.domain.receipt_verifier import ReceiptVerifier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify an Ed25519-signed Mandate Gateway Action Receipt offline."
    )
    parser.add_argument(
        "receipt_file",
        help="Path to action_receipt.json file to verify.",
    )
    parser.add_argument(
        "--public-key",
        dest="public_key",
        default=None,
        help=(
            "Ed25519 public key (hex string or base64). "
            "If omitted, attempts to read from receipt details or environment."
        ),
    )
    parser.add_argument(
        "--expected-transaction-id",
        dest="expected_transaction_id",
        default=None,
        help="Optional expected transaction_id binding.",
    )
    parser.add_argument(
        "--expected-mandate-id",
        dest="expected_mandate_id",
        default=None,
        help="Optional expected mandate_id binding.",
    )
    parser.add_argument(
        "--expected-merchant-id",
        dest="expected_merchant_id",
        default=None,
        help="Optional expected merchant_id binding.",
    )

    args = parser.parse_args()

    receipt_path = Path(args.receipt_file)
    if not receipt_path.exists():
        print(f"INVALID RECEIPT\n✗ File not found: {receipt_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(receipt_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as exc:
        print(f"INVALID RECEIPT\n✗ Failed to parse JSON file: {exc}", file=sys.stderr)
        sys.exit(1)

    # Resolve public key
    pubkey = args.public_key
    if not pubkey:
        # Check if public key is included in raw_data metadata
        pubkey = raw_data.get("public_key") or raw_data.get("signer_public_key")

    if not pubkey:
        print(
            "INVALID RECEIPT\n✗ Public key must be specified via --public-key or embedded in receipt metadata.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = ReceiptVerifier.verify(
        receipt=raw_data,
        public_key=pubkey,
        expected_transaction_id=args.expected_transaction_id,
        expected_mandate_id=args.expected_mandate_id,
        expected_merchant_id=args.expected_merchant_id,
    )

    print(result.summary())
    if result.is_valid:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
