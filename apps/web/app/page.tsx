"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Navbar from "./components/Navbar";

export default function HomePage() {
  const [mcpCount, setMcpCount] = useState<number>(13);
  const [pipelineStatus, setPipelineStatus] = useState<string>("OPERATIONAL");

  useEffect(() => {
    fetch("http://localhost:8000/api/agent/mcp/tools")
      .then((res) => res.json())
      .then((data) => {
        if (data && data.count) setMcpCount(data.count);
      })
      .catch(() => {});
  }, []);

  const cards = [
    {
      title: "MCP Explorer & Tool Gateway",
      desc: "Model Context Protocol JSON-RPC 2.0 interface. Inspect approved tools, test RPC invocations, and verify security barriers.",
      href: "/mcp",
      external: false,
      badge: "MCP PROTOCOL",
      badgeColor: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
      btnText: "Launch MCP Explorer →",
      btnBg: "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/20",
    },
    {
      title: "AI Buyer Control Interface",
      desc: "Page A — 10-Stage agent telemetry pipeline, real product discovery (OpenFoodFacts API), cart solver & step-up gate.",
      href: "/buyer",
      external: false,
      badge: "BUYER PORTAL",
      badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      btnText: "Launch Buyer Telemetry →",
      btnBg: "bg-blue-600 hover:bg-blue-500 shadow-blue-600/20",
    },
    {
      title: "Buyer Mandates Controller",
      desc: "Page C — Active buyer spending mandates, daily budget caps, category permissions & one-click instant revocation.",
      href: "/mandates",
      external: false,
      badge: "MANDATES STUDIO",
      badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      btnText: "Manage Buyer Mandates →",
      btnBg: "bg-amber-600 hover:bg-amber-500 shadow-amber-600/20",
    },
    {
      title: "Transactions & Audit Ledger",
      desc: "Page D — Cryptographically bound transaction records, 5-layer security timeline, SHA-256 evidence & human approvals.",
      href: "/transactions",
      external: false,
      badge: "AUDIT LEDGER",
      badgeColor: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
      btnText: "Inspect Transaction Ledger →",
      btnBg: "bg-cyan-600 hover:bg-cyan-500 shadow-cyan-600/20",
    },
    {
      title: "Merchant Policy Center",
      desc: "Page B — Configure store purchase rules, merchant product catalog, step-up limits & allowed connector permissions.",
      href: "/merchant",
      external: false,
      badge: "MERCHANT HUB",
      badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      btnText: "Configure Merchant Policy →",
      btnBg: "bg-purple-600 hover:bg-purple-500 shadow-purple-600/20",
    },
    {
      title: "Operations Dashboard UI",
      desc: "Interactive control room dashboard with real-time system metrics, active mandate stats, and live telemetry feeds.",
      href: "http://localhost:8000/dashboard",
      external: true,
      badge: "CONTROL ROOM",
      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      btnText: "Open Dashboard UI →",
      btnBg: "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20",
    },
  ];

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 font-sans">
      <Navbar />

      {/* Main Hub Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="text-center mb-14">
          <div className="flex justify-center items-center gap-2 mb-3">
            <span className="text-xs font-extrabold uppercase tracking-widest text-orange-400 bg-orange-500/10 px-4 py-1.5 rounded-full border border-orange-500/20">
              Autonomous AI Commerce Trust Protocol
            </span>
            <span className="text-xs font-bold bg-emerald-500/10 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-500/20 flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
              API REAL DATA ACTIVE
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight mb-4">
            Mandate Gateway Control Hub
          </h1>
          <p className="text-slate-400 text-base max-w-3xl mx-auto leading-relaxed">
            Production-grade AI commerce foundation enforcing fail-closed product truth, Model Context Protocol (MCP) JSON-RPC tool boundaries, 5-layer payment safety, and Ed25519 signed transaction receipts.
          </p>
        </div>

        {/* System Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          <div className="bg-[#111827] border border-slate-800 rounded-2xl p-5 text-center">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1">Approved MCP Tools</span>
            <span className="text-2xl font-black text-indigo-400">{mcpCount} Tools</span>
          </div>
          <div className="bg-[#111827] border border-slate-800 rounded-2xl p-5 text-center">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1">Telemetry Pipeline</span>
            <span className="text-2xl font-black text-emerald-400">10 Stages</span>
          </div>
          <div className="bg-[#111827] border border-slate-800 rounded-2xl p-5 text-center">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1">Payment Safety</span>
            <span className="text-2xl font-black text-cyan-400">5-Layer Lock</span>
          </div>
          <div className="bg-[#111827] border border-slate-800 rounded-2xl p-5 text-center">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1">Live Product Search</span>
            <span className="text-2xl font-black text-orange-400">OpenFoodFacts</span>
          </div>
        </div>

        {/* Navigation Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cards.map((card, i) => (
            <div
              key={i}
              className="bg-[#111827] border border-slate-800 rounded-2xl p-7 flex flex-col justify-between shadow-xl hover:border-slate-700 transition group"
            >
              <div>
                <div className="flex justify-between items-center mb-4">
                  <span className={`text-[11px] font-black px-3 py-1 rounded-md border ${card.badgeColor}`}>
                    {card.badge}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">MODULE 0{i + 1}</span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-orange-400 transition">
                  {card.title}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-6">{card.desc}</p>
              </div>

              {card.external ? (
                <a
                  href={card.href}
                  className={`w-full py-3.5 rounded-xl text-white font-extrabold text-xs transition shadow-lg flex items-center justify-center gap-2 ${card.btnBg}`}
                >
                  {card.btnText}
                </a>
              ) : (
                <Link
                  href={card.href}
                  className={`w-full py-3.5 rounded-xl text-white font-extrabold text-xs transition shadow-lg flex items-center justify-center gap-2 ${card.btnBg}`}
                >
                  {card.btnText}
                </Link>
              )}
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-slate-800/80 py-6 px-8 text-center text-xs text-slate-500 mt-16">
        RAZERPAY MANDATE GATEWAY — REAL-TIME AGENT TRUST & SETTLEMENT LAYER • SHA-256 PROVENANCE VERIFIED
      </footer>
    </div>
  );
}
