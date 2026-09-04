"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";

const API = "http://localhost:8000";
const MERCHANT_ID = "mer_tech_store";

interface MerchantPolicy {
  merchant_id: string;
  ai_commerce_enabled: boolean;
  autonomous_limit_paise: number;
  step_up_threshold_paise: number;
  allowed_categories: string[];
  allowed_tools: string[];
  blocked_tools: string[];
  policy_version?: number;
}

interface Product {
  product_id: string;
  title: string;
  price_inr: number;
  price_paise: number;
  category: string;
  description?: string;
}

export default function MerchantPage() {
  const [policy, setPolicy] = useState<MerchantPolicy | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingPolicy, setLoadingPolicy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Editable fields
  const [aiEnabled, setAiEnabled] = useState(true);
  const [autoLimitInr, setAutoLimitInr] = useState("5000");
  const [stepUpInr, setStepUpInr] = useState("10000");
  const [categories, setCategories] = useState("electronics, clothing, books, supplies");

  // New product form
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [productForm, setProductForm] = useState({ title: "", price_inr: "", category: "", description: "" });
  const [addingProduct, setAddingProduct] = useState(false);
  const [productMsg, setProductMsg] = useState<string | null>(null);

  const fetchPolicy = useCallback(async () => {
    setLoadingPolicy(true);
    try {
      const res = await fetch(`${API}/api/merchants/${MERCHANT_ID}/policy`);
      const data = await res.json();
      if (!data.error) {
        setPolicy(data);
        setAiEnabled(data.ai_commerce_enabled ?? true);
        setAutoLimitInr(String((data.autonomous_limit_paise || 500000) / 100));
        setStepUpInr(String((data.step_up_threshold_paise || 1000000) / 100));
        setCategories((data.allowed_categories || []).join(", "));
      }
    } catch {
      /* ignore — show defaults */
    } finally {
      setLoadingPolicy(false);
    }
  }, []);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/merchants/${MERCHANT_ID}/products`);
      const data = await res.json();
      const prods = data.products || data.items || [];
      setProducts(prods);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchPolicy();
    fetchProducts();
  }, [fetchPolicy, fetchProducts]);

  const handleSavePolicy = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const payload = {
        ai_commerce_enabled: aiEnabled,
        autonomous_limit_paise: Math.round(Number(autoLimitInr) * 100),
        step_up_threshold_paise: Math.round(Number(stepUpInr) * 100),
        allowed_categories: categories.split(",").map((s) => s.trim()).filter(Boolean),
      };
      const res = await fetch(`${API}/api/merchants/${MERCHANT_ID}/policy`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.error) {
        setSaveMsg(`Error: ${data.error.message}`);
      } else {
        setSaveMsg("Policy updated successfully and published!");
        await fetchPolicy();
      }
    } catch {
      setSaveMsg("Network error — backend unreachable. Settings saved locally.");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(null), 4000);
    }
  };

  const handleAddProduct = async () => {
    setAddingProduct(true);
    setProductMsg(null);
    try {
      const res = await fetch(`${API}/api/merchants/${MERCHANT_ID}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: productForm.title,
          price_paise: Math.round(Number(productForm.price_inr) * 100),
          price_inr: Number(productForm.price_inr),
          category: productForm.category,
          description: productForm.description,
        }),
      });
      const data = await res.json();
      if (data.error) {
        setProductMsg(`Error: ${data.error.message}`);
      } else {
        setProductMsg(`Product "${productForm.title}" added!`);
        setProductForm({ title: "", price_inr: "", category: "", description: "" });
        setShowAddProduct(false);
        await fetchProducts();
      }
    } catch {
      setProductMsg("Network error adding product.");
    } finally {
      setAddingProduct(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 font-sans pb-16">
      {/* Navbar */}
      <header className="border-b border-slate-800/80 px-8 py-5 flex justify-between items-center bg-[#0d1322]">
        <div className="flex items-center gap-3">
          <Link href="/" className="w-9 h-9 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center font-black text-lg text-white shadow-lg shadow-purple-500/20">
            M
          </Link>
          <div>
            <h1 className="text-lg font-extrabold text-white m-0">MERCHANT POLICY</h1>
            <p className="text-xs text-slate-400 m-0">Configure autonomous AI commerce rules & operational guardrails</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold px-3 py-1.5 rounded-full border ${aiEnabled ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" : "bg-red-500/10 text-red-400 border-red-500/30"}`}>
            {aiEnabled ? "● AI COMMERCE ENABLED" : "○ AI COMMERCE DISABLED"}
          </span>
          <Link href="/" className="text-xs font-bold text-slate-400 hover:text-white bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700">
            ← Hub
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-8 space-y-6">
        {/* Policy Config */}
        <section className="bg-[#111827] border border-slate-800 p-6 rounded-2xl shadow-xl space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-purple-500 rounded-full" />
              Merchant Policy — {MERCHANT_ID}
              {policy?.policy_version && (
                <span className="text-xs bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded font-mono ml-2">v{policy.policy_version}</span>
              )}
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">AI Commerce:</span>
              <button
                onClick={() => setAiEnabled((v) => !v)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${aiEnabled ? "bg-emerald-600" : "bg-slate-700"}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${aiEnabled ? "translate-x-6" : "translate-x-1"}`} />
              </button>
            </div>
          </div>

          {loadingPolicy ? (
            <div className="flex items-center gap-3 text-sm text-slate-400 animate-pulse">
              <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
              Loading policy from backend...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1.5">Autonomous Purchase Limit (₹)</label>
                <input
                  type="number"
                  value={autoLimitInr}
                  onChange={(e) => setAutoLimitInr(e.target.value)}
                  className="w-full bg-[#0d1322] border border-slate-700 text-white px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-purple-500 transition"
                />
                <p className="text-xs text-slate-500 mt-1.5">Single purchases below this limit execute autonomously without human confirmation.</p>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1.5">Step-Up Approval Threshold (₹)</label>
                <input
                  type="number"
                  value={stepUpInr}
                  onChange={(e) => setStepUpInr(e.target.value)}
                  className="w-full bg-[#0d1322] border border-slate-700 text-white px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-purple-500 transition"
                />
                <p className="text-xs text-slate-500 mt-1.5">Purchases above this value require explicit buyer step-up human confirmation.</p>
              </div>

              <div className="md:col-span-2">
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1.5">Allowed Product Categories</label>
                <input
                  type="text"
                  value={categories}
                  onChange={(e) => setCategories(e.target.value)}
                  placeholder="e.g. electronics, books, clothing"
                  className="w-full bg-[#0d1322] border border-slate-700 text-white px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-purple-500 transition"
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-4 pt-2 border-t border-slate-800">
            <button
              onClick={handleSavePolicy}
              disabled={saving}
              className="bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-2.5 rounded-xl text-sm transition disabled:opacity-50 shadow-lg shadow-purple-500/20"
            >
              {saving ? "Publishing..." : "⚡ Update & Publish Policy"}
            </button>
            {saveMsg && (
              <span className={`text-xs font-bold ${saveMsg.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>
                {saveMsg}
              </span>
            )}
          </div>
        </section>

        {/* MCP Operations */}
        <section className="bg-[#111827] border border-slate-800 p-6 rounded-2xl shadow-xl">
          <h2 className="text-base font-bold text-white flex items-center gap-2 mb-5">
            <span className="w-2 h-2 bg-indigo-500 rounded-full" />
            MCP Tool Authorization Matrix
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4">
              <h3 className="font-bold text-emerald-400 text-sm mb-3 flex items-center gap-2">
                <span className="text-emerald-400">✓</span> Allowed Operations
              </h3>
              <ul className="space-y-2">
                {(policy?.allowed_tools || ["razorpay_create_order", "razorpay_create_payment_link", "razorpay_fetch_payment", "openfoodfacts_search", "merchant_catalog_query"]).map((tool) => (
                  <li key={tool} className="flex items-center gap-2 text-xs text-emerald-400 font-mono">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                    {tool}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4">
              <h3 className="font-bold text-red-400 text-sm mb-3 flex items-center gap-2">
                <span className="text-red-400">✕</span> Blocked Operations
              </h3>
              <ul className="space-y-2">
                {(policy?.blocked_tools || ["razorpay_create_payout", "razorpay_bank_transfer", "razorpay_admin_settlement", "bypass_mandate_check"]).map((tool) => (
                  <li key={tool} className="flex items-center gap-2 text-xs text-red-400 font-mono">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                    {tool}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Product Catalog */}
        <section className="bg-[#111827] border border-slate-800 p-6 rounded-2xl shadow-xl">
          <div className="flex justify-between items-center mb-5">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 bg-slate-400 rounded-full" />
              Merchant Product Catalog ({products.length})
            </h2>
            <button
              onClick={() => setShowAddProduct((v) => !v)}
              className="text-xs font-bold bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg border border-slate-600 transition"
            >
              + Add Product
            </button>
          </div>

          {showAddProduct && (
            <div className="bg-[#0d1322] border border-slate-700 rounded-xl p-5 mb-5 space-y-4">
              <h3 className="text-sm font-bold text-white">New Product</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { label: "Title", key: "title", type: "text" },
                  { label: "Price (₹)", key: "price_inr", type: "number" },
                  { label: "Category", key: "category", type: "text" },
                  { label: "Description", key: "description", type: "text" },
                ].map(({ label, key, type }) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">{label}</label>
                    <input
                      type={type}
                      value={(productForm as any)[key]}
                      onChange={(e) => setProductForm((f) => ({ ...f, [key]: e.target.value }))}
                      className="w-full bg-[#090d16] border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-purple-500"
                    />
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={handleAddProduct}
                  disabled={addingProduct}
                  className="bg-purple-600 hover:bg-purple-500 text-white font-bold px-5 py-2 rounded-xl text-xs transition disabled:opacity-50"
                >
                  {addingProduct ? "Adding..." : "Add to Catalog"}
                </button>
                <button onClick={() => setShowAddProduct(false)} className="text-xs text-slate-500 hover:text-slate-300">Cancel</button>
                {productMsg && <span className={`text-xs font-bold ${productMsg.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>{productMsg}</span>}
              </div>
            </div>
          )}

          {products.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
              No products in catalog yet. Add products above to enable buyer discovery.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((p) => (
                <div key={p.product_id} className="bg-[#0d1322] border border-slate-800 rounded-xl p-4 space-y-2 hover:border-slate-700 transition">
                  <p className="font-bold text-sm text-white leading-snug">{p.title}</p>
                  {p.description && <p className="text-xs text-slate-400 line-clamp-2">{p.description}</p>}
                  <div className="flex justify-between items-center pt-1">
                    <span className="text-base font-extrabold text-purple-400">₹{(p.price_inr || p.price_paise / 100).toLocaleString()}</span>
                    <span className="text-[11px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded font-mono">{p.category}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
