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
    <header className="sticky top-0 z-50 border-b border-[#1e2d40]/80 bg-[#050810]/95 backdrop-blur-xl">
      {/* Top micro-bar */}
      <div className="border-b border-[#0d1525] px-6 py-1.5 flex items-center justify-between">
        <span className="text-[10px] font-mono text-slate-600 tracking-widest uppercase">
          RAZORPAY MANDATE GATEWAY — AUTONOMOUS COMMERCE TRUST PROTOCOL v2.0
        </span>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-slate-600">
            {currentTime ? `${currentTime} IST` : "LIVE IST"}
          </span>
          <div
            className={`flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              backendStatus === "online"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : backendStatus === "offline"
                ? "bg-red-500/10 text-red-400 border-red-500/20"
                : "bg-slate-800 text-slate-500 border-slate-700"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                backendStatus === "online"
                  ? "bg-emerald-500 animate-pulse"
                  : backendStatus === "offline"
                  ? "bg-red-500"
                  : "bg-slate-500 animate-pulse"
              }`}
            />
            {backendStatus === "online" ? "API LIVE" : backendStatus === "offline" ? "API DOWN" : "CHECKING"}
          </div>
        </div>
      </div>

      {/* Main nav row */}
      <div className="px-6 py-3 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group shrink-0">
          <div className="relative w-10 h-10">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 via-orange-400 to-emerald-500 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-orange-500/30 group-hover:scale-105 transition-transform duration-200">
              R
            </div>
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#050810] animate-pulse" />
          </div>
          <div className="hidden sm:block">
            <div className="flex items-center gap-2">
              <span className="text-base font-black tracking-tight text-white">RAZORPAY</span>
              <span className="text-[10px] uppercase font-black text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20 tracking-widest">
                MANDATE
              </span>
            </div>
            <p className="text-[10px] text-slate-500 font-medium tracking-wide">AI Commerce Trust & Settlement Protocol</p>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1 bg-[#0c1120] border border-[#1e2d40] p-1.5 rounded-2xl">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all duration-200 ${
                  isActive
                    ? "bg-gradient-to-r from-orange-500/20 to-emerald-500/20 text-white border border-orange-500/30 shadow-lg shadow-orange-500/10"
                    : "text-slate-400 hover:text-white hover:bg-[#131f35]"
                }`}
              >
                <span className="text-base leading-none">{link.icon}</span>
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
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0c1120] border border-[#1e2d40] text-xs font-semibold text-slate-400 hover:text-white hover:border-indigo-500/40 transition-all duration-200"
          >
            <span className="text-sm">📖</span>
            <span>API Docs</span>
          </a>

          {/* Mobile menu button */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-lg bg-[#0c1120] border border-[#1e2d40] text-slate-400 hover:text-white transition"
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-[#1e2d40] bg-[#080d1a] px-4 py-3 flex flex-col gap-1">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold transition ${
                  isActive
                    ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                    : "text-slate-400 hover:text-white hover:bg-[#131f35]"
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
