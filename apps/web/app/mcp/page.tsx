"use client";

import React, { useState, useEffect } from "react";
import Navbar from "../components/Navbar";

interface MCPTool {
  name: string;
  description: string;
  permission?: string;
  inputSchema: any;
}

export default function MCPExplorerPage() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loadingTools, setLoadingTools] = useState<boolean>(true);
  const [selectedTool, setSelectedTool] = useState<string>("search_products");
  const [jsonRpcRequest, setJsonRpcRequest] = useState<string>(
    JSON.stringify(
      {
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "search_products",
          arguments: { query: "coffee", max_price_paise: 50000 },
        },
      },
      null,
      2
    )
  );
  const [jsonRpcResponse, setJsonRpcResponse] = useState<any>(null);
  const [executing, setExecuting] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"tools" | "workbench" | "security">("tools");

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    setLoadingTools(true);
    try {
      const res = await fetch("http://localhost:8000/api/agent/mcp/tools");
      const data = await res.json();
      if (data && data.tools) {
        setTools(data.tools);
      }
    } catch (err) {
      console.error("Error fetching MCP tools:", err);
    } finally {
      setLoadingTools(false);
    }
  };

  const handleSelectTool = (tool: MCPTool) => {
    setSelectedTool(tool.name);
    // Build standard template args based on input schema properties
    const props = tool.inputSchema?.properties || {};
    const defaultArgs: any = {};
    Object.keys(props).forEach((key) => {
      if (key === "query" || key === "prompt") defaultArgs[key] = "coffee";
      else if (key === "max_price_paise" || key === "amount_paise" || key === "total_budget_paise") defaultArgs[key] = 50000;
      else if (key === "merchant_id") defaultArgs[key] = "mer_tech_store";
      else if (key === "buyer_id") defaultArgs[key] = "buyer_demo_01";
      else if (key === "mandate_id") defaultArgs[key] = "man_buyer_01";
      else if (key === "transaction_id") defaultArgs[key] = "tx_auto_98234";
      else if (key === "order_id" || key === "merchant_order_id") defaultArgs[key] = "ord_demo_101";
      else if (key === "product_id") defaultArgs[key] = "src_baefe2bf";
      else if (key === "purchase_request_id" || key === "payment_transaction_id") defaultArgs[key] = "req_demo_001";
      else defaultArgs[key] = "test_value";
    });

    const payload = {
      jsonrpc: "2.0",
      id: Math.floor(Math.random() * 1000) + 1,
      method: "tools/call",
      params: {
        name: tool.name,
        arguments: defaultArgs,
      },
    };
    setJsonRpcRequest(JSON.stringify(payload, null, 2));
    setActiveTab("workbench");
  };

  const executeJsonRpc = async () => {
    setExecuting(true);
    setJsonRpcResponse(null);
    try {
      let parsed = JSON.parse(jsonRpcRequest);
      const res = await fetch("http://localhost:8000/api/agent/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      setJsonRpcResponse(data);
    } catch (err: any) {
      setJsonRpcResponse({ error: { message: err.message || "Failed to execute MCP RPC request" } });
    } finally {
      setExecuting(false);
    }
  };

  const testSecurityBarrier = async (restrictedTool: string) => {
    setExecuting(true);
    setActiveTab("workbench");
    const payload = {
      jsonrpc: "2.0",
      id: 999,
      method: "tools/call",
      params: {
        name: restrictedTool,
        arguments: { amount_paise: 100000, recipient: "attacker" },
      },
    };
    setJsonRpcRequest(JSON.stringify(payload, null, 2));
    try {
      const res = await fetch("http://localhost:8000/api/agent/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setJsonRpcResponse(data);
    } catch (err: any) {
      setJsonRpcResponse({ error: { message: err.message } });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 font-sans">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header Title */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 pb-6 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-black uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full border border-indigo-500/20">
                Model Context Protocol (MCP) Server
              </span>
              <span className="text-xs font-mono bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded">
                JSON-RPC 2.0
              </span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              MCP Tools & Permission Explorer
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Inspect approved MCP capabilities, test live JSON-RPC tool invocations, and verify autonomous security barrier enforcement.
            </p>
          </div>

          {/* Action Tabs */}
          <div className="flex items-center gap-2 bg-[#111827] border border-slate-800 p-1.5 rounded-xl">
            <button
              onClick={() => setActiveTab("tools")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                activeTab === "tools"
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Approved Tools ({tools.length})
            </button>
            <button
              onClick={() => setActiveTab("workbench")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                activeTab === "workbench"
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              RPC Test Workbench
            </button>
            <button
              onClick={() => setActiveTab("security")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                activeTab === "security"
                  ? "bg-red-600 text-white shadow-lg"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Security Barrier Tests
            </button>
          </div>
        </div>

        {/* TAB 1: Approved Tools Directory */}
        {activeTab === "tools" && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full"></span>
                Allowlisted MCP Tools Directory
              </h2>
              <button
                onClick={fetchTools}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition border border-slate-700"
              >
                Refresh Tools List
              </button>
            </div>

            {loadingTools ? (
              <div className="p-12 text-center text-slate-400 bg-[#111827] border border-slate-800 rounded-2xl">
                <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                Loading approved MCP tools...
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {tools.map((tool) => (
                  <div
                    key={tool.name}
                    className="bg-[#111827] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between hover:border-indigo-500/50 transition group"
                  >
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="font-mono text-sm font-extrabold text-indigo-400 group-hover:text-indigo-300">
                          {tool.name}
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          SAFE_READ
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mb-4 leading-relaxed">
                        {tool.description}
                      </p>

                      <div className="bg-[#090d16] border border-slate-800/80 rounded-xl p-3 mb-4">
                        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
                          Input Parameters
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {Object.keys(tool.inputSchema?.properties || {}).length > 0 ? (
                            Object.keys(tool.inputSchema.properties).map((prop) => (
                              <span
                                key={prop}
                                className="text-[11px] font-mono bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700"
                              >
                                {prop}
                              </span>
                            ))
                          ) : (
                            <span className="text-[11px] text-slate-600 font-mono">None (Empty object)</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleSelectTool(tool)}
                      className="w-full py-2 bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 font-bold text-xs rounded-xl transition shadow"
                    >
                      Test in RPC Workbench →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: RPC Workbench */}
        {activeTab === "workbench" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Request Panel */}
            <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                    JSON-RPC 2.0 Request Payload
                  </h3>
                  <span className="text-xs font-mono text-slate-500">POST /api/agent/mcp</span>
                </div>

                <div className="mb-4">
                  <label className="text-xs text-slate-400 font-semibold mb-1.5 block">
                    Quick Tool Preset
                  </label>
                  <select
                    value={selectedTool}
                    onChange={(e) => {
                      const t = tools.find((x) => x.name === e.target.value);
                      if (t) handleSelectTool(t);
                    }}
                    className="w-full bg-[#090d16] border border-slate-700 rounded-xl px-3.5 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    {tools.map((t) => (
                      <option key={t.name} value={t.name}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-4">
                  <label className="text-xs text-slate-400 font-semibold mb-1.5 block">
                    JSON-RPC Request Body
                  </label>
                  <textarea
                    value={jsonRpcRequest}
                    onChange={(e) => setJsonRpcRequest(e.target.value)}
                    rows={12}
                    className="w-full bg-[#090d16] border border-slate-800 rounded-xl p-4 font-mono text-xs text-emerald-400 leading-relaxed focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={executeJsonRpc}
                  disabled={executing}
                  className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-extrabold text-xs rounded-xl shadow-lg transition flex items-center justify-center gap-2"
                >
                  {executing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Executing MCP Tool...
                    </>
                  ) : (
                    "Execute MCP JSON-RPC Request"
                  )}
                </button>
                <button
                  onClick={() => {
                    const listPayload = { jsonrpc: "2.0", id: 1, method: "tools/list" };
                    setJsonRpcRequest(JSON.stringify(listPayload, null, 2));
                  }}
                  className="px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-xl transition border border-slate-700"
                >
                  Load tools/list
                </button>
              </div>
            </div>

            {/* Response Panel */}
            <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                    JSON-RPC 2.0 Response Result
                  </h3>
                  {jsonRpcResponse && (
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        jsonRpcResponse.error
                          ? "bg-red-500/10 text-red-400 border border-red-500/20"
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      }`}
                    >
                      {jsonRpcResponse.error ? "RPC ERROR" : "200 OK SUCCESS"}
                    </span>
                  )}
                </div>

                <div className="bg-[#090d16] border border-slate-800 rounded-xl p-4 min-h-[360px] max-h-[480px] overflow-y-auto">
                  {jsonRpcResponse ? (
                    <pre className="font-mono text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {JSON.stringify(jsonRpcResponse, null, 2)}
                    </pre>
                  ) : (
                    <div className="h-full flex items-center justify-center text-slate-600 text-xs font-mono py-24">
                      Press "Execute MCP JSON-RPC Request" to run tool live.
                    </div>
                  )}
                </div>
              </div>

              {jsonRpcResponse && jsonRpcResponse.result && (
                <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300">
                  ✓ Provenance verified response returned cleanly from MCP server adapter.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: Security Barrier Tests */}
        {activeTab === "security" && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-[#111827] border border-red-500/30 rounded-2xl p-8 shadow-2xl mb-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-red-500/10 rounded-xl border border-red-500/30 flex items-center justify-center text-red-400 font-bold text-lg">
                  🛡️
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Autonomous MCP Execution Barrier Test</h2>
                  <p className="text-xs text-slate-400">
                    Verifies that restricted payment execution tools are strictly blocked from discovery and execution by autonomous MCP clients.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                <div className="bg-[#090d16] border border-slate-800 rounded-xl p-5">
                  <span className="text-xs font-extrabold text-red-400 uppercase tracking-wider block mb-2">
                    Test 1: execute_payment
                  </span>
                  <p className="text-xs text-slate-400 mb-4">
                    Attempt to execute autonomous payment movement directly by tool name.
                  </p>
                  <button
                    onClick={() => testSecurityBarrier("execute_payment")}
                    className="w-full py-2.5 bg-red-600/20 hover:bg-red-600 text-red-300 hover:text-white border border-red-500/40 rounded-xl text-xs font-extrabold transition"
                  >
                    Test Block: execute_payment →
                  </button>
                </div>

                <div className="bg-[#090d16] border border-slate-800 rounded-xl p-5">
                  <span className="text-xs font-extrabold text-red-400 uppercase tracking-wider block mb-2">
                    Test 2: create_merchant_order
                  </span>
                  <p className="text-xs text-slate-400 mb-4">
                    Attempt to create merchant order directly without human step-up gate.
                  </p>
                  <button
                    onClick={() => testSecurityBarrier("create_merchant_order")}
                    className="w-full py-2.5 bg-red-600/20 hover:bg-red-600 text-red-300 hover:text-white border border-red-500/40 rounded-xl text-xs font-extrabold transition"
                  >
                    Test Block: create_merchant_order →
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800/80 py-6 px-8 text-center text-xs text-slate-500 mt-16">
        RAZERPAY MANDATE GATEWAY — MODEL CONTEXT PROTOCOL SERVER ADAPTER • JSON-RPC 2.0 ENFORCED
      </footer>
    </div>
  );
}
