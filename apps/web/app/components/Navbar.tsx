"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [menuOpen, setMenuOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const update = () => setCurrentTime(new Date().toLocaleTimeString("en-IN", { hour12: false }));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch("http://localhost:8000/health", { signal: AbortSignal.timeout(3000) });
        const data = await res.json();
        setBackendStatus(data.status === "HEALTHY" ? "online" : "offline");
      } catch {
        setBackendStatus("offline");
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/", label: "Hub", icon: "⬡" },
    { href: "/buyer", label: "Buyer AI", icon: "🤖" },
    { href: "/mandates", label: "Mandates", icon: "🔐" },
    { href: "/transactions", label: "Ledger", icon: "📋" },
    { href: "/merchant", label: "Merchant", icon: "🏪" },
    { href: "/mcp", label: "MCP", icon: "⚡" },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-[#040711]/85 backdrop-blur-2xl transition-all duration-300">
      {/* Top micro-bar */}
      <div className="border-b border-white/[0.04] px-6 py-1.5 flex items-center justify-between max-w-7xl mx-auto">
        <span className="text-[11px] font-mono text-slate-400 tracking-wider font-medium flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse" />
          RAZORPAY MANDATE GATEWAY — AI COMMERCE TRUST PROTOCOL v2.0
        </span>
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-slate-400 font-medium">
            {currentTime ? `${currentTime} IST` : "LIVE IST"}
          </span>
          <div
            className={`flex items-center gap-1.5 text-[10px] font-semibold px-2.5 py-0.5 rounded-full border transition-colors ${
              backendStatus === "online"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : backendStatus === "offline"
                ? "bg-red-500/10 text-red-400 border-red-500/20"
                : "bg-slate-800 text-slate-400 border-slate-700"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                backendStatus === "online"
                  ? "bg-emerald-400 animate-pulse"
                  : backendStatus === "offline"
                  ? "bg-red-400"
                  : "bg-slate-400 animate-pulse"
              }`}
            />
            {backendStatus === "online" ? "API LIVE" : backendStatus === "offline" ? "API DOWN" : "CHECKING"}
          </div>
        </div>
      </div>

      {/* Main nav row */}
      <div className="px-6 py-2.5 flex items-center justify-between gap-4 max-w-7xl mx-auto">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group shrink-0">
          <div className="relative w-9 h-9">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 via-orange-400 to-emerald-500 flex items-center justify-center font-black text-lg text-white shadow-lg shadow-orange-500/20 group-hover:scale-105 transition-transform duration-200">
              R
            </div>
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-[#040711] animate-pulse" />
          </div>
          <div className="hidden sm:block">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-white">RAZORPAY</span>
              <span className="text-[10px] uppercase font-bold text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20 tracking-wider">
                MANDATE
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium tracking-normal">AI Commerce Trust & Settlement Protocol</p>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1 bg-[#090d1a]/90 border border-white/[0.08] p-1 rounded-2xl shadow-inner">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                  isActive
                    ? "bg-gradient-to-r from-orange-500/20 via-indigo-500/20 to-emerald-500/20 text-white border border-white/[0.15] shadow-md shadow-orange-500/5"
                    : "text-slate-400 hover:text-white hover:bg-white/[0.05]"
                }`}
              >
                <span className="text-sm leading-none">{link.icon}</span>
                <span>{link.label}</span>
                {isActive && (
                  <span className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-pulse" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-2">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#090d1a] border border-white/[0.08] text-xs font-semibold text-slate-300 hover:text-white hover:border-indigo-500/40 transition-all duration-200"
          >
            <span className="text-sm">📖</span>
            <span>API Docs</span>
          </a>

          {/* Mobile menu button */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-xl bg-[#090d1a] border border-white/[0.08] text-slate-300 hover:text-white transition"
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-white/[0.08] bg-[#040711]/95 px-4 py-3 flex flex-col gap-1 backdrop-blur-xl">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition ${
                  isActive
                    ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                    : "text-slate-400 hover:text-white hover:bg-white/[0.05]"
                }`}
              >
                <span>{link.icon}</span>
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
}

