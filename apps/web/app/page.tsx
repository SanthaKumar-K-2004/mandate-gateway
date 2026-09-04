"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Navbar from "./components/Navbar";

interface LiveStat {
  label: string;
  value: string;
  sub?: string;
  color: string;
  icon: string;
}

export default function HomePage() {
  const [mcpCount, setMcpCount] = useState<number>(13);
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  const [txCount, setTxCount] = useState<number>(0);
  const [mandateCount, setMandateCount] = useState<number>(2);
  const [tick, setTick] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // Live stats fetch
    const fetchStats = async () => {
      try {
        const [health, mcpData, opsData] = await Promise.allSettled([
          fetch("http://localhost:8000/health").then((r) => r.json()),
          fetch("http://localhost:8000/api/agent/mcp/tools").then((r) => r.json()),
          fetch("http://localhost:8000/internal/operations/transactions").then((r) => r.json()),
        ]);
        if (health.status === "fulfilled") setApiHealthy(health.value?.status === "HEALTHY");
        if (mcpData.status === "fulfilled" && mcpData.value?.count) setMcpCount(mcpData.value.count);
        if (opsData.status === "fulfilled") {
          const items = opsData.value?.transactions || opsData.value || [];
          if (Array.isArray(items)) setTxCount(items.length);
        }
      } catch {}
    };
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  // Animated tick for live clock
  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Particle canvas animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    const particles: { x: number; y: number; vx: number; vy: number; size: number; opacity: number; color: string }[] = [];
    const colors = ["rgba(249,115,22,", "rgba(16,185,129,", "rgba(99,102,241,", "rgba(6,182,212,"];

    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        size: Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.4 + 0.1,
        color: colors[Math.floor(Math.random() * colors.length)],
      });
    }

    let animId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}${p.opacity})`;
        ctx.fill();
      });
      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(30,45,64,${0.4 * (1 - dist / 100)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      animId = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animId);
  }, []);

  const liveStats: LiveStat[] = [
    { label: "MCP Tools", value: `${mcpCount}`, sub: "APPROVED", color: "indigo", icon: "⚡" },
    { label: "Pipeline Stages", value: "10", sub: "TELEMETRY", color: "blue", icon: "🔄" },
    { label: "Safety Layers", value: "5", sub: "LOCK LEVELS", color: "cyan", icon: "🛡️" },
    { label: "Transactions", value: txCount > 0 ? `${txCount}` : "Live", sub: "IN LEDGER", color: "emerald", icon: "💳" },
    { label: "API Gateway", value: apiHealthy === null ? "..." : apiHealthy ? "ONLINE" : "OFFLINE", sub: "SYSTEM STATUS", color: apiHealthy ? "emerald" : "red", icon: "🟢" },
    { label: "Mandates Active", value: `${mandateCount}`, sub: "BUYER POLICY", color: "amber", icon: "🔐" },
  ];

  const colorMap: Record<string, { text: string; bg: string; border: string; glow: string }> = {
    indigo: { text: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/20", glow: "shadow-indigo-500/10" },
    blue:   { text: "text-blue-400",   bg: "bg-blue-500/10",   border: "border-blue-500/20",   glow: "shadow-blue-500/10" },
    cyan:   { text: "text-cyan-400",   bg: "bg-cyan-500/10",   border: "border-cyan-500/20",   glow: "shadow-cyan-500/10" },
    emerald:{ text: "text-emerald-400",bg: "bg-emerald-500/10",border: "border-emerald-500/20",glow: "shadow-emerald-500/10" },
    amber:  { text: "text-amber-400",  bg: "bg-amber-500/10",  border: "border-amber-500/20",  glow: "shadow-amber-500/10" },
    red:    { text: "text-red-400",    bg: "bg-red-500/10",    border: "border-red-500/20",    glow: "shadow-red-500/10" },
    purple: { text: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20", glow: "shadow-purple-500/10" },
    orange: { text: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", glow: "shadow-orange-500/10" },
  };

  const modules = [
    {
      title: "MCP Tool Gateway",
      desc: "Model Context Protocol JSON-RPC 2.0 server. Browse approved tools, execute live RPC calls, and verify autonomous AI security barriers.",
      href: "/mcp",
      badge: "MCP PROTOCOL",
      color: "indigo",
      icon: "⚡",
      features: ["tools/list & tools/call", "Security barrier test", "Live JSON-RPC workbench"],
    },
    {
      title: "AI Buyer Control",
      desc: "10-stage agent telemetry pipeline with real product discovery from OpenFoodFacts API, cart solver, and step-up authentication gate.",
      href: "/buyer",
      badge: "BUYER TELEMETRY",
      color: "blue",
      icon: "🤖",
      features: ["10-stage pipeline", "Live product search", "SHA-256 evidence"],
    },
    {
      title: "Mandates Studio",
      desc: "Configure buyer spending mandates, daily budget caps, category permissions. One-click instant revocation with audit trail.",
      href: "/mandates",
      badge: "POLICY ENGINE",
      color: "amber",
      icon: "🔐",
      features: ["Create/revoke mandates", "Budget enforcement", "Real-time policy"],
    },
    {
      title: "Audit Ledger",
      desc: "Cryptographically bound transaction records, 5-layer security timeline, SHA-256 provenance evidence, and human step-up approvals.",
      href: "/transactions",
      badge: "AUDIT TRAIL",
      color: "cyan",
      icon: "📋",
      features: ["Ed25519 signatures", "Step-up gate", "Full timeline"],
    },
    {
      title: "Merchant Policy Hub",
      desc: "Store-level purchase rules, product catalog configuration, step-up limits, and allowed payment connector permissions.",
      href: "/merchant",
      badge: "MERCHANT CONFIG",
      color: "purple",
      icon: "🏪",
      features: ["Policy rules", "Product catalog", "Connector config"],
    },
    {
      title: "Operations Dashboard",
      desc: "Live system control room with real-time metrics, active mandate stats, Swagger API explorer, and telemetry health feeds.",
      href: "http://localhost:8000/docs",
      badge: "CONTROL ROOM",
      color: "emerald",
      icon: "🎛️",
      external: true,
      features: ["Swagger UI", "Live metrics", "Health endpoints"],
    },
  ];

  const architecture = [
    { num: "01", title: "Intent Ingestion", desc: "Natural language buyer intent parsed by policy engine", color: "orange" },
    { num: "02", title: "MCP Tool Dispatch", desc: "JSON-RPC 2.0 tool calls to approved capability registry", color: "indigo" },
    { num: "03", title: "Live Product Discovery", desc: "OpenFoodFacts API + merchant direct catalog search", color: "blue" },
    { num: "04", title: "SHA-256 Evidence Hashing", desc: "Cryptographic provenance verification on every product", color: "cyan" },
    { num: "05", title: "Mandate Authorization", desc: "Zero-LLM deterministic rule evaluation against policy", color: "emerald" },
    { num: "06", title: "Human Step-Up Gate", desc: "High-value purchases require explicit human approval token", color: "amber" },
    { num: "07", title: "Razorpay Settlement", desc: "Ed25519-signed order creation & payment commitment", color: "purple" },
  ];

  return (
  return (
    <div className="min-h-screen bg-[#040711] text-slate-100 font-sans overflow-x-hidden">
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Particle Canvas background */}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none opacity-50"
        />
        {/* Cyber grid overlay */}
        <div className="absolute inset-0 cyber-grid opacity-15 pointer-events-none" />
        {/* Radial gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#040711]/70 to-[#040711] pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-6 pt-16 pb-14 text-center">
          {/* Status pill */}
          <div className="flex justify-center items-center gap-3 mb-6 flex-wrap">
            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-orange-400 bg-orange-500/10 px-4 py-1.5 rounded-full border border-orange-500/20 backdrop-blur-md">
              🏆 Autonomous AI Commerce Trust Protocol
            </span>
            {apiHealthy !== null && (
              <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border backdrop-blur-md transition-colors ${
                apiHealthy
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-red-500/10 text-red-400 border-red-500/20"
              }`}>
                <span className={`w-2 h-2 rounded-full animate-pulse ${apiHealthy ? "bg-emerald-400" : "bg-red-400"}`} />
                {apiHealthy ? "ALL SYSTEMS LIVE" : "API OFFLINE"}
              </span>
            )}
          </div>

          {/* Main heading */}
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-5 leading-tight text-white">
            <span className="text-white block">Mandate</span>
            <span className="gradient-text block">Gateway</span>
            <span className="text-slate-400 text-2xl md:text-3xl font-bold block mt-2 tracking-normal">AI Commerce Safety & Settlement Layer</span>
          </h1>

          <p className="text-slate-300 text-base md:text-lg max-w-3xl mx-auto leading-relaxed mb-8 font-normal">
            Production-grade AI commerce foundation enforcing fail-closed product truth, Model Context Protocol (MCP) JSON-RPC tool boundaries, 5-layer payment safety, and <span className="text-emerald-400 font-semibold">Ed25519 signed</span> transaction receipts. Built for <span className="text-orange-400 font-semibold">Razorpay Raze 2026 Buildathon</span>.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-wrap gap-3 justify-center mb-14">
            <Link
              href="/buyer"
              className="px-7 py-3.5 bg-gradient-to-r from-orange-500 to-orange-400 hover:from-orange-400 hover:to-orange-300 text-white font-bold text-sm rounded-2xl shadow-xl shadow-orange-500/20 transition-all duration-300 hover:scale-[1.02] flex items-center gap-2"
            >
              🤖 Launch AI Buyer Demo
            </Link>
            <Link
              href="/mcp"
              className="px-7 py-3.5 bg-[#090d1a] hover:bg-[#0e1428] border border-white/[0.1] hover:border-indigo-500/40 text-white font-semibold text-sm rounded-2xl transition-all duration-300 hover:scale-[1.02] flex items-center gap-2"
            >
              ⚡ Explore MCP Tools
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="px-7 py-3.5 bg-[#090d1a] hover:bg-[#0e1428] border border-white/[0.1] hover:border-emerald-500/40 text-slate-300 hover:text-white font-semibold text-sm rounded-2xl transition-all duration-300 flex items-center gap-2"
            >
              📖 API Swagger Docs ↗
            </a>
          </div>
        </div>
      </section>

      {/* Live Stats Grid */}
      <section className="max-w-7xl mx-auto px-6 mb-14">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {liveStats.map((stat, i) => {
            const c = colorMap[stat.color] || colorMap.indigo;
            return (
              <div
                key={i}
                className={`glass-card rounded-2xl p-4 text-center hover:-translate-y-0.5 transition-all duration-300 ${c.glow}`}
              >
                <div className="text-xl mb-1">{stat.icon}</div>
                <div className={`text-2xl font-black ${c.text} leading-none mb-1`}>{stat.value}</div>
                <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">{stat.sub}</div>
                <div className="text-[11px] text-slate-500 mt-0.5 font-medium">{stat.label}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Module Cards */}
      <section className="max-w-7xl mx-auto px-6 mb-20">
        <div className="flex items-center gap-3 mb-8">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[#1e2d40] to-transparent" />
          <span className="text-xs font-black uppercase tracking-widest text-slate-500 px-4">System Modules</span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[#1e2d40] to-transparent" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {modules.map((mod, i) => {
            const c = colorMap[mod.color] || colorMap.indigo;
            const Content = (
              <div
                className={`group bg-[#0c1120] border border-[#1e2d40] hover:border-opacity-60 rounded-2xl p-6 flex flex-col h-full transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl cursor-pointer`}
                style={{ animationDelay: `${i * 80}ms` }}
              >
                {/* Badge row */}
                <div className="flex items-center justify-between mb-4">
                  <span className={`text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border ${c.bg} ${c.text} ${c.border}`}>
                    {mod.badge}
                  </span>
                  <span className="text-xs text-slate-600 font-mono">MOD-{String(i + 1).padStart(2, "0")}</span>
                </div>

                {/* Icon + Title */}
                <div className="flex items-start gap-3 mb-3">
                  <span className="text-3xl flex-shrink-0 group-hover:scale-110 transition-transform duration-200">{mod.icon}</span>
                  <h3 className={`text-lg font-black text-white group-hover:${c.text} transition-colors leading-tight`}>
                    {mod.title}
                  </h3>
                </div>

                {/* Description */}
                <p className="text-xs text-slate-400 leading-relaxed mb-4 flex-1">{mod.desc}</p>

                {/* Feature chips */}
                <div className="flex flex-wrap gap-1.5 mb-5">
                  {mod.features.map((f) => (
                    <span key={f} className="text-[10px] font-mono text-slate-500 bg-[#0a0f1e] border border-[#1a2535] px-2 py-0.5 rounded-md">
                      {f}
                    </span>
                  ))}
                </div>

                {/* CTA */}
                <div className={`w-full py-3 rounded-xl text-white font-black text-xs text-center transition-all duration-200 flex items-center justify-center gap-1.5 ${c.bg} border ${c.border} group-hover:bg-opacity-30`}>
                  <span>Open {mod.title}</span>
                  <span className="group-hover:translate-x-0.5 transition-transform">→</span>
                </div>
              </div>
            );

            return mod.external ? (
              <a key={i} href={mod.href} target="_blank" rel="noopener noreferrer">
                {Content}
              </a>
            ) : (
              <Link key={i} href={mod.href}>
                {Content}
              </Link>
            );
          })}
        </div>
      </section>

      {/* Architecture Timeline */}
      <section className="max-w-7xl mx-auto px-6 mb-20">
        <div className="bg-[#0c1120] border border-[#1e2d40] rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 bg-orange-500/10 border border-orange-500/20 rounded-xl flex items-center justify-center text-orange-400 font-black text-sm">⬡</div>
            <div>
              <h2 className="text-xl font-black text-white">Trust Pipeline Architecture</h2>
              <p className="text-xs text-slate-500">End-to-end autonomous commerce flow from intent to cryptographic settlement</p>
            </div>
          </div>

          <div className="relative">
            {/* Connecting line */}
            <div className="absolute left-8 top-8 bottom-8 w-px bg-gradient-to-b from-orange-500/40 via-indigo-500/30 to-emerald-500/40" />

            <div className="space-y-4">
              {architecture.map((step, i) => {
                const c = colorMap[step.color] || colorMap.indigo;
                return (
                  <div key={i} className="relative flex items-start gap-5 pl-4">
                    <div className={`relative z-10 w-8 h-8 rounded-xl border ${c.bg} ${c.border} flex items-center justify-center flex-shrink-0`}>
                      <span className={`text-xs font-black font-mono ${c.text}`}>{step.num}</span>
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="flex items-center gap-2 mb-0.5">
                        <h4 className="text-sm font-bold text-white">{step.title}</h4>
                        <div className={`h-px flex-1 bg-gradient-to-r ${c.bg} to-transparent`} />
                      </div>
                      <p className="text-xs text-slate-500">{step.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#1e2d40]/60 py-8 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-emerald-500 rounded-lg flex items-center justify-center font-black text-sm text-white">R</div>
            <div>
              <p className="text-xs font-black text-slate-400">RAZORPAY MANDATE GATEWAY</p>
              <p className="text-[10px] text-slate-600">Built for Razorpay Raze 2025 — SanthaKumar K</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
            <span>SHA-256 PROVENANCE VERIFIED</span>
            <span>•</span>
            <span>ED25519 SIGNED RECEIPTS</span>
            <span>•</span>
            <span>MCP JSON-RPC 2.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
