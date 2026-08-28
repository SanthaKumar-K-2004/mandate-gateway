"use client";

import React, { useState } from "react";

interface TransactionItem {
  id: string;
  buyerId: string;
  merchantId: string;
  amountPaise: number;
  state: "AUTHORIZED" | "STEP_UP_REQUIRED" | "COMMITTED" | "FAILED";
  decision: "ALLOW" | "STEP_UP_REQUIRED" | "REJECT";
  razorpayStatus: string;
  checksPassed: string[];
  checksFailed: string[];
}

const SAMPLE_TRANSACTIONS: TransactionItem[] = [
  {
    id: "tx_auto_98234",
    buyerId: "buy_user_99",
    merchantId: "mer_office_depot",
    amountPaise: 450000,
    state: "COMMITTED",
    decision: "ALLOW",
    razorpayStatus: "order_created (order_Px91823)",
    checksPassed: ["merchant_policy", "mandate_active", "daily_budget", "autonomous_limit"],
    checksFailed: [],
  },
  {
    id: "tx_stepup_12345",
    buyerId: "buy_user_99",
    merchantId: "mer_tech_store",
    amountPaise: 1200000,
    state: "STEP_UP_REQUIRED",
    decision: "STEP_UP_REQUIRED",
    razorpayStatus: "NOT_ATTEMPTED (AWAITING STEP-UP CONFIRMATION)",
    checksPassed: ["merchant_policy", "mandate_active", "daily_budget"],
    checksFailed: ["autonomous_limit_exceeded (₹12,000 > ₹5,000)"],
  },
];

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<TransactionItem[]>(SAMPLE_TRANSACTIONS);

  const handleStepUpDecision = (txId: string, approved: boolean) => {
    setTransactions(
      transactions.map((tx) =>
        tx.id === txId
          ? {
              ...tx,
              state: approved ? ("COMMITTED" as const) : ("FAILED" as const),
              razorpayStatus: approved
                ? "order_created (order_StepUpApproved)"
                : "REJECTED_BY_BUYER",
            }
          : tx
      )
    );
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-bold">Page D — Real-Time Transaction Monitor</h1>
        <p className="text-gray-600 text-sm">Transaction state machine, policy evaluation, and Razorpay execution trace</p>
      </header>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">Transaction Activity Stream</h2>
        <div className="space-y-4">
          {transactions.map((tx) => (
            <div key={tx.id} className="p-5 border rounded-lg space-y-3 bg-white shadow-xs">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-3">
                  <span className="font-bold text-md text-gray-900">{tx.id}</span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-bold ${
                      tx.state === "COMMITTED"
                        ? "bg-green-100 text-green-800"
                        : tx.state === "STEP_UP_REQUIRED"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    State: {tx.state}
                  </span>
                </div>
                <span className="font-bold text-lg text-blue-900">
                  ₹{(tx.amountPaise / 100).toLocaleString()}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs bg-gray-50 p-3 rounded">
                <div>
                  <span className="font-semibold text-gray-700 block mb-1">Passed Controls:</span>
                  <ul className="list-disc list-inside text-green-700 space-y-0.5">
                    {tx.checksPassed.map((c, i) => (
                      <li key={i}>✓ {c}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <span className="font-semibold text-gray-700 block mb-1">Failed / Step-Up Triggers:</span>
                  {tx.checksFailed.length === 0 ? (
                    <span className="text-gray-500 italic">None</span>
                  ) : (
                    <ul className="list-disc list-inside text-amber-700 space-y-0.5">
                      {tx.checksFailed.map((f, i) => (
                        <li key={i}>⚠ {f}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="text-xs text-gray-600 font-mono bg-gray-900 text-gray-200 p-2 rounded">
                Razorpay Execution Status: {tx.razorpayStatus}
              </div>

              {tx.state === "STEP_UP_REQUIRED" && (
                <div className="pt-2 flex space-x-3 border-t">
                  <button
                    onClick={() => handleStepUpDecision(tx.id, true)}
                    className="flex-1 bg-green-600 text-white font-bold py-2 rounded text-xs hover:bg-green-700"
                  >
                    Approve Step-Up Purchase
                  </button>
                  <button
                    onClick={() => handleStepUpDecision(tx.id, false)}
                    className="flex-1 bg-red-600 text-white font-bold py-2 rounded text-xs hover:bg-red-700"
                  >
                    Reject Step-Up Purchase
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
