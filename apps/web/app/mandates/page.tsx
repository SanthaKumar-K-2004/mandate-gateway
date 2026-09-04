"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Navbar from "../components/Navbar";

const API = "http://localhost:8000";

interface Mandate {
  mandate_id: string;
  buyer_id: string;
  merchant_id: string;
  max_amount_paise: number;
  daily_budget_paise: number;
  allowed_merchants: string[];
  allowed_categories: string[];
  expires_at: string;
  status: string;
  used_today_paise?: number;
  created_at?: string;
}

const statusColor = (s: string) => {
  if (s === "ACTIVE") return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  if (s === "REVOKED") return "bg-red-500/10 text-red-400 border-red-500/30";
  return "bg-slate-500/10 text-slate-400 border-slate-600";
};

export default function MandatesPage() {
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    buyer_id: "buy_user_99",
    merchant_id: "mer_tech_store",
    max_amount_inr: "5000",
    daily_budget_inr: "15000",
    allowed_categories: "electronics, supplies",
    expires_at: "2026-12-31",
  });
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState<string | null>(null);

  const KNOWN_IDS = ["man_buyer_01", "man_buyer_02"];

  const fetchMandates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/mandates`);
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        const normalized: Mandate[] = data.map((m: any) => ({
          mandate_id: m.mandate_id,
          buyer_id: m.buyer_id,
          merchant_id: m.merchant_scope && m.merchant_scope.length > 0 ? Array.from(m.merchant_scope)[0] as string : "ALL_MERCHANTS",
          max_amount_paise: m.maximum_amount_paise || m.max_amount_paise || 500000,
          daily_budget_paise: m.daily_budget_paise || 1000000,
          allowed_merchants: m.merchant_scope ? Array.from(m.merchant_scope) : ["ALL"],
          allowed_categories: m.category_scope ? Array.from(m.category_scope) : ["all"],
          expires_at: m.expires_at || "2026-12-31T23:59:59Z",
          status: m.status || "ACTIVE",
          used_today_paise: m.used_today_paise || 0,
          created_at: m.issued_at || m.created_at || new Date().toISOString(),
        }));
        setMandates(normalized);
      } else {
        const results = await Promise.allSettled(
          KNOWN_IDS.map((id) => fetch(`${API}/api/mandates/${id}`).then((r) => r.json()))
        );
        const items: Mandate[] = results
          .filter((r) => r.status === "fulfilled" && !(r as PromiseFulfilledResult<any>).value?.error)
          .map((r) => (r as PromiseFulfilledResult<any>).value);
        setMandates(items);
        if (items.length === 0) setError("No mandates found. Create one below.");
      }
    } catch {
      setError("Could not reach backend API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMandates();
    const iv = setInterval(fetchMandates, 30000);
    return () => clearInterval(iv);
  }, [fetchMandates]);

  const handleRevoke = async (id: string) => {
    setRevoking(id);
    try {
      const res = await fetch(`${API}/api/mandates/${id}/revoke`, { method: "POST" });
      const data = await res.json();
      if (!data.error) await fetchMandates();
    } catch {
      /* ignore */
    } finally {
      setRevoking(null);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setCreateMsg(null);
    try {
      const res = await fetch(`${API}/api/mandates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          buyer_id: form.buyer_id,
          merchant_id: form.merchant_id,
          max_amount_paise: Math.round(Number(form.max_amount_inr) * 100),
          daily_budget_paise: Math.round(Number(form.daily_budget_inr) * 100),
          allowed_merchants: [form.merchant_id],
          allowed_categories: form.allowed_categories.split(",").map((s) => s.trim()),
          expires_at: new Date(form.expires_at).toISOString(),
        }),
      });
      const data = await res.json();
      if (data.error) {
        setCreateMsg(`Error: ${data.error.message}`);
      } else {
        setCreateMsg(`Mandate ${data.mandate_id || "created"} successfully activated!`);
        setShowCreate(false);
        await fetchMandates();
      }
    } catch {
      setCreateMsg("Network error — backend unreachable.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 font-sans pb-16">
      <Navbar />

      <main className="max-w-6xl mx-auto px-8 py-8 space-y-6">
        <div className="flex justify-between items-center pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-2xl font-extrabold text-white">BUYER MANDATES STUDIO</h1>
            <p className="text-xs text-slate-400">Active authorization mandates, spend caps & one-click revocation</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreate((v) => !v)}
              className="text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white px-4 py-2 rounded-lg border border-amber-500/40 transition shadow"
            >
              + New Mandate
            </button>
            <button onClick={fetchMandates} className="text-xs font-bold text-slate-400 hover:text-white bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700">
              ↻ Refresh
            </button>
          </div>
        </div>
        {/* Create Mandate Form */}
        {showCreate && (
          <section className="bg-[#111827] border border-amber-500/20 p-6 rounded-2xl shadow-xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-amber-500 rounded-full" />
              Create New Mandate
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: "Buyer ID", key: "buyer_id" },
                { label: "Merchant ID", key: "merchant_id" },
                { label: "Allowed Categories", key: "allowed_categories" },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">{label}</label>
                  <input
                    type="text"
                    value={(form as any)[key]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="w-full bg-[#0d1322] border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-amber-500"
                  />
                </div>
              ))}
              {[
                { label: "Single Purchase Cap (₹)", key: "max_amount_inr" },
                { label: "Daily Budget (₹)", key: "daily_budget_inr" },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">{label}</label>
                  <input
                    type="number"
                    value={(form as any)[key]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="w-full bg-[#0d1322] border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-amber-500"
                  />
                </div>
              ))}
              <div>
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Expires At</label>
                <input
                  type="date"
                  value={form.expires_at}
                  onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))}
                  className="w-full bg-[#0d1322] border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>
            <div className="flex items-center gap-4 pt-2">
              <button
                onClick={handleCreate}
                disabled={creating}
                className="bg-amber-600 hover:bg-amber-500 text-white font-bold px-6 py-2.5 rounded-xl text-sm transition disabled:opacity-50"
              >
                {creating ? "Creating..." : "⚡ Create & Activate Mandate"}
              </button>
              <button onClick={() => setShowCreate(false)} className="text-xs text-slate-400 hover:text-white">Cancel</button>
              {createMsg && <span className={`text-xs font-bold ${createMsg.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>{createMsg}</span>}
            </div>
          </section>
        )}

        {/* Mandates List */}
        <section className="bg-[#111827] border border-slate-800 p-6 rounded-2xl shadow-xl">
          <div className="flex justify-between items-center mb-5">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-amber-500 rounded-full" />
              Active Authorization Mandates ({mandates.length})
            </h2>
            <span className="text-xs font-mono text-slate-500">LIVE — BACKEND VERIFIED</span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              <div className="inline-block w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-2" />
              <p>Fetching mandate records from backend...</p>
            </div>
          ) : error && mandates.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
              {error}
            </div>
          ) : (
            <div className="space-y-4">
              {mandates.map((m) => (
                <div key={m.mandate_id} className="bg-[#0d1322] border border-slate-800 rounded-xl p-5 space-y-3 hover:border-slate-700 transition">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-white text-sm">{m.mandate_id}</span>
                      <span className={`text-xs px-2.5 py-0.5 rounded-md border font-bold ${statusColor(m.status)}`}>
                        {m.status}
                      </span>
                    </div>
                    {m.status === "ACTIVE" && (
                      <button
                        onClick={() => handleRevoke(m.mandate_id)}
                        disabled={revoking === m.mandate_id}
                        className="text-xs bg-red-600/80 hover:bg-red-600 text-white font-bold py-1.5 px-4 rounded-lg transition disabled:opacity-50"
                      >
                        {revoking === m.mandate_id ? "Revoking..." : "✕ Revoke"}
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">Buyer</span>
                      <span className="text-sm font-mono text-slate-300">{m.buyer_id}</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">Single Cap</span>
                      <span className="text-base font-extrabold text-amber-400">₹{((m.max_amount_paise || 0) / 100).toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">Daily Budget</span>
                      <span className="text-base font-extrabold text-blue-400">₹{((m.daily_budget_paise || 0) / 100).toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">Expires</span>
                      <span className="text-sm font-mono text-slate-300">{m.expires_at ? new Date(m.expires_at).toLocaleDateString("en-IN") : "—"}</span>
                    </div>
                  </div>

                  {(m.allowed_categories?.length > 0 || m.allowed_merchants?.length > 0) && (
                    <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800/60">
                      {m.allowed_categories?.map((c) => (
                        <span key={c} className="text-[11px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded font-semibold">{c}</span>
                      ))}
                      {m.allowed_merchants?.map((merch) => (
                        <span key={merch} className="text-[11px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded font-mono">{merch}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
