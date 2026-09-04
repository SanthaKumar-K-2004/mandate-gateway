"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";

const API = "http://localhost:8000";

interface Transaction {
  transaction_id: string;
  buyer_id: string;
  merchant_id: string;
  amount_paise: number;
  state: string;
  decision: string;
  razorpay_order_id?: string;
  razorpay_status?: string;
  checks_passed?: string[];
  checks_failed?: string[];
  created_at?: string;
  mandate_id?: string;
}

interface TimelineEvent {
  event: string;
  timestamp: string;
  details?: Record<string, any>;
}

const stateColor = (s: string) => {
  if (s === "COMMITTED" || s === "AUTHORIZED") return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  if (s === "STEP_UP_REQUIRED") return "bg-amber-500/10 text-amber-400 border-amber-500/30";
  if (s === "FAILED" || s === "REJECTED") return "bg-red-500/10 text-red-400 border-red-500/30";
  return "bg-slate-500/10 text-slate-400 border-slate-600";
};

const SAMPLE_TX_IDS = ["tx_auto_98234", "tx_stepup_12345"];

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTx, setExpandedTx] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<Record<string, TimelineEvent[]>>({});
  const [loadingTimeline, setLoadingTimeline] = useState<string | null>(null);
  const [stepUpDecision, setStepUpDecision] = useState<Record<string, string>>({});
  const [processingStepUp, setProcessingStepUp] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch all known tx IDs + look for recent ones via internal ops
      const [opsRes, ...txResults] = await Promise.allSettled([
        fetch(`${API}/internal/operations/transactions`).then((r) => r.json()),
        ...SAMPLE_TX_IDS.map((id) =>
          fetch(`${API}/api/transactions/${id}`).then((r) => r.json())
        ),
      ]);

      const items: Transaction[] = [];

      // From operations endpoint
      if (opsRes.status === "fulfilled") {
        const opsData = (opsRes as PromiseFulfilledResult<any>).value;
        const opsTxs = opsData.transactions || opsData.items || [];
        items.push(...opsTxs);
      }

      // From individual tx endpoints
      for (const r of txResults) {
        if (r.status === "fulfilled") {
          const d = (r as PromiseFulfilledResult<any>).value;
          if (!d.error && d.transaction_id) {
            // Avoid duplicates
            if (!items.find((t) => t.transaction_id === d.transaction_id)) {
              items.push(d);
            }
          }
        }
      }

      setTransactions(items);
      if (items.length === 0) setError("No transactions found yet. Try running a purchase from the Buyer Portal.");
    } catch {
      setError("Could not reach backend API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
    const iv = setInterval(fetchTransactions, 20000);
    return () => clearInterval(iv);
  }, [fetchTransactions]);

  const fetchTimeline = async (txId: string) => {
    if (timeline[txId]) {
      setExpandedTx((prev) => (prev === txId ? null : txId));
      return;
    }
    setLoadingTimeline(txId);
    setExpandedTx(txId);
    try {
      const res = await fetch(`${API}/api/transactions/${txId}/events`);
      const data = await res.json();
      const events = data.events || data.timeline || [];
      setTimeline((prev) => ({ ...prev, [txId]: events }));
    } catch {
      setTimeline((prev) => ({ ...prev, [txId]: [] }));
    } finally {
      setLoadingTimeline(null);
    }
  };

  const handleStepUp = async (txId: string, approve: boolean) => {
    setProcessingStepUp(txId);
    try {
      const endpoint = approve
        ? `${API}/api/transactions/${txId}/approve`
        : `${API}/api/transactions/${txId}/reject`;
      const res = await fetch(endpoint, { method: "POST" });
      const data = await res.json();
      setStepUpDecision((prev) => ({
        ...prev,
        [txId]: approve ? `APPROVED — ${data.razorpay_order_id || "Committed"}` : "REJECTED BY BUYER",
      }));
      await fetchTransactions();
    } catch {
      setStepUpDecision((prev) => ({
        ...prev,
        [txId]: approve ? "APPROVED (offline mode)" : "REJECTED",
      }));
    } finally {
      setProcessingStepUp(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 font-sans pb-16">
      {/* Navbar */}
      <header className="border-b border-slate-800/80 px-8 py-5 flex justify-between items-center bg-[#0d1322]">
        <div className="flex items-center gap-3">
          <Link href="/" className="w-9 h-9 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center font-black text-lg text-white shadow-lg shadow-cyan-500/20">
            T
          </Link>
          <div>
            <h1 className="text-lg font-extrabold text-white m-0">TRANSACTION LEDGER</h1>
            <p className="text-xs text-slate-400 m-0">Cryptographic state machine • SHA-256 evidence • Razorpay execution trace</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchTransactions} className="text-xs font-bold text-slate-400 hover:text-white bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700">
            ↻ Refresh
          </button>
          <Link href="/" className="text-xs font-bold text-slate-400 hover:text-white bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700">
            ← Hub
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-8 space-y-6">
        {/* Stats Row */}
        {transactions.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total", value: transactions.length, color: "text-white" },
              { label: "Committed", value: transactions.filter((t) => t.state === "COMMITTED" || t.state === "AUTHORIZED").length, color: "text-emerald-400" },
              { label: "Step-Up Pending", value: transactions.filter((t) => t.state === "STEP_UP_REQUIRED").length, color: "text-amber-400" },
              { label: "Total Value", value: `₹${(transactions.reduce((s, t) => s + (t.amount_paise || 0), 0) / 100).toLocaleString()}`, color: "text-blue-400" },
            ].map((stat) => (
              <div key={stat.label} className="bg-[#111827] border border-slate-800 rounded-xl p-4 text-center">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{stat.label}</p>
                <p className={`text-2xl font-extrabold ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Transaction Stream */}
        <section className="bg-[#111827] border border-slate-800 p-6 rounded-2xl shadow-xl">
          <div className="flex justify-between items-center mb-5">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-cyan-500 rounded-full" />
              Transaction Activity Stream ({transactions.length})
            </h2>
            <span className="text-xs font-mono text-slate-500">LIVE — REAL-TIME BACKEND DATA</span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              <div className="inline-block w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-2" />
              <p>Fetching transaction ledger from backend...</p>
            </div>
          ) : error && transactions.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <p className="text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl py-8">{error}</p>
              <Link href="/buyer" className="inline-block text-xs font-bold text-blue-400 hover:text-blue-300">
                → Go to Buyer Portal to execute a purchase
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {transactions.map((tx) => {
                const decided = stepUpDecision[tx.transaction_id];
                return (
                  <div key={tx.transaction_id} className="bg-[#0d1322] border border-slate-800 rounded-xl p-5 space-y-3 hover:border-slate-700 transition">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-mono font-bold text-white text-sm">{tx.transaction_id}</span>
                        <span className={`text-xs px-2.5 py-0.5 rounded-md border font-bold ${stateColor(decided ? (decided.startsWith("APPROVED") ? "COMMITTED" : "FAILED") : tx.state)}`}>
                          {decided ? (decided.startsWith("APPROVED") ? "COMMITTED" : "REJECTED") : tx.state}
                        </span>
                        {tx.decision && (
                          <span className={`text-xs px-2 py-0.5 rounded border font-mono ${tx.decision === "ALLOW" ? "bg-emerald-500/5 text-emerald-500 border-emerald-500/20" : tx.decision === "STEP_UP_REQUIRED" ? "bg-amber-500/5 text-amber-500 border-amber-500/20" : "bg-red-500/5 text-red-500 border-red-500/20"}`}>
                            {tx.decision}
                          </span>
                        )}
                      </div>
                      <span className="font-extrabold text-lg text-blue-400">
                        ₹{((tx.amount_paise || 0) / 100).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      <div>
                        <span className="text-slate-500 block mb-0.5">Buyer</span>
                        <span className="font-mono text-slate-300">{tx.buyer_id || "—"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block mb-0.5">Merchant</span>
                        <span className="font-mono text-slate-300">{tx.merchant_id || "—"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block mb-0.5">Mandate</span>
                        <span className="font-mono text-slate-300">{tx.mandate_id || "—"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block mb-0.5">Razorpay Order</span>
                        <span className="font-mono text-slate-300 text-[11px]">{tx.razorpay_order_id || tx.razorpay_status || "—"}</span>
                      </div>
                    </div>

                    {(tx.checks_passed?.length || tx.checks_failed?.length) ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800/60">
                        <div>
                          <span className="font-bold text-emerald-400 block mb-1">✓ Passed Controls</span>
                          <ul className="space-y-0.5">
                            {(tx.checks_passed || []).map((c, i) => (
                              <li key={i} className="text-emerald-500/80">{c}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <span className="font-bold text-amber-400 block mb-1">⚠ Failed / Step-Up Triggers</span>
                          {(tx.checks_failed || []).length === 0 ? (
                            <span className="text-slate-500 italic">None</span>
                          ) : (
                            <ul className="space-y-0.5">
                              {(tx.checks_failed || []).map((f, i) => (
                                <li key={i} className="text-amber-500/80">{f}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    ) : null}

                    {/* Razorpay status */}
                    {(tx.razorpay_status || tx.razorpay_order_id) && (
                      <div className="text-xs font-mono bg-slate-950 border border-slate-800 text-cyan-400 p-2.5 rounded-lg">
                        Razorpay: {tx.razorpay_order_id || tx.razorpay_status}
                      </div>
                    )}

                    {/* Step-Up Controls */}
                    {(tx.state === "STEP_UP_REQUIRED") && !decided && (
                      <div className="pt-3 flex gap-3 border-t border-slate-800">
                        <button
                          onClick={() => handleStepUp(tx.transaction_id, true)}
                          disabled={processingStepUp === tx.transaction_id}
                          className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs transition disabled:opacity-50"
                        >
                          ✓ Approve Step-Up Purchase
                        </button>
                        <button
                          onClick={() => handleStepUp(tx.transaction_id, false)}
                          disabled={processingStepUp === tx.transaction_id}
                          className="flex-1 bg-red-600 hover:bg-red-500 text-white font-bold py-2.5 rounded-xl text-xs transition disabled:opacity-50"
                        >
                          ✕ Reject Step-Up Purchase
                        </button>
                      </div>
                    )}

                    {decided && (
                      <div className={`text-xs font-mono font-bold p-2.5 rounded-lg ${decided.startsWith("APPROVED") ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                        Human Decision: {decided}
                      </div>
                    )}

                    {/* Timeline toggle */}
                    <button
                      onClick={() => fetchTimeline(tx.transaction_id)}
                      className="text-xs text-slate-500 hover:text-slate-300 font-semibold flex items-center gap-1"
                    >
                      {expandedTx === tx.transaction_id ? "▲ Hide Timeline" : "▼ Show Event Timeline"}
                    </button>

                    {expandedTx === tx.transaction_id && (
                      <div className="pt-2 border-t border-slate-800/60 space-y-1.5">
                        {loadingTimeline === tx.transaction_id ? (
                          <div className="text-xs text-slate-500 animate-pulse">Loading timeline...</div>
                        ) : (timeline[tx.transaction_id] || []).length === 0 ? (
                          <div className="text-xs text-slate-600 italic">No timeline events available.</div>
                        ) : (
                          (timeline[tx.transaction_id] || []).map((ev, i) => (
                            <div key={i} className="flex items-start gap-3 text-xs">
                              <span className="text-slate-600 font-mono whitespace-nowrap">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                              <span className="text-slate-300">{ev.event}</span>
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
