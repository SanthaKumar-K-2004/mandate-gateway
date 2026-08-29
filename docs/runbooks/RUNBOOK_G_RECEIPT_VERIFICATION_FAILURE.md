# Runbook G — Ed25519 Action Receipt Verification Failure

## Detection
- **Alert**: `receipt_signature_verification_failure`
- **Condition**: `receipt_verification_failures_total > 0`.

## Impact
- Inability to verify authenticity of signed action receipts.

## Immediate Safety Rule
> [!IMPORTANT]
> Unverified or invalid receipts must be rejected by client applications and external verifiers.

## Diagnosis Steps
1. Fetch receipt details (`receipt_id`, `canonical_payload_hash`, `signature_hex`, `public_key_hex`).
2. Verify Ed25519 public key matches current or active historical public key in key store.
3. Check for payload canonicalization mismatches (field order, spacing, UTF-8 encoding).

## Verification Steps
1. Re-run cryptographic verification using standard Ed25519 signature verifier.

## Recovery Steps
1. If key rotation occurred -> ensure verifier includes updated public key ring.
2. If invalid signature -> flag transaction receipt as unverified in audit logs.

## Escalation Criteria
- Escalates to Cryptographic Engineer if signing key store corruption is suspected.

## Forbidden Actions
- Do NOT disable Ed25519 verification checks.
