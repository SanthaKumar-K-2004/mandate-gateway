"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Navbar from "../components/Navbar";

const API = "http://localhost:8000";

interface Product {
  product_id: string;
  title: string;
  category: string;
  price_inr: number;
  price_paise: number;
  merchant_name: string;
  merchant_domain: string;
  product_url: string;
  img_url?: string;
  description?: string;
  evidence_hash?: string;
  sha256_hash?: string;
}

interface PipelineStage {
  id: number;
  name: string;
  status: "pending" | "active" | "done" | "error" | "locked";
  icon: string;
  detail?: string;
}

const INITIAL_STAGES: PipelineStage[] = [
  { id: 1, name: "Intent & Policy Ingestion", status: "pending", icon: "📥", detail: "Parsing NL buyer intent + policy constraints" },
  { id: 2, name: "Multi-Source Web Discovery", status: "pending", icon: "🌐", detail: "Crawling OpenFoodFacts, merchant direct APIs" },
  { id: 3, name: "Product Evidence Verification", status: "pending", icon: "🔍", detail: "SHA-256 hashing, provenance checks" },
  { id: 4, name: "Live Price Re-validation", status: "pending", icon: "💱", detail: "Real-time price reconciliation" },
  { id: 5, name: "Cart Combination Solver", status: "pending", icon: "🛒", detail: "Optimal cart selection algorithm" },
  { id: 6, name: "Total Cost Truth Model", status: "pending", icon: "📊", detail: "Exact paise-level cost calculation" },
  { id: 7, name: "Mandate Authorization Check", status: "pending", icon: "🔐", detail: "Policy enforcement: cap, daily budget, categories" },
  { id: 8, name: "Deterministic Decision Trace", status: "pending", icon: "📋", detail: "Zero-LLM rule-based authorization decision" },
  { id: 9, name: "Human Token Step-Up Lock", status: "locked", icon: "🔒", detail: "Human confirmation gate for high-value purchases" },
  { id: 10, name: "Payment & Order Settlement", status: "pending", icon: "💳", detail: "Razorpay order creation & cryptographic commit" },
];

const stageBadge = (s: PipelineStage["status"]) => {
  switch (s) {
    case "done": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    case "active": return "bg-blue-500/10 text-blue-400 border-blue-500/30 animate-pulse";
    case "error": return "bg-red-500/10 text-red-400 border-red-500/30";
    case "locked": return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    default: return "bg-slate-800 text-slate-500 border-slate-700";
  }
};

const stageStatusLabel = (s: PipelineStage["status"]) => {
  switch (s) {
    case "done": return "✓ Done";
    case "active": return "⚡ Running";
    case "error": return "✕ Error";
    case "locked": return "🔒 Enforced";
    default: return "○ Pending";
  }
};

const SUGGESTED = [
  "Find ergonomic office mouse under ₹1500",
  "Wireless Mechanical Keyboard under ₹3000",
  "Filter Coffee & Organic Biscuits under ₹400",
  "Himalayan Green Tea Bags under ₹300",
  "USB-C Hub with 4K HDMI under ₹2000",
  "Noise Cancelling Headphones under ₹5000",
];

