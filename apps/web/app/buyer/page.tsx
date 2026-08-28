"use client";

import React, { useState } from "react";

interface Product {
  id: string;
  name: string;
  category: string;
  pricePaise: number;
  description: string;
}

const SAMPLE_PRODUCTS: Product[] = [
  { id: "prd_101", name: "Ergonomic Office Chair", category: "supplies", pricePaise: 450000, description: "Lumbar support ergonomic chair." },
  { id: "prd_102", name: "Wireless Mechanical Keyboard", category: "electronics", pricePaise: 250000, description: "Tactile switch wireless keyboard." },
  { id: "prd_103", name: "Ultra-wide 4K Monitor", category: "electronics", pricePaise: 1200000, description: "34-inch curved productivity display." }
];

export default function BuyerPage() {
  const [userIntent, setUserIntent] = useState("Find ergonomic office supplies under ₹5,000.");
  const [selectedMandate, setSelectedMandate] = useState("man_buyer_01");
  const [cart, setCart] = useState<Product[]>([]);
  const [purchaseStatus, setPurchaseStatus] = useState<string | null>(null);

  const addToCart = (product: Product) => {
    setCart([...cart, product]);
  };

  const handleExecutePurchase = async () => {
    setPurchaseStatus("EVALUATING_AUTHORIZATION...");
    const totalAmount = cart.reduce((sum, item) => sum + item.pricePaise, 0);

    setTimeout(() => {
      if (totalAmount > 500000) {
        setPurchaseStatus("STEP_UP_REQUIRED — Autonomous limit exceeded (Cap: ₹5,000)");
      } else {
        setPurchaseStatus("AUTHORIZED & COMMITTED — Transaction ID: tx_auto_98234");
      }
    }, 800);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-bold">Page A — AI Buyer Control Interface</h1>
        <p className="text-gray-600 text-sm">Autonomous AI intent execution & purchase mandate binding</p>
      </header>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">1. User Intent Prompt</h2>
        <input
          type="text"
          value={userIntent}
          onChange={(e) => setUserIntent(e.target.value)}
          className="w-full p-3 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter buyer intent..."
        />
        <div className="flex items-center space-x-4 text-sm">
          <label className="font-medium">Active Mandate Binding:</label>
          <select
            value={selectedMandate}
            onChange={(e) => setSelectedMandate(e.target.value)}
            className="p-2 border rounded"
          >
            <option value="man_buyer_01">Mandate #man_buyer_01 (Max: ₹5,000 / Daily: ₹10,000)</option>
            <option value="man_buyer_02">Mandate #man_buyer_02 (Max: ₹15,000 / Daily: ₹25,000)</option>
          </select>
        </div>
      </section>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">2. Recommended Catalog Products</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SAMPLE_PRODUCTS.map((prod) => (
            <div key={prod.id} className="p-4 border rounded hover:shadow-md transition">
              <h3 className="font-bold text-md">{prod.name}</h3>
              <p className="text-xs text-gray-500 capitalize">Category: {prod.category}</p>
              <p className="text-sm font-semibold mt-2 text-blue-600">₹{(prod.pricePaise / 100).toLocaleString()}</p>
              <button
                onClick={() => addToCart(prod)}
                className="mt-3 w-full bg-blue-600 text-white text-xs font-semibold py-2 px-3 rounded hover:bg-blue-700"
              >
                Add to AI Cart
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white p-6 rounded shadow-sm border space-y-4">
        <h2 className="text-lg font-semibold">3. AI Buyer Cart & Purchase Execution</h2>
        {cart.length === 0 ? (
          <p className="text-gray-500 text-sm">Cart is empty. Select a recommended product above.</p>
        ) : (
          <div className="space-y-3">
            {cart.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center text-sm p-2 border-b">
                <span>{item.name}</span>
                <span className="font-semibold">₹{(item.pricePaise / 100).toLocaleString()}</span>
              </div>
            ))}
            <div className="flex justify-between items-center text-base font-bold pt-2">
              <span>Total Amount:</span>
              <span>₹{(cart.reduce((sum, i) => sum + i.pricePaise, 0) / 100).toLocaleString()}</span>
            </div>
            <button
              onClick={handleExecutePurchase}
              className="mt-4 w-full bg-green-600 text-white font-bold py-3 rounded hover:bg-green-700 transition"
            >
              Authorize & Execute AI Purchase Proposal
            </button>
          </div>
        )}
        {purchaseStatus && (
          <div className="mt-4 p-4 rounded bg-gray-900 text-green-400 font-mono text-sm">
            Status: {purchaseStatus}
          </div>
        )}
      </section>
    </div>
  );
}
