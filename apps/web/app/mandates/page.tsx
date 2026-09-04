"use client";

import React, { useState, useEffect, useCallback } from "react";
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
    <div className="min-h-screen bg-[#040711] text-slate-100 font-sans pb-16">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 md:px-8 py-8 space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-white/[0.08]">
          <div>
            <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20 font-bold uppercase tracking-wider">
              POLICY MANAGEMENT
            </span>
            <h1 className="text-3xl font-extrabold text-white tracking-tight mt-1">BUYER MANDATES STUDIO</h1>
            <p className="text-xs text-slate-400 mt-0.5">Configure spending mandates, daily budget caps, category permissions & one-click revocation</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreate((v) => !v)}
              className="text-xs font-bold bg-amber-500 hover:bg-amber-400 text-black px-4 py-2.5 rounded-xl transition shadow-lg shadow-amber-500/20 hover:scale-[1.02]"
            >
              + New Mandate
            </button>
            <button onClick={fetchMandates} className="text-xs font-bold text-slate-300 hover:text-white bg-[#090d1a] border border-white/[0.08] px-3.5 py-2.5 rounded-xl hover:border-white/[0.2] transition">
              ↻ Refresh
            </button>
          </div>
        </div>

        {/* Create Mandate Form */}
        {showCreate && (
          <section className="glass-card p-6 rounded-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
              Create New Mandate Rule
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: "Buyer ID", key: "buyer_id" },
                { label: "Merchant Scope", key: "merchant_id" },
                { label: "Allowed Categories", key: "allowed_categories" },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">{label}</label>
                  <input
                    type="text"
                    value={(form as any)[key]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="w-full glass-input text-white px-3 py-2 rounded-xl text-xs font-mono focus:outline-none"
                  />
                </div>
              ))}
              {[
                { label: "Single Purchase Cap (₹)", key: "max_amount_inr" },
                { label: "Daily Budget (₹)", key: "daily_budget_inr" },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">{label}</label>
                  <input
                    type="number"
                    value={(form as any)[key]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="w-full glass-input text-white px-3 py-2 rounded-xl text-xs font-mono focus:outline-none"
                  />
                </div>
              ))}
              <div>
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Expires At</label>
                <input
                  type="date"
                  value={form.expires_at}
                  onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))}
                  className="w-full glass-input text-white px-3 py-2 rounded-xl text-xs font-mono focus:outline-none"
                />
              </div>
            </div>
            <div className="flex items-center gap-4 pt-2">
              <button
                onClick={handleCreate}
                disabled={creating}
                className="bg-amber-500 hover:bg-amber-400 text-black font-bold px-6 py-2.5 rounded-xl text-sm transition disabled:opacity-50 hover:scale-[1.02]"
              >
                {creating ? "Creating..." : "⚡ Create & Activate Mandate"}
              </button>
              <button onClick={() => setShowCreate(false)} className="text-xs font-semibold text-slate-400 hover:text-white">Cancel</button>
              {createMsg && <span className={`text-xs font-bold ${createMsg.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>{createMsg}</span>}
            </div>
          </section>
        )}

        {/* Mandates List */}
        {loading ? (
          <div className="py-16 text-center">
            <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-300">Loading mandate policy ledger...</p>
          </div>
        ) : error && mandates.length === 0 ? (
          <div className="py-12 text-center glass-card rounded-2xl border-dashed">
            <p className="text-sm text-slate-400">{error}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {mandates.map((m) => {
              const maxInr = (m.max_amount_paise / 100).toLocaleString();
              const dailyInr = (m.daily_budget_paise / 100).toLocaleString();
              const usedInr = ((m.used_today_paise || 0) / 100).toLocaleString();
              const isRevoking = revoking === m.mandate_id;

              return (
                <div key={m.mandate_id} className="glass-panel p-6 rounded-2xl space-y-4 hover:border-white/[0.2] transition-all duration-300">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] font-mono text-slate-400 block mb-0.5">MANDATE ID</span>
                      <h3 className="font-mono font-bold text-base text-white">{m.mandate_id}</h3>
                    </div>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${statusColor(m.status)}`}>
                      {m.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-white/[0.08]">
                    <div className="bg-[#080d18] border border-white/[0.06] p-3 rounded-xl">
                      <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Single-Tx Cap</span>
                      <span className="font-mono font-extrabold text-amber-400 text-sm">₹{maxInr}</span>
                    </div>
                    <div className="bg-[#080d18] border border-white/[0.06] p-3 rounded-xl">
                      <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Daily Budget</span>
                      <span className="font-mono font-extrabold text-emerald-400 text-sm">₹{dailyInr}</span>
                      <span className="text-[10px] text-slate-500 block mt-0.5">Used today: ₹{usedInr}</span>
                    </div>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-400 font-medium">Buyer:</span>
                      <span className="font-mono text-slate-200">{m.buyer_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400 font-medium">Allowed Merchants:</span>
                      <span className="font-mono text-slate-200 truncate max-w-[200px]">
                        {m.allowed_merchants ? m.allowed_merchants.join(", ") : "ALL"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400 font-medium">Allowed Categories:</span>
                      <span className="font-mono text-slate-200 truncate max-w-[200px]">
                        {m.allowed_categories ? m.allowed_categories.join(", ") : "all"}
                      </span>
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-400 pt-1">
                      <span>Expires:</span>
                      <span className="font-mono">{m.expires_at ? new Date(m.expires_at).toLocaleDateString("en-IN") : "Never"}</span>
                    </div>
                  </div>

                  {m.status === "ACTIVE" && (
                    <div className="pt-2 border-t border-white/[0.08] flex justify-end">
                      <button
                        onClick={() => handleRevoke(m.mandate_id)}
                        disabled={isRevoking}
                        className="text-xs font-bold bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 px-4 py-2 rounded-xl transition disabled:opacity-50"
                      >
                        {isRevoking ? "Revoking..." : "🚫 Instant Revoke Mandate"}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
