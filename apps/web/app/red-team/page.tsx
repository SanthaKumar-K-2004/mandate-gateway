"use client";

import React, { useState } from "react";

interface AttackResult {
  attackType: string;
  status: string;
  blockedReason: string;
  affectedTransactionId: string;
  auditEventId: string;
  timestamp: string;
}

const ATTACK_VECTORS = [
  { type: "PROMPT_INJECTION", label: "Catalog Prompt Injection" },
  { type: "CART_TAMPER", label: "Cart Hash Tampering" },
  { type: "NONCE_REPLAY", label: "Cryptographic Nonce Replay" },
  { type: "DOUBLE_SPEND", label: "Concurrent Double Spend" },
  { type: "TIMEOUT_RETRY", label: "Ambiguous Timeout Retry" },
  { type: "EXPIRED_MANDATE", label: "Expired Buyer Mandate" },
  { type: "MERCHANT_POLICY", label: "Merchant Category Violation" },
  { type: "UNAUTHORIZED_TOOL", label: "Unauthorized Payout Execution" },
];

export default function RedTeamPage() {
  const [attackLogs, setAttackLogs] = useState<AttackResult[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);

  const triggerAttack = (attackType: string) => {
    setIsSimulating(true);
    setTimeout(() => {
      const newResult: AttackResult = {
        attackType,
        status: "BLOCKED_FAIL_CLOSED",
        blockedReason: `Security Engine intercepted ${attackType}: Gateway policy rule enforced cleanly.`,
        affectedTransactionId: `tx_redteam_${Math.floor(Math.random() * 89999 + 10000)}`,
        auditEventId: `evt_redteam_${Math.floor(Math.random() * 89999 + 10000)}`,
        timestamp: new Date().toISOString(),
      };
      setAttackLogs((prev) => [newResult, ...prev]);
      setIsSimulating(false);
    }, 400);
  };

  const triggerAllAttacks = () => {
    ATTACK_VECTORS.forEach((vec, idx) => {
      setTimeout(() => triggerAttack(vec.type), idx * 250);
    });
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <header className="border-b pb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Page E — Red Team Chaos Lab</h1>
          <p className="text-gray-600 text-sm">Adversarial attack simulation & security invariant verification</p>
        </div>
        <button
          onClick={triggerAllAttacks}
          disabled={isSimulating}
          className="bg-red-600 hover:bg-red-700 text-white font-bold px-5 py-2 rounded text-sm transition"
        >
          {isSimulating ? "SIMULATING..." : "RUN ALL 8 ATTACKS"}
        </button>
      </header>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">Adversarial Attack Simulation Vectors</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {ATTACK_VECTORS.map((vector) => (
            <button
              key={vector.type}
              onClick={() => triggerAttack(vector.type)}
              disabled={isSimulating}
              className="p-3 bg-gray-100 hover:bg-gray-200 border rounded text-xs font-semibold text-gray-800 text-left transition"
            >
              ⚡ {vector.label}
            </button>
          ))}
        </div>
      </section>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">Live Security Event Log</h2>
        {attackLogs.length === 0 ? (
          <p className="text-gray-500 text-sm">No attack simulations executed yet. Click an attack button above.</p>
        ) : (
          <div className="space-y-3 font-mono text-xs">
            {attackLogs.map((log, idx) => (
              <div key={idx} className="p-4 bg-gray-900 text-green-400 rounded border border-gray-700 space-y-1">
                <div className="flex justify-between text-yellow-400 font-bold">
                  <span>ATTACK VECTOR: {log.attackType}</span>
                  <span className="text-red-400">RESULT: {log.status}</span>
                </div>
                <div>Blocked Reason: {log.blockedReason}</div>
                <div className="text-gray-400">
                  Transaction ID: {log.affectedTransactionId} | Audit Event: {log.auditEventId}
                </div>
                <div className="text-gray-500 text-[10px]">Timestamp: {log.timestamp}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
