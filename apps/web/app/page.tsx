"use client";

import React from "react";

export default function HomePage() {
  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif", background: "#0b0f19", color: "#f8fafc", minHeight: "100vh" }}>
      <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.5rem" }}>Razerpay Mandate Gateway</h1>
      <p style={{ color: "#94a3b8", marginBottom: "2rem" }}>M18 — Production Deployment, Observability & Premium Product Experience</p>
      
      <div style={{ background: "#131b2e", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "1.5rem", maxWidth: "600px" }}>
        <h2 style={{ fontSize: "1.25rem", color: "#06b6d4", marginBottom: "0.75rem" }}>Operations Dashboard UI</h2>
        <p style={{ color: "#94a3b8", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
          Access the live interactive single-page dashboard at <code>/ui</code> or <code>/dashboard</code> on the backend API server.
        </p>
        <a 
          href="/dashboard" 
          style={{ display: "inline-block", background: "linear-gradient(135deg, #06b6d4, #8b5cf6)", color: "#ffffff", padding: "0.65rem 1.25rem", borderRadius: "8px", textDecoration: "none", fontWeight: 600, fontSize: "0.9rem" }}
        >
          Open Operations Dashboard &rarr;
        </a>
      </div>
    </div>
  );
}
