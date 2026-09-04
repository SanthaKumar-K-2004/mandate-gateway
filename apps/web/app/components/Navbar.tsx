"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "Command Hub" },
    { href: "/buyer", label: "Buyer Telemetry" },
    { href: "/mandates", label: "Mandates Studio" },
    { href: "/transactions", label: "Transactions" },
    { href: "/merchant", label: "Merchant Hub" },
    { href: "/mcp", label: "MCP Explorer" },
  ];

  return (
    <header className="border-b border-slate-800/80 px-6 py-4 bg-[#0d1322]/90 backdrop-blur-md sticky top-0 z-50 flex flex-wrap justify-between items-center gap-4">
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 bg-gradient-to-br from-orange-500 to-emerald-500 rounded-xl flex items-center justify-center font-black text-lg text-white shadow-lg shadow-orange-500/20 group-hover:scale-105 transition-transform">
            R
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-tight text-white m-0 flex items-center gap-2">
              RAZERPAY <span className="text-[10px] uppercase font-bold text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20">Gateway</span>
            </h1>
            <p className="text-[11px] text-slate-400 m-0">AI Commerce Trust & Settlement Protocol</p>
          </div>
        </Link>
      </div>

      <nav className="flex items-center gap-1.5 bg-[#111827] border border-slate-800 p-1.5 rounded-xl text-xs font-semibold">
        {navLinks.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                isActive
                  ? "bg-gradient-to-r from-orange-500/20 to-emerald-500/20 text-white font-bold border border-orange-500/30 shadow"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/50"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-full text-[11px] font-bold text-emerald-400">
        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
        GATEWAY ONLINE
      </div>
    </header>
  );
}
