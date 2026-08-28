"use client";

import React, { useState } from "react";

export default function MerchantPage() {
  const [aiCommerceEnabled, setAiCommerceEnabled] = useState(true);
  const [policyVersion, setPolicyVersion] = useState(1);
  const [autonomousLimitPaise, setAutonomousLimitPaise] = useState(500000);
  const [stepUpThresholdPaise, setStepUpThresholdPaise] = useState(1000000);
  const [allowedCategories, setAllowedCategories] = useState("electronics, clothing, books, supplies");
  const [savedStatus, setSavedStatus] = useState<string | null>(null);

  const handleSavePolicy = () => {
    setPolicyVersion(policyVersion + 1);
    setSavedStatus(`Policy v${policyVersion + 1} saved successfully.`);
    setTimeout(() => setSavedStatus(null), 3000);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <header className="border-b pb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Page B — Merchant AI Commerce Policy</h1>
          <p className="text-gray-600 text-sm">Configure autonomous AI commerce rules & operational guardrails</p>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-sm font-semibold">AI Commerce Status:</span>
          <button
            onClick={() => setAiCommerceEnabled(!aiCommerceEnabled)}
            className={`px-4 py-2 rounded text-sm font-bold text-white transition ${
              aiCommerceEnabled ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"
            }`}
          >
            {aiCommerceEnabled ? "ENABLED" : "DISABLED"}
          </button>
        </div>
      </header>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">Merchant Policy Overview</h2>
          <span className="text-xs bg-blue-100 text-blue-800 font-bold px-3 py-1 rounded">
            Policy Version: v{policyVersion}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Autonomous Purchase Limit (₹)
            </label>
            <input
              type="number"
              value={autonomousLimitPaise / 100}
              onChange={(e) => setAutonomousLimitPaise(Number(e.target.value) * 100)}
              className="w-full p-2 border rounded text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Single purchases below this limit execute automatically.</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Step-Up Approval Threshold (₹)
            </label>
            <input
              type="number"
              value={stepUpThresholdPaise / 100}
              onChange={(e) => setStepUpThresholdPaise(Number(e.target.value) * 100)}
              className="w-full p-2 border rounded text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Purchases above this limit require explicit buyer confirmation.</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">
            Allowed Product Categories (Comma-separated)
          </label>
          <input
            type="text"
            value={allowedCategories}
            onChange={(e) => setAllowedCategories(e.target.value)}
            className="w-full p-2 border rounded text-sm"
          />
        </div>

        <div className="pt-4 flex justify-between items-center">
          <button
            onClick={handleSavePolicy}
            className="bg-blue-600 text-white font-bold px-6 py-2 rounded text-sm hover:bg-blue-700"
          >
            Update & Publish Merchant Policy
          </button>
          {savedStatus && <span className="text-sm font-semibold text-green-600">{savedStatus}</span>}
        </div>
      </section>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">Allowed vs Blocked MCP Operations</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-4 bg-green-50 rounded border border-green-200">
            <h3 className="font-bold text-green-800 mb-2">Allowed Operations</h3>
            <ul className="list-disc list-inside text-green-700 space-y-1">
              <li>razorpay_create_order</li>
              <li>razorpay_create_payment_link</li>
              <li>razorpay_fetch_payment</li>
            </ul>
          </div>
          <div className="p-4 bg-red-50 rounded border border-red-200">
            <h3 className="font-bold text-red-800 mb-2">Blocked Operations</h3>
            <ul className="list-disc list-inside text-red-700 space-y-1">
              <li>razorpay_create_payout</li>
              <li>razorpay_bank_transfer</li>
              <li>razorpay_admin_settlement</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
