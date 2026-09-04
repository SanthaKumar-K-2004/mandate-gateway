"use client";

import React from "react";
import Link from "next/link";

export default function HomePage() {
  const cards = [
    {
      title: "Operations Dashboard UI",
      desc: "Interactive 10-Stage AI Commerce Control Center with live product discovery, cost truth model & Razorpay settlement.",
      href: "http://localhost:8000/dashboard",
      external: true,
      badge: "LIVE DEMO",
      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      btnText: "Open Operations Dashboard →",
      btnBg: "bg-emerald-600 hover:bg-emerald-500",
    },
    {
      title: "AI Buyer Control Interface",
      desc: "Page A — Natural language buyer shopping intent execution, real catalog recommendation, and mandate binding.",
      href: "/buyer",
      external: false,
      badge: "BUYER PORTAL",
      badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      btnText: "Launch Buyer Portal →",
      btnBg: "bg-blue-600 hover:bg-blue-500",
    },
    {
      title: "Merchant AI Commerce Policy",
      desc: "Page B — Configure merchant autonomous purchase limits, step-up approval thresholds & allowed MCP tools.",
      href: "/merchant",
      external: false,
      badge: "MERCHANT HUB",
      badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      btnText: "Configure Merchant Policy →",
      btnBg: "bg-purple-600 hover:bg-purple-500",
    },
    {
      title: "Buyer Mandates Controller",
      desc: "Page C — Active buyer authorization mandates, spend cap enforcement, category permissions & one-click revocation.",
      href: "/mandates",
      external: false,
      badge: "MANDATES",
      badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      btnText: "Manage Buyer Mandates →",
      btnBg: "bg-amber-600 hover:bg-amber-500",
    },
    {
      title: "Transactions & Audit Ledger",
      desc: "Page D — Cryptographically bound transaction records, SHA-256 evidence hashes & outbox dispatch telemetry.",
      href: "/transactions",
      external: false,
      badge: "AUDIT LEDGER",
      badgeColor: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
      btnText: "Inspect Transaction Ledger →",
      btnBg: "bg-cyan-600 hover:bg-cyan-500",
    },
  ];

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 px-8 py-5 flex justify-between items-center bg-[#0d1322]">
        <div className="flex items-center gap-3.5">
          <div className="w-9 h-9 bg-gradient-to-br from-orange-500 to-emerald-500 rounded-xl flex items-center justify-center font-black text-lg text-white shadow-lg shadow-orange-500/20">
            R
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-white m-0">RAZERPAY</h1>
            <p className="text-xs text-slate-400 m-0">Mandate Gateway — AI Commerce Trust & Settlement Layer</p>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3.5 py-1.5 rounded-full text-xs font-bold text-emerald-400">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse inline-block"></span>
          GATEWAY v1.0.0 ONLINE
        </div>
      </header>

      {/* Main Hub Content */}
      <main className="max-w-6xl mx-auto px-8 py-12">
        <div className="text-center mb-14">
          <span className="text-xs font-extrabold uppercase tracking-widest text-orange-500 bg-orange-500/10 px-3.5 py-1.5 rounded-full border border-orange-500/20">
            Autonomous AI Commerce Protocol
          </span>
          <h2 className="text-4xl font-extrabold mt-4 mb-3 text-white tracking-tight">
            Mandate Gateway Control Hub
          </h2>
          <p className="text-slate-400 text-base max-w-2xl mx-auto leading-relaxed">
            Verified zero-LLM payment authorization, multi-merchant product discovery, total cost truth model, and cryptographic transaction settlement.
          </p>
        </div>

        {/* Navigation Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cards.map((card, i) => (
            <div
              key={i}
              className="bg-[#111827] border border-slate-800 rounded-2xl p-7 flex flex-col justify-between shadow-xl hover:border-slate-700 transition"
            >
              <div>
                <div className="flex justify-between items-center mb-4">
                  <span className={`text-xs font-extrabold px-2.5 py-1 rounded-md border ${card.badgeColor}`}>
                    {card.badge}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">MODULE 0{i + 1}</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{card.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed mb-6">{card.desc}</p>
              </div>

              {card.external ? (
                <a
                  href={card.href}
                  className={`inline-flex items-center justify-center px-5 py-3 rounded-xl text-white font-bold text-sm transition shadow-lg ${card.btnBg}`}
                >
                  {card.btnText}
                </a>
              ) : (
                <Link
                  href={card.href}
                  className={`inline-flex items-center justify-center px-5 py-3 rounded-xl text-white font-bold text-sm transition shadow-lg ${card.btnBg}`}
                >
                  {card.btnText}
                </Link>
              )}
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 px-8 text-center text-xs text-slate-500 mt-16">
        RAZERPAY MANDATE GATEWAY — REAL-TIME AGENT TRUST & SETTLEMENT LAYER • SHA-256 PROVENANCE VERIFIED
      </footer>
    </div>
  );
}