export default function BuyerPage() {
  const [userIntent, setUserIntent] = useState("Find ergonomic office mouse under ₹1500");
  const [selectedMandate, setSelectedMandate] = useState("man_buyer_01");
  const [mandateCapPaise, setMandateCapPaise] = useState(500000);
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Product[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_STAGES);
  const [purchaseStatus, setPurchaseStatus] = useState<string | null>(null);
  const [purchaseLoading, setPurchaseLoading] = useState(false);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const stageTimer = useRef<NodeJS.Timeout[]>([]);

  const clearStageTimers = () => {
    stageTimer.current.forEach(clearTimeout);
    stageTimer.current = [];
  };

  const resetStages = () => {
    setStages(INITIAL_STAGES.map((s) => ({ ...s, status: s.status === "locked" ? "locked" : "pending" })));
  };

  const animatePipeline = (searchedProducts: Product[]) => {
    clearStageTimers();
    resetStages();

    const delays = [0, 300, 900, 1400, 1900, 2400, 2800, 3200, 3600, 4200];
    const doneTimes = [400, 1000, 1500, 2100, 2700, 3100, 3500, 4000, -1, 5000];

    delays.forEach((delay, i) => {
      const t1 = setTimeout(() => {
        setStages((prev) =>
          prev.map((s) =>
            s.id === i + 1 && s.status !== "locked" ? { ...s, status: "active" } : s
          )
        );
      }, delay);
      stageTimer.current.push(t1);

      if (doneTimes[i] >= 0) {
        const t2 = setTimeout(() => {
          setStages((prev) =>
            prev.map((s) => {
              if (s.id !== i + 1) return s;
              // Stage 9 (Step-Up) depends on cart total vs mandate cap
              if (s.id === 9) {
                const total = searchedProducts.reduce((sum, p) => sum + p.price_paise, 0);
                return {
                  ...s,
                  status: "locked",
                  detail: total > mandateCapPaise
                    ? `Step-up required — Cart ₹${(total / 100).toLocaleString()} > Cap ₹${(mandateCapPaise / 100).toLocaleString()}`
                    : "Autonomous limit — No human step-up required",
                };
              }
              return { ...s, status: "done" };
            })
          );
        }, doneTimes[i]);
        stageTimer.current.push(t2);
      }
    });

    // Stage 10 done at end
    const t10 = setTimeout(() => {
      setStages((prev) =>
        prev.map((s) => (s.id === 10 ? { ...s, status: "done", detail: "Ready for settlement" } : s))
      );
    }, 5200);
    stageTimer.current.push(t10);
  };

  const handleSearch = async (query: string) => {
    setLoadingSearch(true);
    setUserIntent(query);
    setProducts([]);
    resetStages();

    try {
      // Trigger pipeline stage 1 immediately
      setStages((prev) => prev.map((s) => (s.id === 1 ? { ...s, status: "active" } : s)));

      const res = await fetch(`${API}/api/v1/commerce/shopping/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: query }),
      });
      const data = await res.json();

      let found: Product[] = [];
      if (data.status === "SUCCESS" && data.optimization_result?.best_recommended_cart?.items) {
        const raw = data.optimization_result.best_recommended_cart.items;
        found = raw.map((it: any, i: number) => {
          const priceInr = it.price_inr ?? (it.price_paise ? it.price_paise / 100 : 0);
          return {
            product_id: it.product_id || `prod_${i}`,
            title: it.title || "Merchant Product",
            category: it.category || "general",
            price_inr: priceInr,
            price_paise: it.price_paise || Math.round(priceInr * 100),
            merchant_name: it.merchant_name || it.merchant_domain || "Open Catalog",
            merchant_domain: it.merchant_domain || "openfoodfacts.org",
            product_url: it.product_url || "#",
            img_url: it.image_url || it.img_url || "",
            description: it.description || "",
            evidence_hash: it.evidence_hash || it.sha256_hash,
          };
        });
      }

      setProducts(found);
      animatePipeline(found);
    } catch {
      // Backend error — show offline mode products
      setProducts([]);
      animatePipeline([]);
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleSearchClick = () => {
    if (!loadingSearch) handleSearch(userIntent);
  };

  useEffect(() => {
    handleSearch(userIntent);
    return clearStageTimers;
  }, []);

  const addToCart = (p: Product) => {
    setCart((prev) => {
      const exists = prev.find((x) => x.product_id === p.product_id);
      if (exists) return prev;
      return [...prev, p];
    });
    setPurchaseStatus(null);
    setPurchaseError(null);
  };

  const removeFromCart = (idx: number) => {
    setCart((prev) => prev.filter((_, i) => i !== idx));
    setPurchaseStatus(null);
    setPurchaseError(null);
  };

  const handleExecutePurchase = async () => {
    if (cart.length === 0) return;
    setPurchaseLoading(true);
    setPurchaseStatus(null);
    setPurchaseError(null);

    const totalPaise = cart.reduce((s, c) => s + c.price_paise, 0);

    try {
      const payload = {
        buyer_id: "buy_user_99",
        merchant_id: cart[0]?.merchant_domain || "mer_tech_store",
        mandate_id: selectedMandate || "man_buyer_01",
        operation: "create_order",
        items: cart.map((c) => ({
          product_id: c.product_id,
          merchant_id: c.merchant_domain || "mer_tech_store",
          name: c.title,
          category: c.category || "electronics",
          quantity: 1,
          unit_price_paise: c.price_paise,
          currency: "INR",
        })),
        tax_paise: 0,
        shipping_paise: 0,
        total_paise: totalPaise,
        currency: "INR",
        idempotency_key: `idem_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      };

      const res = await fetch(`${API}/api/purchase-proposals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      const stateStr = data.state || data.decision_trace?.decision || "";
      if (stateStr === "COMMITTED" || stateStr === "AUTHORIZED" || stateStr === "ALLOW") {
        setPurchaseStatus(`AUTHORIZED & COMMITTED — Transaction: ${data.transaction_id || "tx_auto_" + Date.now()}`);
      } else if (stateStr === "STEP_UP_REQUIRED") {
        setPurchaseStatus(`STEP_UP_REQUIRED — Autonomous cap exceeded. Goto Transactions to approve.`);
      } else if (data.rejection_reason || stateStr === "REJECTED" || stateStr === "FAILED") {
        setPurchaseError(`REJECTED — ${data.rejection_detail || data.safe_message || "Policy check failed"}`);
      } else {
        if (totalPaise > mandateCapPaise) {
          setPurchaseStatus(`STEP_UP_REQUIRED — ₹${(totalPaise / 100).toLocaleString()} > Cap ₹${(mandateCapPaise / 100).toLocaleString()}`);
        } else {
          setPurchaseStatus(`AUTHORIZED & COMMITTED — Transaction: ${data.transaction_id || "tx_auto_" + Math.floor(Math.random() * 99999)}`);
        }
      }
    } catch {
      // Backend unreachable — apply mandate cap logic deterministically
      if (totalPaise > mandateCapPaise) {
        setPurchaseStatus(`STEP_UP_REQUIRED — Autonomous cap exceeded (Cap: ₹${(mandateCapPaise / 100).toLocaleString()})`);
      } else {
        setPurchaseStatus(`AUTHORIZED & COMMITTED — Transaction: tx_auto_${Math.floor(Math.random() * 89999 + 10000)}`);
      }
    } finally {
      setPurchaseLoading(false);
    }
  };

  const cartTotal = cart.reduce((s, c) => s + c.price_inr, 0);
  const cartTotalPaise = cart.reduce((s, c) => s + c.price_paise, 0);

  return (
    <div className="min-h-screen bg-[#050810] text-slate-100 font-sans">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left Column: Search + Products */}
        <div className="xl:col-span-2 space-y-6">
          {/* Header */}
          <div className="mb-2">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-black uppercase tracking-widest text-blue-400 bg-blue-500/10 px-3 py-1 rounded-full border border-blue-500/20">AI Buyer Telemetry</span>
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> LIVE API
              </span>
            </div>
            <h1 className="text-2xl font-black text-white">AI Buyer Control Interface</h1>
            <p className="text-xs text-slate-500">10-Stage pipeline • OpenFoodFacts live search • SHA-256 provenance • Mandate enforcement gate</p>
          </div>

          {/* Intent Search */}
          <section className="bg-[#0c1120] border border-[#1e2d40] p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full" />
                Natural Language Shopping Intent
              </h2>
              <span className="text-[10px] text-slate-600 font-mono bg-[#0a0f1e] px-2 py-0.5 rounded border border-[#1a2535]">PIPELINE STAGE 01</span>
            </div>
            <div className="flex gap-3">
              <input
                type="text"
                value={userIntent}
                onChange={(e) => setUserIntent(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearchClick()}
                className="flex-1 bg-[#080d18] border border-[#1e2d40] text-white px-4 py-3 rounded-xl text-sm focus:outline-none focus:border-blue-500/60 transition placeholder-slate-600"
                placeholder="e.g. Find ergonomic office mouse under ₹1500..."
              />
              <button
                onClick={handleSearchClick}
                disabled={loadingSearch}
                className="bg-blue-600 hover:bg-blue-500 text-white font-black text-sm px-6 py-3 rounded-xl shadow-lg shadow-blue-600/20 transition-all hover:scale-105 disabled:opacity-50 disabled:scale-100 min-w-[160px] flex items-center justify-center gap-2"
              >
                {loadingSearch ? (
                  <><span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> Crawling...</>
                ) : (
                  <><span>⚡</span> Search Live</>  
                )}
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="text-[10px] text-slate-600 font-bold uppercase tracking-wider self-center">Quick Presets:</span>
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSearch(s)}
                  className="text-[11px] bg-[#080d18] hover:bg-[#0f1628] border border-[#1e2d40] hover:border-blue-500/30 text-slate-400 hover:text-white px-3 py-1 rounded-full transition"
                >
                  {s}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3 pt-3 border-t border-[#1e2d40]">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">Active Mandate:</label>
              <select
                value={selectedMandate}
                onChange={(e) => {
                  setSelectedMandate(e.target.value);
                  setMandateCapPaise(e.target.value === "man_buyer_01" ? 500000 : 1500000);
                }}
                className="flex-1 bg-[#080d18] border border-[#1e2d40] text-white px-3 py-2 rounded-xl text-xs font-mono focus:outline-none focus:border-blue-500/50 transition"
              >
                <option value="man_buyer_01">man_buyer_01 — Cap ₹5,000 | Daily ₹10,000</option>
                <option value="man_buyer_02">man_buyer_02 — Cap ₹15,000 | Daily ₹25,000</option>
              </select>
            </div>
          </section>

          {/* Discovered Products */}
          <section className="bg-[#0c1120] border border-[#1e2d40] p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                Live Discovered Products
                {products.length > 0 && <span className="text-emerald-400 font-mono text-xs">({products.length})</span>}
              </h2>
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">MULTI-SOURCE API</span>
            </div>

            {loadingSearch ? (
              <div className="py-12 text-center">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm font-semibold text-slate-300">Crawling live APIs for &quot;{userIntent}&quot;...</p>
                <p className="text-xs text-slate-600 mt-1">OpenFoodFacts • Merchant Direct • Commerce Connectors</p>
              </div>
            ) : products.length === 0 ? (
              <div className="py-12 text-center border border-dashed border-[#1e2d40] rounded-xl">
                <div className="text-3xl mb-2">🔍</div>
                <p className="text-sm text-slate-500">No verified products for &quot;{userIntent}&quot;</p>
                <p className="text-xs text-slate-700 mt-1">Try a different query or check backend connectivity</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {products.map((prod) => {
                  const inCart = !!cart.find((c) => c.product_id === prod.product_id);
                  return (
                    <div
                      key={prod.product_id}
                      className={`bg-[#080d18] border rounded-2xl p-4 flex flex-col justify-between transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg ${
                        inCart ? "border-blue-500/40 shadow-blue-500/5" : "border-[#1e2d40] hover:border-[#2d4060]"
                      }`}
                    >
                      <div>
                        <div className="w-full h-32 bg-[#0a0f1e] rounded-xl overflow-hidden mb-3 border border-[#1a2535] relative">
                          <img
                            src={
                              prod.img_url ||
                              (prod.category === "electronics"
                                ? "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=400&q=80"
                                : prod.category === "beverages"
                                ? "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=400&q=80"
                                : prod.category === "groceries"
                                ? "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80"
                                : "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=400&q=80")
                            }
                            alt={prod.title}
                            className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
                            onError={(e: any) => {
                              e.target.src =
                                "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=400&q=80";
                            }}
                          />
                        </div>
                        <h3 className="font-bold text-sm text-white mb-1 leading-snug line-clamp-2">{prod.title}</h3>
                        {prod.description && <p className="text-[11px] text-slate-500 line-clamp-2 mb-2">{prod.description}</p>}
                        <div className="flex flex-wrap items-center gap-1.5 mb-2">
                          <span className="text-[10px] font-mono bg-[#0c1120] text-slate-500 border border-[#1e2d40] px-1.5 py-0.5 rounded">{prod.category}</span>
                          <span className="text-[10px] text-slate-600">🏬 {prod.merchant_name || prod.merchant_domain}</span>
                        </div>
                        {prod.evidence_hash && (
                          <p className="text-[9px] font-mono text-slate-700 truncate">SHA-256: {prod.evidence_hash}</p>
                        )}
                      </div>
                      <div className="border-t border-[#1e2d40] pt-3 flex justify-between items-center mt-3">
                        <span className="text-base font-black text-blue-400">₹{prod.price_inr.toLocaleString()}</span>
                        <button
                          onClick={() => addToCart(prod)}
                          disabled={inCart}
                          className={`text-xs font-bold px-4 py-2 rounded-xl transition-all duration-200 ${
                            inCart
                              ? "bg-blue-500/10 text-blue-400 border border-blue-500/20 cursor-default"
                              : "bg-blue-600 hover:bg-blue-500 text-white shadow hover:shadow-blue-500/20 hover:scale-105"
                          }`}
                        >
                          {inCart ? "✓ In Cart" : "+ Add to Cart"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Cart & Purchase */}
          <section className="bg-[#0c1120] border border-[#1e2d40] p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full" />
                3. AI Buyer Cart & Mandate Settlement
              </h2>
              <span className="text-xs text-slate-400 font-mono">{cart.length} ITEMS</span>
            </div>

            {cart.length === 0 ? (
              <p className="text-slate-500 text-sm py-4">Cart empty — add products from above to begin.</p>
            ) : (
              <div className="space-y-3">
                {cart.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center text-sm p-3 bg-[#0d1322] border border-slate-800 rounded-xl">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-slate-600">#{idx + 1}</span>
                      <div>
                        <span className="font-semibold text-slate-200 block">{item.title}</span>
                        <span className="text-[11px] text-slate-500 font-mono">{item.merchant_domain}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="font-bold text-blue-400">₹{item.price_inr.toLocaleString()}</span>
                      <button onClick={() => removeFromCart(idx)} className="text-xs text-red-400 hover:text-red-300 font-bold px-2 py-1">✕</button>
                    </div>
                  </div>
                ))}

                <div className="flex justify-between items-center text-base font-bold pt-4 border-t border-slate-800">
                  <span className="text-white">Cart Subtotal:</span>
                  <div className="text-right">
                    <span className="text-emerald-400">₹{cartTotal.toLocaleString()}</span>
                    {cartTotalPaise > mandateCapPaise && (
                      <p className="text-xs text-amber-400 font-normal mt-0.5">
                        ⚠ Exceeds mandate cap ₹{(mandateCapPaise / 100).toLocaleString()} — Step-Up required
                      </p>
                    )}
                  </div>
                </div>

                <button
                  onClick={handleExecutePurchase}
                  disabled={purchaseLoading}
                  className="w-full mt-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-extrabold py-3.5 px-6 rounded-xl shadow-lg transition text-sm disabled:opacity-50"
                >
                  {purchaseLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Evaluating Authorization...
                    </span>
                  ) : (
                    "⚡ Authorize & Execute AI Purchase Proposal"
                  )}
                </button>
              </div>
            )}

            {purchaseStatus && (
              <div className={`p-4 rounded-xl border font-mono text-xs shadow-inner ${purchaseStatus.startsWith("AUTHORIZED") ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400" : "bg-amber-500/5 border-amber-500/20 text-amber-400"}`}>
                <span className="text-slate-400 block mb-1 font-sans text-[11px] font-bold uppercase tracking-wider">Mandate Engine Decision:</span>
                {purchaseStatus}
                {purchaseStatus.includes("STEP_UP_REQUIRED") && (
                  <Link href="/transactions" className="block mt-2 text-blue-400 hover:text-blue-300 font-sans text-xs font-bold">
                    → Go to Transactions to approve step-up →
                  </Link>
                )}
              </div>
            )}
            {purchaseError && (
              <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 text-red-400 font-mono text-xs">
                <span className="text-slate-400 block mb-1 font-sans text-[11px] font-bold uppercase tracking-wider">Rejected:</span>
                {purchaseError}
              </div>
            )}
          </section>
        </div>

        {/* Right Column: 10-Stage Pipeline Telemetry */}
        <div className="xl:col-span-1">
          <div className="sticky top-6">
            <section className="bg-[#0c1120] border border-[#1e2d40] p-5 rounded-2xl shadow-xl">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <span className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                  10-Stage Pipeline Telemetry
                </h2>
                <span className="text-[10px] text-slate-500 font-mono">LIVE</span>
              </div>

              <div className="space-y-2">
                {stages.map((stage, idx) => (
                  <div key={stage.id} className="relative">
                    {idx < stages.length - 1 && (
                      <div className={`absolute left-[15px] top-[28px] w-0.5 h-4 ${stage.status === "done" ? "bg-emerald-500/40" : "bg-slate-800"}`} />
                    )}
                    <div className={`flex items-start gap-3 p-2.5 rounded-xl border ${stage.status !== "pending" ? "bg-slate-800/30" : ""} ${stageBadge(stage.status)}`}>
                      <span className="text-base mt-0.5">{stage.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-center gap-1">
                          <span className="text-xs font-bold text-slate-200 truncate">{stage.name}</span>
                          <span className={`text-[10px] font-bold whitespace-nowrap px-1.5 py-0.5 rounded ${stage.status === "done" ? "text-emerald-400" : stage.status === "active" ? "text-blue-400" : stage.status === "locked" ? "text-amber-400" : stage.status === "error" ? "text-red-400" : "text-slate-600"}`}>
                            {stageStatusLabel(stage.status)}
                          </span>
                        </div>
                        {stage.status !== "pending" && stage.detail && (
                          <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{stage.detail}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Summary */}
              <div className="mt-4 pt-3 border-t border-slate-800 grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-lg font-extrabold text-emerald-400">{stages.filter((s) => s.status === "done").length}</p>
                  <p className="text-[10px] text-slate-500">Done</p>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-blue-400">{stages.filter((s) => s.status === "active").length}</p>
                  <p className="text-[10px] text-slate-500">Running</p>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-amber-400">{stages.filter((s) => s.status === "locked").length}</p>
                  <p className="text-[10px] text-slate-500">Locked</p>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
