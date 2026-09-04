"use client";

import React, { useState, useEffect, useCallback } from "react";
import Navbar from "../components/Navbar";

interface MCPTool {
  name: string;
  description: string;
  permission?: string;
  inputSchema: { properties?: Record<string, any>; required?: string[] };
}

const DEFAULT_QUERIES: Record<string, object> = {
  search_products: { query: "coffee", max_price_paise: 50000 },
  check_mandate: { mandate_id: "man_buyer_01", amount_paise: 20000 },
  get_mandate_details: { mandate_id: "man_buyer_01" },
  get_product_details: { product_id: "src_baefe2bf" },
  get_merchant_catalog: { merchant_id: "mer_tech_store" },
  check_daily_limit: { mandate_id: "man_buyer_01", amount_paise: 15000 },
  get_buyer_mandates: { buyer_id: "buyer_demo_01" },
  verify_product_provenance: { product_id: "src_baefe2bf" },
  get_transaction_status: { transaction_id: "tx_auto_98234" },
  get_merchant_policies: { merchant_id: "mer_tech_store" },
};

function buildDefaultArgs(tool: MCPTool): object {
  const props = tool.inputSchema?.properties || {};
  const overrides = DEFAULT_QUERIES[tool.name];
  if (overrides) return overrides;
  const args: Record<string, any> = {};
  Object.keys(props).forEach((k) => {
    if (k.includes("query") || k.includes("prompt")) args[k] = "coffee";
    else if (k.includes("amount") || k.includes("paise") || k.includes("budget")) args[k] = 50000;
    else if (k.includes("merchant")) args[k] = "mer_tech_store";
    else if (k.includes("buyer")) args[k] = "buyer_demo_01";
    else if (k.includes("mandate")) args[k] = "man_buyer_01";
    else if (k.includes("transaction")) args[k] = "tx_auto_98234";
    else if (k.includes("product")) args[k] = "src_baefe2bf";
    else if (k.includes("order")) args[k] = "ord_demo_101";
    else args[k] = "test_value";
  });
  return args;
}

