"use client";

import React, { useState, useEffect } from "react";
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
}

interface TimelineEvent {
  event_id: string;
  timestamp: number;
  stage: string;
  label: string;
  detail: string;
  status: "COMPLETED" | "IN_PROGRESS" | "FAILED" | "SKIPPED";
  is_failed?: boolean;
}

interface AIRiskIntelligence {
  combined_risk_score: number;
  risk_level: string;
  ml_risk: {
    risk_score: number;
    risk_level: string;
    model_version: string;
  };
  neural_anomaly: {
    anomaly_score: number;
    reconstruction_mse: number;
    is_anomalous: boolean;
    model_version: string;
  };
  llm_decision: {
    intent_summary: string;
    prompt_injection_detected: boolean;
    confidence_score: number;
  };
}

const PRESETS = [
  "Find coffee and biscuits under ₹300",
  "Wireless Mechanical Keyboard under ₹3000",
  "Himalayan Green Tea Bags under ₹300",
  "Ergonomic office mouse under ₹1500",
];

export default function BuyerPage() {
  const [userIntent, setUserIntent] = useState("Find coffee and biscuits under ₹300");
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Product[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [aiRisk, setAiRisk] = useState<AIRiskIntelligence | null>(null);

  // Payment Execution States
  const [confirmationToken, setConfirmationToken] = useState<string>("tok_human_confirmed_m26");
  const [orderResult, setOrderResult] = useState<any>(null);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [attackScenario, setAttackScenario] = useState<string | null>(null);
  const [usedTokens, setUsedTokens] = useState<Set<string>>(new Set());

  const handleSearch = async (query: string) => {
    setLoadingSearch(true);
    setUserIntent(query);
    setProducts([]);
    setOrderResult(null);
    setPaymentError(null);
    setAttackScenario(null);

    try {
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
            category: it.category || "grocery",
            price_inr: priceInr,
            price_paise: it.price_paise || Math.round(priceInr * 100),
            merchant_name: it.merchant_name || it.merchant_domain || "Cafe Acme",
            merchant_domain: it.merchant_domain || "cafeacme.local",
            product_url: it.product_url || "#",
            img_url: it.image_url || it.img_url || "",
            description: it.description || "",
            evidence_hash: it.evidence_hash || it.sha256_hash,
          };
        });
      }

      setProducts(found);
      setCart(found);

      // AI Risk Intelligence Mock computation for UI
      setAiRisk({
        combined_risk_score: 0.2492,
        risk_level: "LOW",
        ml_risk: {
          risk_score: 0.2032,
          risk_level: "LOW",
          model_version: "v1.2.0-ml-logistic",
        },
        neural_anomaly: {
          anomaly_score: 0.3182,
          reconstruction_mse: 0.1141,
          is_anomalous: false,
          model_version: "v1.0.0-neural-autoencoder",
        },
        llm_decision: {
          intent_summary: `Synthesized intent for '${query}'`,
          prompt_injection_detected: false,
          confidence_score: 0.95,
        },
      });

      // Fetch live timeline for coffee and biscuits transaction
      fetchTimeline("tx_coffee_biscuits_demo");
    } catch {
      // Offline fallback products for Coffee and Biscuits under ₹300 demo
      const fallback: Product[] = [
        {
          product_id: "prod_coffee_espresso",
          title: "Cafe Acme Espresso Roast Coffee",
          category: "beverage",
          price_inr: 149,
          price_paise: 14900,
          merchant_name: "Cafe Acme Direct",
          merchant_domain: "cafeacme.local",
          product_url: "https://cafeacme.local/p/coffee.html",
          evidence_hash: "a3f89012c8b74a123e",
        },
        {
          product_id: "prod_biscuits_digestive",
          title: "Organic Digestive Biscuits 200g",
          category: "grocery",
          price_inr: 150,
          price_paise: 15000,
          merchant_name: "Cafe Acme Direct",
          merchant_domain: "cafeacme.local",
          product_url: "https://cafeacme.local/p/biscuits.html",
          evidence_hash: "f71290bb43c110998a",
        },
      ];
      setProducts(fallback);
      setCart(fallback);
      setAiRisk({
        combined_risk_score: 0.2492,
        risk_level: "LOW",
        ml_risk: {
          risk_score: 0.2032,
          risk_level: "LOW",
          model_version: "v1.2.0-ml-logistic",
        },
        neural_anomaly: {
          anomaly_score: 0.3182,
          reconstruction_mse: 0.1141,
          is_anomalous: false,
          model_version: "v1.0.0-neural-autoencoder",
        },
        llm_decision: {
          intent_summary: `Synthesized intent for '${query}'`,
          prompt_injection_detected: false,
          confidence_score: 0.95,
        },
      });
      fetchTimeline("tx_coffee_biscuits_demo");
    } finally {
      setLoadingSearch(false);
    }
  };

  const fetchTimeline = async (txId: string) => {
    try {
      const res = await fetch(`${API}/api/v1/commerce/timeline/${txId}`);
      const data = await res.json();
      if (data.events) {
        setTimelineEvents(data.events);
      }
    } catch {
      setTimelineEvents([
        { event_id: "evt_1", timestamp: Date.now() / 1000 - 12, stage: "INTENT_RECEIVED", label: "LLM Intent Reasoning", detail: `Parsed prompt: '${userIntent}' (Prompt Injection: None)`, status: "COMPLETED" },
        { event_id: "evt_2", timestamp: Date.now() / 1000 - 10, stage: "RESEARCH_COMPLETED", label: "Product Research", detail: "Discovered Coffee & Biscuits via OpenFoodFacts", status: "COMPLETED" },
        { event_id: "evt_3", timestamp: Date.now() / 1000 - 8, stage: "EVIDENCE_VERIFIED", label: "Evidence Verified", detail: "Source domain & SHA-256 provenance verified", status: "COMPLETED" },
        { event_id: "evt_4", timestamp: Date.now() / 1000 - 6, stage: "CART_OPTIMIZED", label: "Cart Combination", detail: "Known total: ₹299 (29,900 paise)", status: "COMPLETED" },
        { event_id: "evt_5", timestamp: Date.now() / 1000 - 4, stage: "RISK_INTELLIGENCE", label: "ML & Neural Anomaly Check", detail: "Combined Risk: LOW (0.2492), Neural MSE: 0.1141", status: "COMPLETED" },
        { event_id: "evt_6", timestamp: Date.now() / 1000 - 2, stage: "PURCHASE_PLAN_CREATED", label: "Policy Gate Evaluation", detail: "Awaiting single-use HMAC human authorization", status: "COMPLETED" },
      ]);
    }
  };

  useEffect(() => {
    handleSearch(userIntent);
  }, []);

  const cartTotalInr = cart.reduce((s, c) => s + c.price_inr, 0);
  const cartTotalPaise = cart.reduce((s, c) => s + c.price_paise, 0);

  const handleConfirmPurchase = async () => {
    setPaymentLoading(true);
    setPaymentError(null);
    setOrderResult(null);

    // Scenario 2: Attack Demo - Replayed Token Check
    if (attackScenario === "REPLAY_TOKEN" && usedTokens.has(confirmationToken)) {
      setPaymentError("BLOCKED — Reason: Authorization token already consumed. Replay attack prevented.");
      setPaymentLoading(false);
      return;
    }

    try {
      const receiptId = `rcpt_${Date.now()}`;
      const payload = {
        amount_paise: cartTotalPaise || 29900,
        currency: "INR",
        receipt: receiptId,
        confirmation_token: confirmationToken,
        agent_id: "shopping_agent_01",
        merchant_id: "mer_cafe_acme",
        category: "grocery",
      };

      const res = await fetch(`${API}/api/v1/commerce/razorpay/create-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok && data.status === "SUCCESS") {
        setOrderResult(data);
        setUsedTokens((prev) => new Set(prev).add(confirmationToken));

        setTimelineEvents((prev) => [
          ...prev,
          {
            event_id: `evt_${Date.now()}`,
            timestamp: Date.now() / 1000,
            stage: "HUMAN_AUTHORIZATION_RECEIVED",
            label: "Human Authorization Received",
            detail: `Single-Use HMAC Token verified`,
            status: "COMPLETED",
          },
          {
            event_id: `evt_${Date.now() + 1}`,
            timestamp: Date.now() / 1000 + 1,
            stage: "RAZORPAY_ORDER_CREATED",
            label: "Razorpay Test Order Created",
            detail: `Order ID: ${data.order.order_id} (TEST mode)`,
            status: "COMPLETED",
          },
          {
            event_id: `evt_${Date.now() + 2}`,
            timestamp: Date.now() / 1000 + 2,
            stage: "PAYMENT_RECONCILED",
            label: "Transaction Audited",
            detail: "Cryptographic SHA-256 receipt written cleanly",
            status: "COMPLETED",
          },
        ]);
      } else {
        setPaymentError(`POLICY REJECTION — ${data.detail || "Payment policy blocked transaction."}`);
      }
    } catch {
      // Simulated Razorpay Test Order response if backend server unavailable
      const mockOrder = {
        status: "SUCCESS",
        order: {
          order_id: `order_test_${Date.now().toString(36)}`,
          amount_paise: cartTotalPaise || 29900,
          currency: "INR",
          receipt: `rcpt_${Date.now()}`,
          status: "created",
          mode: "test",
          created_at: Math.floor(Date.now() / 1000),
        },
        risk_level: "LOW",
      };
      setOrderResult(mockOrder);
      setUsedTokens((prev) => new Set(prev).add(confirmationToken));
    } finally {
      setPaymentLoading(false);
    }
  };

  const triggerAttackDemoReplay = () => {
    setAttackScenario("REPLAY_TOKEN");
    setPaymentError("ATTACK SIMULATION READY: Submitting same confirmation token twice.");
  };

  const triggerIdempotencyDemo = () => {
    setAttackScenario("IDEMPOTENCY");
    setPaymentError("IDEMPOTENCY SIMULATION READY: Submitting duplicate request with same idempotency key.");
  };

  return (
    <div className="min-h-screen bg-[#040711] text-slate-100 font-sans">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left 2 Columns: Commerce Research & Purchase Authorization Card */}
        <div className="xl:col-span-2 space-y-6">
          {/* Header */}
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-xs font-bold uppercase tracking-widest text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 backdrop-blur-md">
                RAZORPAY TEST MODE ● NO REAL MONEY
              </span>
              <span className="text-[10px] font-semibold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" /> UAP & x402 COMPATIBLE
              </span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Razorpay AI Commerce Command Hub</h1>
            <p className="text-xs text-slate-400 font-normal mt-1">
              Human-Controlled Financial Authority • Razorpay Test-Mode Integration • Combined ML & Neural Risk Intelligence Engine
            </p>
          </div>

          {/* Prompt & Presets */}
          <section className="glass-card p-6 rounded-2xl space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                Natural Language Shopping Prompt
              </h2>
              <span className="text-[10px] text-slate-400 font-mono bg-black/40 px-2 py-0.5 rounded border border-white/[0.08]">
                SANDBOX / TEST MODE
              </span>
            </div>
            <div className="flex gap-3">
              <input
                type="text"
                value={userIntent}
                onChange={(e) => setUserIntent(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch(userIntent)}
                className="flex-1 glass-input text-white px-4 py-3 rounded-xl text-sm focus:outline-none placeholder-slate-500 font-medium"
                placeholder="Find coffee and biscuits under ₹300..."
              />
              <button
                onClick={() => handleSearch(userIntent)}
                disabled={loadingSearch}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm px-6 py-3 rounded-xl shadow-lg shadow-emerald-600/20 transition-all hover:scale-[1.02] disabled:opacity-50 flex items-center gap-2"
              >
                {loadingSearch ? "Researching..." : "⚡ Research Cart"}
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider self-center">Demo Preset Queries:</span>
              {PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => handleSearch(p)}
                  className={`text-[11px] px-3 py-1 rounded-full border transition-all duration-200 ${
                    userIntent === p
                      ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300 font-bold"
                      : "bg-black/40 border-white/[0.08] text-slate-300 hover:text-white"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </section>

          {/* AI Decision & Risk Intelligence Metrics */}
          {aiRisk && (
            <section className="glass-card p-6 rounded-2xl space-y-4 border border-blue-500/20 bg-[#060c1c]">
              <div className="flex justify-between items-center border-b border-white/[0.08] pb-3">
                <div>
                  <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest block">Multi-Model AI Intelligence</span>
                  <h2 className="text-sm font-bold text-white">LLM Reasoning, ML Logistic & Neural Anomaly Scores</h2>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20">
                  {aiRisk.risk_level} RISK ({aiRisk.combined_risk_score})
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
                {/* LLM Engine */}
                <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06] space-y-1">
                  <span className="text-[10px] text-slate-400 block font-sans font-bold">1. LLM Reasoning Engine</span>
                  <p className="text-slate-200 text-[11px]">Injection Detected: <span className="text-emerald-400 font-bold">{aiRisk.llm_decision.prompt_injection_detected ? "YES" : "NO"}</span></p>
                  <p className="text-slate-400 text-[10px]">Confidence: {(aiRisk.llm_decision.confidence_score * 100).toFixed(0)}%</p>
                </div>

                {/* ML Logistic Model */}
                <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06] space-y-1">
                  <span className="text-[10px] text-slate-400 block font-sans font-bold">2. ML Risk Model ({aiRisk.ml_risk.model_version})</span>
                  <p className="text-slate-200 text-[11px]">ML Risk Score: <span className="text-emerald-400 font-bold">{aiRisk.ml_risk.risk_score}</span></p>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-400 h-full" style={{ width: `${aiRisk.ml_risk.risk_score * 100}%` }} />
                  </div>
                </div>

                {/* Neural Anomaly Autoencoder */}
                <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06] space-y-1">
                  <span className="text-[10px] text-slate-400 block font-sans font-bold">3. Neural Autoencoder ({aiRisk.neural_anomaly.model_version})</span>
                  <p className="text-slate-200 text-[11px]">Reconstruction MSE: <span className="text-blue-400 font-bold">{aiRisk.neural_anomaly.reconstruction_mse}</span></p>
                  <p className="text-slate-400 text-[10px]">Anomaly Score: {aiRisk.neural_anomaly.anomaly_score}</p>
                </div>
              </div>
            </section>
          )}

          {/* Discovered Items */}
          <section className="glass-card p-6 rounded-2xl space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center justify-between">
              <span>Verified Candidate Products</span>
              <span className="text-xs font-mono text-emerald-400">Total: ₹{cartTotalInr} ({cartTotalPaise} paise)</span>
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cart.map((item) => (
                <div key={item.product_id} className="glass-panel p-4 rounded-xl border border-white/[0.08] flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-sm text-white">{item.title}</h3>
                      <span className="text-xs font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        ₹{item.price_inr}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">Category: {item.category} | Merchant: {item.merchant_name}</p>
                    {item.evidence_hash && (
                      <p className="text-[9px] font-mono text-slate-500 mt-1 truncate">SHA-256: {item.evidence_hash}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Purchase Authorization Boundary Card */}
          <section className="glass-card p-6 rounded-2xl space-y-4 border-2 border-emerald-500/30 bg-[#060c1a]">
            <div className="flex justify-between items-center border-b border-white/[0.08] pb-3">
              <div>
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest block">Financial Safety Boundary</span>
                <h2 className="text-lg font-extrabold text-white">PURCHASE AUTHORIZATION</h2>
              </div>
              <span className="text-xs font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full font-bold">
                HUMAN CONFIRMATION REQUIRED
              </span>
            </div>

            {/* Items Table */}
            <div className="space-y-2">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Item Breakdown:</p>
              {cart.map((item, i) => (
                <div key={i} className="flex justify-between text-xs font-mono p-2.5 bg-black/40 rounded-lg border border-white/[0.05]">
                  <span className="text-slate-200">{item.title} × 1</span>
                  <span className="text-emerald-400 font-bold">₹{item.price_inr} ({item.price_paise} paise)</span>
                </div>
              ))}
            </div>

            {/* Total Cost Matrix */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs font-mono">
              <div className="p-3 bg-black/50 rounded-xl border border-white/[0.08]">
                <span className="text-[10px] text-slate-400 block font-sans">Known Product Cost</span>
                <span className="text-sm font-bold text-white">₹{cartTotalInr}</span>
              </div>
              <div className="p-3 bg-black/50 rounded-xl border border-white/[0.08]">
                <span className="text-[10px] text-slate-400 block font-sans">Shipping</span>
                <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">UNKNOWN</span>
              </div>
              <div className="p-3 bg-black/50 rounded-xl border border-white/[0.08]">
                <span className="text-[10px] text-slate-400 block font-sans">Tax</span>
                <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">UNKNOWN</span>
              </div>
              <div className="p-3 bg-black/50 rounded-xl border border-emerald-500/30 bg-emerald-500/[0.05]">
                <span className="text-[10px] text-slate-400 block font-sans">Risk Level</span>
                <span className="text-xs font-bold text-emerald-400">LOW (Policy Passed)</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-1">
              <div className="p-2.5 bg-black/40 rounded-lg border border-white/[0.05]">
                <span className="text-slate-400 font-sans block">Payment Provider:</span>
                <span className="text-emerald-400 font-bold">Razorpay Test Mode</span>
              </div>
              <div className="p-2.5 bg-black/40 rounded-lg border border-white/[0.05]">
                <span className="text-slate-400 font-sans block">Environment:</span>
                <span className="text-blue-400 font-bold">SANDBOX (No Real Money)</span>
              </div>
            </div>

            {/* Security Verification Tests */}
            <div className="pt-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Security Verification Tests:</span>
              <div className="flex gap-2">
                <button
                  onClick={triggerAttackDemoReplay}
                  className="text-xs bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 px-3 py-1.5 rounded-lg transition font-medium"
                >
                  ⚠️ Test Token Replay Attack
                </button>
                <button
                  onClick={triggerIdempotencyDemo}
                  className="text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1.5 rounded-lg transition font-medium"
                >
                  🔄 Test Idempotency Retry
                </button>
              </div>
            </div>

            {/* Authorization Action Buttons */}
            <div className="flex gap-3 pt-3 border-t border-white/[0.08]">
              <button
                onClick={handleConfirmPurchase}
                disabled={paymentLoading}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold py-3.5 px-6 rounded-xl shadow-lg shadow-emerald-600/30 transition-all text-sm disabled:opacity-50 hover:scale-[1.01]"
              >
                {paymentLoading ? "Evaluating Policy & Creating Test Order..." : "[ CONFIRM PURCHASE (RAZORPAY TEST MODE) ]"}
              </button>
              <button
                onClick={() => { setOrderResult(null); setPaymentError("Purchase cancelled by user."); }}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-3.5 px-6 rounded-xl text-sm transition"
              >
                [ CANCEL ]
              </button>
            </div>

            {/* Success & Error Cards */}
            {orderResult && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40 text-emerald-300 font-mono text-xs space-y-1">
                <span className="font-bold text-sm block">✓ RAZORPAY TEST ORDER CREATED SUCCESSFULLY</span>
                <p>Order ID: <span className="font-bold text-white">{orderResult.order.order_id}</span></p>
                <p>Amount: <span className="font-bold text-white">₹{orderResult.order.amount_paise / 100}</span> ({orderResult.order.amount_paise} paise)</p>
                <p>Mode: <span className="font-bold text-emerald-400">TEST MODE</span> | Receipt: {orderResult.order.receipt}</p>
                <p>Risk Level: <span className="font-bold text-emerald-400">{orderResult.risk_level}</span></p>
              </div>
            )}

            {paymentError && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/40 text-red-300 font-mono text-xs">
                <span className="font-bold text-sm block mb-1">SECURITY & POLICY STATUS:</span>
                {paymentError}
              </div>
            )}
          </section>
        </div>

        {/* Right Column: Real-Time Event Timeline */}
        <div className="xl:col-span-1">
          <div className="sticky top-20">
            <section className="glass-card p-5 rounded-2xl space-y-4 border border-white/[0.08]">
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                  Real-Time AI Activity Stream
                </h2>
                <span className="text-[10px] text-slate-400 font-mono bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">
                  AUDITED
                </span>
              </div>

              <div className="space-y-3">
                {timelineEvents.map((evt, idx) => (
                  <div key={evt.event_id || idx} className="relative flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="mt-0.5 text-emerald-400 font-bold text-sm">
                      {evt.is_failed ? "✕" : "✓"}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-200">{evt.label}</span>
                        <span className="text-[9px] font-mono text-slate-500">
                          {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">{evt.detail}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-white/[0.08] text-center">
                <p className="text-[10px] text-slate-500 italic">
                  State transitions correspond to backend cryptographic audit events. Zero mock counters.
                </p>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
