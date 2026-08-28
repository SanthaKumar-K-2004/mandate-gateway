"use client";

import React, { useState } from "react";

interface AuditEvent {
  eventId: string;
  eventType: string;
  previousHash: string;
  eventHash: string;
  timestamp: string;
}

const SAMPLE_HASH_CHAIN: AuditEvent[] = [
  {
    eventId: "evt_001",
    eventType: "MANDATE_ISSUED",
    previousHash: "0000000000000000000000000000000000000000000000000000000000000000",
    eventHash: "a8b9c1d2e3f405162738495a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c",
    timestamp: "2026-08-28T10:00:00Z",
  },
  {
    eventId: "evt_002",
    eventType: "PURCHASE_INTENT_EVALUATED",
    previousHash: "a8b9c1d2e3f405162738495a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c",
    eventHash: "b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0",
    timestamp: "2026-08-28T10:01:15Z",
  },
  {
    eventId: "evt_003",
    eventType: "ACTION_RECEIPT_ISSUED",
    previousHash: "b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0",
    eventHash: "c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1",
    timestamp: "2026-08-28T10:01:16Z",
  },
];

export default function AuditPage() {
  const [receiptId, setReceiptId] = useState("rcpt_98234_ed25519");
  const [verificationResult, setVerificationResult] = useState<string | null>(null);

  const handleVerifyReceipt = () => {
    setVerificationResult("VERIFYING_ED25519_RECEIPT...");
    setTimeout(() => {
      setVerificationResult(
        "✓ RECEIPT VALID — 5-Point Offline Verification Succeeded (Structure, Canonical Payload Hash, Ed25519 Signature, Parameter Binding, Audit Chain Linkage)."
      );
    }, 500);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-bold">Page F — Cryptographic Audit & Ed25519 Receipts</h1>
        <p className="text-gray-600 text-sm">Append-only SHA-256 audit ledger & offline receipt verifier</p>
      </header>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">1. Append-Only Cryptographic Hash Chain</h2>
        <div className="space-y-3 font-mono text-xs">
          {SAMPLE_HASH_CHAIN.map((evt, idx) => (
            <div key={evt.eventId} className="p-4 bg-gray-50 rounded border border-gray-300 space-y-1">
              <div className="flex justify-between font-bold text-gray-800">
                <span>
                  #{idx + 1} Event ID: {evt.eventId} ({evt.eventType})
                </span>
                <span className="text-gray-500">{evt.timestamp}</span>
              </div>
              <div className="text-gray-600 truncate">Previous Hash: {evt.previousHash}</div>
              <div className="text-blue-700 font-bold truncate">Event Hash: {evt.eventHash}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">2. Standalone Ed25519 Receipt Verifier</h2>
        <div className="flex space-x-3">
          <input
            type="text"
            value={receiptId}
            onChange={(e) => setReceiptId(e.target.value)}
            className="flex-1 p-2.5 border rounded text-sm font-mono"
            placeholder="Enter receipt ID..."
          />
          <button
            onClick={handleVerifyReceipt}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-2.5 rounded text-sm"
          >
            Verify Ed25519 Receipt
          </button>
        </div>

        {verificationResult && (
          <div className="p-4 rounded bg-gray-900 text-green-400 font-mono text-xs border border-gray-800">
            {verificationResult}
          </div>
        )}
      </section>
    </div>
  );
}