const PERMISSION_BADGE: Record<string, { label: string; bg: string; text: string; border: string }> = {
  SAFE_READ:  { label: "✓ SAFE_READ",  bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  WRITE:      { label: "⚠ WRITE",      bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20" },
  RESTRICTED: { label: "✕ RESTRICTED", bg: "bg-red-500/10",     text: "text-red-400",     border: "border-red-500/20" },
};

type Tab = "tools" | "workbench" | "security" | "docs";

export default function MCPExplorerPage() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loadingTools, setLoadingTools] = useState(true);
  const [filter, setFilter] = useState("");
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [jsonRpcRequest, setJsonRpcRequest] = useState("");
  const [jsonRpcResponse, setJsonRpcResponse] = useState<any>(null);
  const [executing, setExecuting] = useState(false);
  const [execTime, setExecTime] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("tools");
  const [parseError, setParseError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ tool: string; time: number; success: boolean }[]>([]);

  const fetchTools = useCallback(async () => {
    setLoadingTools(true);
    try {
      const res = await fetch("http://localhost:8000/api/agent/mcp/tools");
      const data = await res.json();
      if (data?.tools) {
        setTools(data.tools);
        if (!selectedTool && data.tools.length > 0) {
          loadTool(data.tools[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching MCP tools:", err);
    } finally {
      setLoadingTools(false);
    }
  }, []);

  useEffect(() => { fetchTools(); }, [fetchTools]);

  const loadTool = (tool: MCPTool) => {
    setSelectedTool(tool);
    const payload = {
      jsonrpc: "2.0",
      id: Math.floor(Math.random() * 9000) + 1000,
      method: "tools/call",
      params: { name: tool.name, arguments: buildDefaultArgs(tool) },
    };
    setJsonRpcRequest(JSON.stringify(payload, null, 2));
    setJsonRpcResponse(null);
    setParseError(null);
    setActiveTab("workbench");
  };

  const executeRpc = async () => {
    setParseError(null);
    let parsed: any;
    try {
      parsed = JSON.parse(jsonRpcRequest);
    } catch (e: any) {
      setParseError(`JSON Parse Error: ${e.message}`);
      return;
    }
    setExecuting(true);
    setJsonRpcResponse(null);
    const t0 = performance.now();
    try {
      const res = await fetch("http://localhost:8000/api/agent/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      const elapsed = Math.round(performance.now() - t0);
      setExecTime(elapsed);
      setJsonRpcResponse(data);
      setHistory((h) => [{ tool: parsed?.params?.name || parsed?.method || "rpc", time: elapsed, success: !data.error }, ...h.slice(0, 9)]);
    } catch (err: any) {
      setJsonRpcResponse({ error: { code: -32603, message: err.message || "Network error — is the API server running?" } });
    } finally {
      setExecuting(false);
    }
  };

  const testSecurityBarrier = async (toolName: string) => {
    const payload = {
      jsonrpc: "2.0", id: 999, method: "tools/call",
      params: { name: toolName, arguments: { amount_paise: 100000, recipient: "attacker_wallet" } },
    };
    setJsonRpcRequest(JSON.stringify(payload, null, 2));
    setActiveTab("workbench");
    setExecuting(true);
    setJsonRpcResponse(null);
    try {
      const res = await fetch("http://localhost:8000/api/agent/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setJsonRpcResponse(data);
      setHistory((h) => [{ tool: toolName, time: 0, success: false }, ...h.slice(0, 9)]);
    } catch (err: any) {
      setJsonRpcResponse({ error: { message: err.message } });
    } finally {
      setExecuting(false);
    }
  };

  const loadToolsList = () => {
    setJsonRpcRequest(JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }, null, 2));
    setJsonRpcResponse(null);
    setParseError(null);
  };

  const filteredTools = tools.filter(
    (t) => !filter || t.name.toLowerCase().includes(filter.toLowerCase()) || t.description.toLowerCase().includes(filter.toLowerCase())
  );

  const responseStr = jsonRpcResponse ? JSON.stringify(jsonRpcResponse, null, 2) : "";

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "tools", label: "Tool Registry", count: tools.length },
    { id: "workbench", label: "RPC Workbench" },
    { id: "security", label: "Security Tests" },
    { id: "docs", label: "Protocol Docs" },
  ];

  return (
    <div className="min-h-screen bg-[#050810] text-slate-100 font-sans">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-black uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full border border-indigo-500/20">
                  Model Context Protocol (MCP) Server
                </span>
                <span className="text-[10px] font-mono bg-[#0c1120] text-slate-400 px-2.5 py-1 rounded-lg border border-[#1e2d40]">
                  JSON-RPC 2.0
                </span>
                {!loadingTools && (
                  <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                    {tools.length} tools loaded
                  </span>
                )}
              </div>
              <h1 className="text-3xl font-black text-white tracking-tight">MCP Tool Gateway Explorer</h1>
              <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                Browse approved MCP capabilities, execute live JSON-RPC 2.0 tool invocations against the real backend, and verify autonomous AI security barriers.
              </p>
            </div>

            {/* Execution history mini */}
            {history.length > 0 && (
              <div className="bg-[#0c1120] border border-[#1e2d40] rounded-2xl p-3 min-w-[200px]">
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Recent Calls</p>
                <div className="space-y-1 max-h-20 overflow-y-auto">
                  {history.slice(0, 4).map((h, i) => (
                    <div key={i} className="flex items-center justify-between gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${h.success ? "bg-emerald-500" : "bg-red-500"}`} />
                      <span className="text-[10px] font-mono text-slate-400 truncate flex-1">{h.tool}</span>
                      {h.time > 0 && <span className="text-[10px] font-mono text-slate-600">{h.time}ms</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-2 mt-6 flex-wrap">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                  activeTab === tab.id
                    ? tab.id === "security"
                      ? "bg-red-600 text-white shadow-lg shadow-red-600/20"
                      : "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                    : "bg-[#0c1120] text-slate-400 hover:text-white border border-[#1e2d40] hover:border-[#2d4060]"
                }`}
              >
                {tab.id === "tools" && "📋"}
                {tab.id === "workbench" && "⚡"}
                {tab.id === "security" && "🛡️"}
                {tab.id === "docs" && "📖"}
                {tab.label}
                {tab.count !== undefined && (
                  <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-black ${
                    activeTab === tab.id ? "bg-white/20" : "bg-[#0a0f1e] text-slate-500"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* ─── TAB 1: Tool Registry ─────────────────────────────────────────── */}
        {activeTab === "tools" && (
          <div>
            {/* Search */}
            <div className="flex items-center gap-3 mb-5">
              <div className="relative flex-1 max-w-sm">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">🔍</span>
                <input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="Filter tools by name or description..."
                  className="w-full bg-[#0c1120] border border-[#1e2d40] rounded-xl pl-8 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition"
                />
              </div>
              <button
                onClick={fetchTools}
                className="px-4 py-2.5 bg-[#0c1120] border border-[#1e2d40] hover:border-indigo-500/40 rounded-xl text-xs font-bold text-slate-300 hover:text-white transition flex items-center gap-1.5"
              >
                🔄 Refresh
              </button>
              {filter && (
                <span className="text-xs text-slate-500">
                  {filteredTools.length} / {tools.length} tools
                </span>
              )}
            </div>

            {loadingTools ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="bg-[#0c1120] border border-[#1e2d40] rounded-2xl p-6 animate-pulse">
                    <div className="h-4 bg-[#1e2d40] rounded mb-3 w-2/3" />
                    <div className="h-3 bg-[#1e2d40] rounded mb-2 w-full" />
                    <div className="h-3 bg-[#1e2d40] rounded w-4/5" />
                  </div>
                ))}
              </div>
            ) : filteredTools.length === 0 ? (
              <div className="text-center py-16 text-slate-500">
                <div className="text-4xl mb-3">🔍</div>
                <p className="font-semibold">No tools match &quot;{filter}&quot;</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTools.map((tool) => {
                  const badge = PERMISSION_BADGE["SAFE_READ"];
                  const params = Object.keys(tool.inputSchema?.properties || {});
                  const required = tool.inputSchema?.required || [];
                  return (
                    <div
                      key={tool.name}
                      className="group bg-[#0c1120] border border-[#1e2d40] hover:border-indigo-500/40 rounded-2xl p-5 flex flex-col hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-500/5 transition-all duration-200"
                    >
                      {/* Tool name & permission */}
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="font-mono text-sm font-bold text-indigo-300 group-hover:text-indigo-200 transition leading-tight">
                          {tool.name}
                        </span>
                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border flex-shrink-0 ${badge.bg} ${badge.text} ${badge.border}`}>
                          {badge.label}
                        </span>
                      </div>

                      {/* Description */}
                      <p className="text-[11px] text-slate-400 leading-relaxed mb-4 flex-1 line-clamp-3">
                        {tool.description}
                      </p>

                      {/* Params */}
                      {params.length > 0 && (
                        <div className="mb-4">
                          <p className="text-[9px] font-bold uppercase tracking-widest text-slate-600 mb-1.5">Parameters</p>
                          <div className="flex flex-wrap gap-1">
                            {params.map((p) => (
                              <span
                                key={p}
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                                  required.includes(p)
                                    ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
                                    : "bg-[#0a0f1e] text-slate-500 border-[#1a2535]"
                                }`}
                              >
                                {p}{required.includes(p) ? "*" : ""}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => loadTool(tool)}
                        className="w-full py-2 rounded-xl bg-indigo-500/10 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/20 hover:border-indigo-500 text-xs font-bold transition-all duration-200"
                      >
                        Test in Workbench →
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 2: RPC Workbench ─────────────────────────────────────────── */}
        {activeTab === "workbench" && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {/* Request */}
            <div className="bg-[#0c1120] border border-[#1e2d40] rounded-2xl p-6 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full" />
                  <h3 className="text-sm font-bold text-white">JSON-RPC 2.0 Request</h3>
                </div>
                <span className="text-[10px] font-mono text-slate-500 bg-[#0a0f1e] border border-[#1a2535] px-2 py-0.5 rounded">
                  POST /api/agent/mcp
                </span>
              </div>

              {/* Tool selector */}
              <div className="mb-4">
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">Quick Tool Select</label>
                <select
                  value={selectedTool?.name || ""}
                  onChange={(e) => { const t = tools.find((x) => x.name === e.target.value); if (t) loadTool(t); }}
                  className="w-full bg-[#0a0f1e] border border-[#1e2d40] rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 transition"
                >
                  <option value="">— select a tool —</option>
                  {tools.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
                </select>
              </div>

              {/* JSON editor */}
              <div className="mb-4 flex-1">
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">Request Payload</label>
                <textarea
                  value={jsonRpcRequest}
                  onChange={(e) => { setJsonRpcRequest(e.target.value); setParseError(null); }}
                  rows={14}
                  spellCheck={false}
                  className={`w-full terminal-bg rounded-xl p-4 font-mono text-xs text-emerald-300 leading-relaxed focus:outline-none transition resize-none ${
                    parseError ? "border border-red-500/50" : "border border-[#1a2535] focus:border-indigo-500/60"
                  }`}
                />
                {parseError && (
                  <p className="text-[11px] text-red-400 mt-1 flex items-center gap-1">
                    <span>⚠</span> {parseError}
                  </p>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={executeRpc}
                  disabled={executing || !jsonRpcRequest}
                  className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-black text-xs rounded-xl shadow-lg shadow-indigo-600/20 transition-all duration-200 flex items-center justify-center gap-2"
                >
                  {executing ? (
                    <><div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> Executing...</>
                  ) : (
                    <><span>⚡</span> Execute MCP Call</>
                  )}
                </button>
                <button
                  onClick={loadToolsList}
                  className="px-4 py-3 bg-[#0a0f1e] border border-[#1e2d40] hover:border-[#2d4060] text-slate-300 hover:text-white font-bold text-xs rounded-xl transition"
                >
                  tools/list
                </button>
                <button
                  onClick={() => { setJsonRpcRequest(""); setJsonRpcResponse(null); setParseError(null); }}
                  className="px-4 py-3 bg-[#0a0f1e] border border-[#1e2d40] hover:border-red-500/30 text-slate-500 hover:text-red-400 font-bold text-xs rounded-xl transition"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Response */}
            <div className="bg-[#0c1120] border border-[#1e2d40] rounded-2xl p-6 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${jsonRpcResponse ? (jsonRpcResponse.error ? "bg-red-500" : "bg-emerald-500 animate-pulse") : "bg-slate-600"}`} />
                  <h3 className="text-sm font-bold text-white">JSON-RPC 2.0 Response</h3>
                </div>
                <div className="flex items-center gap-2">
                  {execTime !== null && (
                    <span className="text-[10px] font-mono text-slate-500">{execTime}ms</span>
                  )}
                  {jsonRpcResponse && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                      jsonRpcResponse.error
                        ? "bg-red-500/10 text-red-400 border-red-500/20"
                        : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    }`}>
                      {jsonRpcResponse.error ? "RPC ERROR" : "200 SUCCESS"}
                    </span>
                  )}
                </div>
              </div>

              <div className="terminal-bg rounded-xl p-4 flex-1 min-h-[380px] max-h-[500px] overflow-y-auto">
                {jsonRpcResponse ? (
                  <pre className="font-mono text-[11px] text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {responseStr}
                  </pre>
                ) : executing ? (
                  <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-600">
                    <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs font-mono">Executing MCP tool call...</span>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center gap-2 text-slate-700">
                    <span className="text-3xl">⚡</span>
                    <span className="text-xs font-mono">Press Execute to run a live tool call</span>
                    <span className="text-[10px] text-slate-700">Results appear here in real-time</span>
                  </div>
                )}
              </div>

              {jsonRpcResponse?.result && (
                <div className="mt-3 p-3 bg-emerald-500/5 border border-emerald-500/15 rounded-xl flex items-start gap-2">
                  <span className="text-emerald-400 flex-shrink-0">✓</span>
                  <p className="text-[11px] text-emerald-300">Provenance-verified response returned from MCP server adapter. Tool executed within approved permission scope.</p>
                </div>
              )}
              {jsonRpcResponse?.error && (
                <div className="mt-3 p-3 bg-red-500/5 border border-red-500/15 rounded-xl flex items-start gap-2">
                  <span className="text-red-400 flex-shrink-0">✕</span>
                  <p className="text-[11px] text-red-300">
                    {jsonRpcResponse.error.message || "RPC call returned an error response."}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─── TAB 3: Security Tests ────────────────────────────────────────── */}
        {activeTab === "security" && (
          <div className="max-w-4xl">
            <div className="bg-[#0c1120] border border-red-500/20 rounded-3xl p-8 mb-6">
              <div className="flex items-start gap-4 mb-6">
                <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0">🛡️</div>
                <div>
                  <h2 className="text-xl font-black text-white mb-1">Autonomous Execution Barrier Tests</h2>
                  <p className="text-sm text-slate-400">
                    Verifies that restricted payment-execution tools are strictly blocked from autonomous MCP discovery and invocation. These tests demonstrate our fail-closed security model.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  {
                    name: "execute_payment",
                    title: "Block: execute_payment",
                    desc: "Attempts direct autonomous payment movement — must be blocked at the MCP boundary layer.",
                    expected: "TOOL_NOT_FOUND or PERMISSION_DENIED",
                  },
                  {
                    name: "create_merchant_order",
                    title: "Block: create_merchant_order",
                    desc: "Attempts to create a merchant order without human step-up token — must be rejected.",
                    expected: "STEP_UP_REQUIRED",
                  },
                  {
                    name: "transfer_funds",
                    title: "Block: transfer_funds",
                    desc: "Direct fund transfer attempt — must be completely invisible to the MCP tool registry.",
                    expected: "TOOL_NOT_FOUND",
                  },
                  {
                    name: "delete_mandate",
                    title: "Block: delete_mandate",
                    desc: "Unauthorized mandate deletion — must require human authorization token.",
                    expected: "UNAUTHORIZED",
                  },
                ].map((test) => (
                  <div key={test.name} className="bg-[#080d18] border border-[#1e2d40] rounded-2xl p-5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2 h-2 bg-red-500 rounded-full" />
                      <span className="text-xs font-black text-red-400 uppercase tracking-wide">{test.title}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-2">{test.desc}</p>
                    <p className="text-[10px] font-mono text-amber-500/70 mb-4">
                      Expected: {test.expected}
                    </p>
                    <button
                      onClick={() => testSecurityBarrier(test.name)}
                      className="w-full py-2.5 rounded-xl bg-red-500/10 hover:bg-red-600 text-red-300 hover:text-white border border-red-500/30 hover:border-red-500 text-xs font-bold transition-all duration-200"
                    >
                      Run Security Test →
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-[#0c1120] border border-emerald-500/20 rounded-2xl p-6">
              <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                <span>✅</span> Security Architecture
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { title: "Allowlist-only Registry", desc: "Only explicitly approved tools are discoverable via tools/list. No wildcard access.", icon: "📋" },
                  { title: "Fail-Closed Policy", desc: "Unknown or unlisted tools return TOOL_NOT_FOUND — never silent pass-through.", icon: "🔒" },
                  { title: "Human Gate Required", desc: "Payment execution always requires a signed human step-up token. AI cannot self-authorize.", icon: "👤" },
                ].map((item) => (
                  <div key={item.title} className="bg-[#080d18] border border-emerald-500/10 rounded-xl p-4">
                    <div className="text-2xl mb-2">{item.icon}</div>
                    <h4 className="text-xs font-bold text-emerald-400 mb-1">{item.title}</h4>
                    <p className="text-[10px] text-slate-500 leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── TAB 4: Protocol Docs ─────────────────────────────────────────── */}
        {activeTab === "docs" && (
          <div className="max-w-4xl space-y-5">
            <div className="bg-[#0c1120] border border-[#1e2d40] rounded-2xl p-6">
              <h2 className="text-lg font-black text-white mb-4">MCP JSON-RPC 2.0 Protocol</h2>
              <div className="space-y-4">
                {[
                  {
                    method: "tools/list",
                    endpoint: "POST /api/agent/mcp",
                    desc: "Returns all allowlisted MCP tools with their input schemas. Used by AI agents to discover available capabilities.",
                    body: `{ "jsonrpc": "2.0", "id": 1, "method": "tools/list" }`,
                  },
                  {
                    method: "tools/call",
                    endpoint: "POST /api/agent/mcp",
                    desc: "Executes a specific MCP tool by name with provided arguments. Returns typed result from the tool handler.",
                    body: `{\n  "jsonrpc": "2.0",\n  "id": 2,\n  "method": "tools/call",\n  "params": {\n    "name": "search_products",\n    "arguments": { "query": "coffee", "max_price_paise": 50000 }\n  }\n}`,
                  },
                  {
                    method: "GET /api/agent/mcp/tools",
                    endpoint: "GET /api/agent/mcp/tools",
                    desc: "REST alternative for tools discovery. Returns count and full tool metadata without JSON-RPC wrapper.",
                    body: `curl http://localhost:8000/api/agent/mcp/tools`,
                  },
                ].map((doc) => (
                  <div key={doc.method} className="border border-[#1e2d40] rounded-xl overflow-hidden">
                    <div className="flex items-center gap-3 px-4 py-3 bg-[#080d18]">
                      <span className="font-mono text-xs font-black text-indigo-300">{doc.method}</span>
                      <span className="text-[10px] font-mono text-slate-600">{doc.endpoint}</span>
                    </div>
                    <div className="px-4 py-3">
                      <p className="text-xs text-slate-400 mb-3">{doc.desc}</p>
                      <pre className="terminal-bg rounded-lg p-3 text-[11px] font-mono text-emerald-300 overflow-x-auto">{doc.body}</pre>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-[#1e2d40]/60 py-6 px-6 text-center text-[10px] text-slate-600 font-mono mt-12">
        RAZORPAY MANDATE GATEWAY — MODEL CONTEXT PROTOCOL SERVER • JSON-RPC 2.0 • ALLOWLIST-ONLY TOOL REGISTRY
      </footer>
    </div>
  );
}
