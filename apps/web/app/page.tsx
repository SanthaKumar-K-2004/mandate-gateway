"use client";

import React from "react";

export default function HomePage() {
  const cards = [
    {
      title: "Operations Dashboard UI",
      desc: "Interactive 10-Stage AI Commerce Control Center with live product discovery, cost truth model & Razorpay settlement.",
      href: "/dashboard",
      badge: "LIVE DEMO",
      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      btnText: "Open Operations Dashboard →",
      btnBg: "bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700",
    },
    {
      title: "AI Buyer Control Interface",
      desc: "Page A — Natural language buyer shopping intent execution, real catalog recommendation, and mandate binding.",
      href: "/buyer",
      badge: "BUYER PORTAL",
      badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      btnText: "Launch Buyer Portal →",
      btnBg: "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700",
    },
    {
      title: "Merchant AI Commerce Policy",
      desc: "Page B — Configure merchant autonomous purchase limits, step-up approval thresholds & allowed MCP tools.",
      href: "/merchant",
      badge: "MERCHANT HUB",
      badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      btnText: "Configure Merchant Policy →",
      btnBg: "bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-700 hover:to-violet-700",
    },
    {
      title: "Buyer Mandates Controller",
      desc: "Page C — Active buyer authorization mandates, spend cap enforcement, category permissions & one-click revocation.",
      href: "/mandates",
      badge: "MANDATES",
      badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      btnText: "Manage Buyer Mandates →",
      btnBg: "bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700",
    },
    {
      title: "Transactions & Audit Ledger",
      desc: "Page D — Cryptographically bound transaction records, SHA-256 evidence hashes & outbox dispatch telemetry.",
      href: "/transactions",
      badge: "AUDIT LEDGER",
      badgeColor: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
      btnText: "Inspect Transaction Ledger →",
      btnBg: "bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700",
    },
  ];

  return (
    <div style={{ background: "#090d16", color: "#f8fafc", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      {/* Top Navbar */}
      <header style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", padding: "1.25rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
          <div style={{ width: "38px", height: "38px", background: "linear-gradient(135deg, #f97316, #10b981)", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: "1.2rem", color: "#ffffff", boxShadow: "0 4px 12px rgba(249,115,22,0.3)" }}>
            R
          </div>
          <div>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 800, letterSpacing: "-0.02em", color: "#ffffff", margin: 0 }}>RAZERPAY</h1>
            <p style={{ fontSize: "0.75rem", color: "#94a3b8", margin: 0 }}>Mandate Gateway — AI Commerce Trust & Settlement Layer</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", padding: "0.4rem 0.85rem", borderRadius: "9999px", fontSize: "0.78rem", fontWeight: 700, color: "#34d399" }}>
          <span style={{ width: "8px", height: "8px", background: "#10b981", borderRadius: "50%", display: "inline-block" }}></span>
          GATEWAY v1.0.0 ONLINE
        </div>
      </header>

      {/* Main Hub Content */}
      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "3rem 2rem" }}>
        <div style={{ textAlign: "center", marginBottom: "3.5rem" }}>
          <span style={{ fontSize: "0.76rem", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em", color: "#f97316", background: "rgba(249, 115, 22, 0.1)", padding: "0.3rem 0.8rem", borderRadius: "9999px", border: "1px solid rgba(249, 115, 22, 0.2)" }}>
            Autonomous AI Commerce Protocol
          </span>
          <h2 style={{ fontSize: "2.5rem", fontWeight: 800, marginTop: "1rem", marginBottom: "0.75rem", color: "#ffffff", letterSpacing: "-0.03em" }}>
            Mandate Gateway Control Hub
          </h2>
          <p style={{ color: "#94a3b8", fontSize: "1.05rem", maxWidth: "680px", margin: "0 auto", lineHeight: 1.6 }}>
            Verified zero-LLM payment authorization, multi-merchant product discovery, total cost truth model, and cryptographic transaction settlement.
          </p>
        </div>

        {/* Navigation Cards Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "1.5rem" }}>
          {cards.map((card, i) => (
            <div
              key={i}
              style={{
                background: "#111827",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "16px",
                padding: "1.75rem",
                display: "flex",
                flexDirection: "column",
                justify-space: "between",
                boxShadow: "0 10px 30px rgba(0, 0, 0, 0.2)",
                transition: "all 0.2s ease",
              }}
            >
              <div>
                <div style={{ display: "flex", justify-content: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 800, padding: "0.2rem 0.6rem", borderRadius: "6px", background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#38bdf8" }}>
                    {card.badge}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "#64748b", fontFamily: "monospace" }}>MODULE 0{i + 1}</span>
                </div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "#ffffff", marginBottom: "0.5rem" }}>{card.title}</h3>
                <p style={{ fontSize: "0.88rem", color: "#94a3b8", lineHeight: 1.5, marginBottom: "1.5rem" }}>{card.desc}</p>
              </div>

              <a
                href={card.href}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "0.75rem 1.25rem",
                  borderRadius: "10px",
                  background: card.btnBg.includes("emerald") ? "linear-gradient(135deg, #10b981, #059669)" : card.btnBg.includes("blue") ? "linear-gradient(135deg, #2563eb, #1d4ed8)" : card.btnBg.includes("purple") ? "linear-gradient(135deg, #9333ea, #7e22ce)" : card.btnBg.includes("amber") ? "linear-gradient(135deg, #f59e0b, #d97706)" : "linear-gradient(135deg, #0284c7, #0369a1)",
                  color: "#ffffff",
                  fontWeight: 700,
                  fontSize: "0.9rem",
                  textDecoration: "none",
                  boxShadow: "0 4px 14px rgba(0, 0, 0, 0.25)",
                }}
              >
                {card.btnText}
              </a>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid rgba(255,255,255,0.08)", padding: "1.25rem 2rem", textAlign: "center", fontSize: "0.8rem", color: "#64748b", marginTop: "4rem" }}>
        RAZERPAY MANDATE GATEWAY — REAL-TIME AGENT TRUST & SETTLEMENT LAYER • SHA-256 PROVENANCE VERIFIED
      </footer>
    </div>
  );
}
