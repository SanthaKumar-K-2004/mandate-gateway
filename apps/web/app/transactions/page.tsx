"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Navbar from "../components/Navbar";

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
      const [listRes, opsRes, ...txResults] = await Promise.allSettled([
        fetch(`${API}/api/transactions`).then((r) => r.json()),
        fetch(`${API}/internal/operations/transactions`).then((r) => r.json()),
        ...SAMPLE_TX_IDS.map((id) =>
          fetch(`${API}/api/transactions/${id}`).then((r) => r.json())
        ),
      ]);

      const items: Transaction[] = [];

      // From list endpoint
      if (listRes.status === "fulfilled" && Array.isArray(listRes.value)) {
        items.push(...listRes.value.map((t: any) => ({
          transaction_id: t.transaction_id,
          buyer_id: t.buyer_id,
          merchant_id: t.merchant_id,
          amount_paise: t.amount_paise,
          state: t.state,
          decision: t.decision_trace?.decision || t.state,
          checks_passed: t.decision_trace?.checks_passed || [],
          checks_failed: t.decision_trace?.checks_failed || [],
          created_at: t.created_at || new Date().toISOString(),
          mandate_id: t.mandate_id,
        })));
      }

      // From operations endpoint
      if (opsRes.status === "fulfilled") {
        const opsData = (opsRes as PromiseFulfilledResult<any>).value;
        const opsTxs = opsData.transactions || opsData.items || [];
        for (const t of opsTxs) {
          if (!items.find((x) => x.transaction_id === t.transaction_id)) {
            items.push(t);
          }
        }
      }

      // From individual tx endpoints
      for (const r of txResults) {
        if (r.status === "fulfilled") {
          const d = (r as PromiseFulfilledResult<any>).value;
          if (!d.error && d.transaction_id) {
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
    <div className="min-h-screen bg-[#040711] text-slate-100 font-sans pb-16">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 md:px-8 py-8 space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-white/[0.08]">
          <div>
            <span className="text-[11px] font-mono text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-500/20 font-bold uppercase tracking-wider">
              CRYPTOGRAPHIC LEDGER
            </span>
            <h1 className="text-3xl font-extrabold text-white tracking-tight mt-1">TRANSACTION & AUDIT TRAIL LEDGER</h1>
            <p className="text-xs text-slate-400 mt-0.5">Cryptographic state machine • SHA-256 evidence • 5-layer safety trace & step-up approval gate</p>
          </div>
          <button onClick={fetchTransactions} className="text-xs font-bold text-slate-300 hover:text-white bg-[#090d1a] border border-white/[0.08] px-3.5 py-2.5 rounded-xl hover:border-white/[0.2] transition">
            ↻ Refresh Ledger
          </button>
        </div>

        {/* Stats Row */}
        {transactions.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Transactions", value: transactions.length, color: "text-white" },
              { label: "Committed & Authorized", value: transactions.filter((t) => t.state === "COMMITTED" || t.state === "AUTHORIZED").length, color: "text-emerald-400" },
              { label: "Step-Up Approval Locks", value: transactions.filter((t) => t.state === "STEP_UP_REQUIRED").length, color: "text-amber-400" },
              { label: "Total Volume", value: `₹${(transactions.reduce((s, t) => s + (t.amount_paise || 0), 0) / 100).toLocaleString()}`, color: "text-blue-400" },
            ].map((stat) => (
              <div key={stat.label} className="glass-card rounded-2xl p-4 text-center">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">{stat.label}</p>
                <p className={`text-2xl font-black font-mono ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Transaction Stream */}
        <section className="glass-card p-6 rounded-2xl space-y-4">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              Transaction Activity Stream ({transactions.length})
            </h2>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20 font-medium">LIVE REAL-TIME DATA</span>
          </div>

          {loading ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm font-semibold text-slate-300">Fetching transaction ledger from backend...</p>
            </div>
          ) : error && transactions.length === 0 ? (
            <div className="py-12 text-center space-y-3 glass-panel rounded-2xl border-dashed">
              <p className="text-slate-400 text-sm">{error}</p>
              <Link href="/buyer" className="inline-block text-xs font-bold text-blue-400 hover:text-blue-300">
                → Go to Buyer Portal to execute a purchase →
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {transactions.map((tx) => {
                const decided = stepUpDecision[tx.transaction_id];
                return (
                  <div key={tx.transaction_id} className="glass-panel p-5 rounded-2xl space-y-3 hover:border-white/[0.2] transition-all duration-300">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-mono font-bold text-white text-sm">{tx.transaction_id}</span>
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full border ${stateColor(decided ? (decided.startsWith("APPROVED") ? "COMMITTED" : "FAILED") : tx.state)}`}>
                          {decided ? (decided.startsWith("APPROVED") ? "COMMITTED" : "REJECTED") : tx.state}
                        </span>
                        {tx.decision && (
                          <span className={`text-[10px] px-2.5 py-0.5 rounded-full border font-mono font-bold ${tx.decision === "ALLOW" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : tx.decision === "STEP_UP_REQUIRED" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"}`}>
                            {tx.decision}
                          </span>
                        )}
                      </div>
                      <span className="font-black font-mono text-lg text-blue-400">
                        ₹{((tx.amount_paise || 0) / 100).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1 border-t border-white/[0.08]">
                      <div>
                        <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Buyer</span>
                        <span className="font-mono text-slate-200">{tx.buyer_id || "—"}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Merchant</span>
                        <span className="font-mono text-slate-200">{tx.merchant_id || "—"}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Mandate ID</span>
                        <span className="font-mono text-slate-200">{tx.mandate_id || "—"}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Razorpay Order</span>
                        <span className="font-mono text-slate-200 text-[11px]">{tx.razorpay_order_id || tx.razorpay_status || "—"}</span>
                      </div>
                    </div>

                    {(tx.checks_passed?.length || tx.checks_failed?.length) ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-black/40 p-3 rounded-xl border border-white/[0.06]">
                        <div>
                          <span className="font-bold text-emerald-400 block mb-1">✓ Passed Security Controls</span>
                          <ul className="space-y-0.5">
                            {(tx.checks_passed || []).map((c, i) => (
                              <li key={i} className="text-emerald-400/90 font-mono text-[11px]">• {c}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <span className="font-bold text-amber-400 block mb-1">⚠ Step-Up / Policy Triggers</span>
                          {(tx.checks_failed || []).length === 0 ? (
                            <span className="text-slate-500 italic text-[11px]">None</span>
                          ) : (
                            <ul className="space-y-0.5">
                              {(tx.checks_failed || []).map((f, i) => (
                                <li key={i} className="text-amber-400/90 font-mono text-[11px]">• {f}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    ) : null}

                    {/* Razorpay status */}
                    {(tx.razorpay_status || tx.razorpay_order_id) && (
                      <div className="text-xs font-mono bg-black/50 border border-white/[0.08] text-cyan-400 p-2.5 rounded-xl">
                        Razorpay Order: {tx.razorpay_order_id || tx.razorpay_status}
                      </div>
                    )}

                    {/* Step-Up Controls */}
                    {(tx.state === "STEP_UP_REQUIRED") && !decided && (
                      <div className="pt-3 flex gap-3 border-t border-white/[0.08]">
                        <button
                          onClick={() => handleStepUp(tx.transaction_id, true)}
                          disabled={processingStepUp === tx.transaction_id}
                          className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-black font-extrabold py-2.5 rounded-xl text-xs transition shadow-lg shadow-emerald-500/20 disabled:opacity-50 hover:scale-[1.01]"
                        >
                          ✓ Approve Human Step-Up Token
                        </button>
                        <button
                          onClick={() => handleStepUp(tx.transaction_id, false)}
                          disabled={processingStepUp === tx.transaction_id}
                          className="flex-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 font-bold py-2.5 rounded-xl text-xs transition disabled:opacity-50"
                        >
                          ✕ Reject Step-Up Purchase
                        </button>
                      </div>
                    )}

                    {decided && (
                      <div className={`text-xs font-mono font-bold p-3 rounded-xl border ${decided.startsWith("APPROVED") ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"}`}>
                        Human Approval Result: {decided}
                      </div>
                    )}

                    {/* Timeline toggle */}
                    <button
                      onClick={() => fetchTimeline(tx.transaction_id)}
                      className="text-xs text-slate-400 hover:text-white font-semibold flex items-center gap-1.5 transition"
                    >
                      {expandedTx === tx.transaction_id ? "▲ Hide Timeline" : "▼ Show Audit Event Timeline"}
                    </button>

                    {expandedTx === tx.transaction_id && (
                      <div className="pt-3 border-t border-white/[0.08] space-y-2">
                        {loadingTimeline === tx.transaction_id ? (
                          <div className="text-xs text-slate-400 animate-pulse">Loading timeline events...</div>
                        ) : (timeline[tx.transaction_id] || []).length === 0 ? (
                          <div className="text-xs text-slate-500 italic">No timeline events available.</div>
                        ) : (
                          (timeline[tx.transaction_id] || []).map((ev, i) => (
                            <div key={i} className="flex items-start gap-3 text-xs bg-black/40 p-2 rounded-lg border border-white/[0.04]">
                              <span className="text-slate-500 font-mono text-[11px] whitespace-nowrap">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                              <span className="text-slate-200 font-medium">{ev.event}</span>
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

