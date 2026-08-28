"use client";

import React, { useState } from "react";

interface MandateItem {
  id: string;
  buyerId: string;
  maxAmountPaise: number;
  dailyBudgetPaise: number;
  merchants: string[];
  categories: string[];
  expiresAt: string;
  status: "ACTIVE" | "REVOKED" | "EXPIRED";
}

const SAMPLE_MANDATES: MandateItem[] = [
  {
    id: "man_buyer_01",
    buyerId: "buy_user_99",
    maxAmountPaise: 500000,
    dailyBudgetPaise: 1000000,
    merchants: ["mer_tech_store", "mer_office_depot"],
    categories: ["electronics", "supplies"],
    expiresAt: "2026-12-31T23:59:59Z",
    status: "ACTIVE",
  },
  {
    id: "man_buyer_02",
    buyerId: "buy_user_99",
    maxAmountPaise: 1500000,
    dailyBudgetPaise: 2500000,
    merchants: ["mer_bookstore"],
    categories: ["books"],
    expiresAt: "2026-06-30T23:59:59Z",
    status: "ACTIVE",
  },
];

export default function MandatesPage() {
  const [mandates, setMandates] = useState<MandateItem[]>(SAMPLE_MANDATES);

  const handleRevoke = (id: string) => {
    setMandates(
      mandates.map((m) => (m.id === id ? { ...m, status: "REVOKED" as const } : m))
    );
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-bold">Page C — Buyer Mandates Dashboard</h1>
        <p className="text-gray-600 text-sm">Active authorization mandates, caps, scopes, and revocation</p>
      </header>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">Active Buyer Mandates</h2>
        <div className="space-y-4">
          {mandates.map((mandate) => (
            <div key={mandate.id} className="p-5 border rounded-lg bg-gray-50 space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-3">
                  <span className="font-bold text-md text-blue-900">{mandate.id}</span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-bold ${
                      mandate.status === "ACTIVE"
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {mandate.status}
                  </span>
                </div>
                {mandate.status === "ACTIVE" && (
                  <button
                    onClick={() => handleRevoke(mandate.id)}
                    className="text-xs bg-red-600 text-white font-semibold py-1.5 px-3 rounded hover:bg-red-700"
                  >
                    Revoke Mandate
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <div>
                  <span className="text-gray-500 block">Single Purchase Cap</span>
                  <span className="font-bold text-sm">₹{(mandate.maxAmountPaise / 100).toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Daily Budget</span>
                  <span className="font-bold text-sm">₹{(mandate.dailyBudgetPaise / 100).toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Authorized Merchants</span>
                  <span className="font-semibold">{mandate.merchants.join(", ")}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Allowed Categories</span>
                  <span className="font-semibold">{mandate.categories.join(", ")}</span>
                </div>
              </div>

              <div className="text-xs text-gray-500 pt-1 border-t">
                Expires: {new Date(mandate.expiresAt).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
