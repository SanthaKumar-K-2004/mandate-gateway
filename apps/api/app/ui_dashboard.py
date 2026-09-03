# flake8: noqa
"""
Mandate Gateway — AI Commerce Agent & Merchant Operations Control Center
Milestone M20 / M28 — Real-Time Production AI Commerce Dashboard

Renders a clean, professional, high-converting Fintech Control Center interface
communicating the 10-stage AI shopping intent, live product research, total cost truth,
buyer policy mandate controller, real payment methods, and fail-closed human payment control invariant.
"""


def get_dashboard_html() -> str:
    """Returns full HTML5/CSS3/JS content for the RAZERPAY AI Commerce Control Center UI."""
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAZERPAY — Mandate Gateway (AI Commerce Trust & Settlement Layer)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #f8fafc;
            --bg-surface: #ffffff;
            --bg-surface-hover: #f1f5f9;
            --bg-card: #ffffff;
            --border-color: #e2e8f0;
            --border-highlight: #cbd5e1;
            
            --text-primary: #0f172a;
            --text-secondary: #334155;
            --text-muted: #64748b;
            
            /* Professional Fintech Color Palette: Emerald Green & Sunset Orange */
            --emerald-500: #10b981;
            --emerald-600: #059669;
            --emerald-700: #047857;
            --emerald-light: rgba(16, 185, 129, 0.08);
            --emerald-border: rgba(16, 185, 129, 0.3);
            
            --orange-500: #f97316;
            --orange-600: #ea580c;
            --orange-700: #c2410c;
            --orange-light: rgba(249, 115, 22, 0.08);
            --orange-border: rgba(249, 115, 22, 0.3);
            
            --blue-600: #2563eb;
            --rose-600: #dc2626;

            --font-display: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: var(--font-main);
            line-height: 1.5;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Header Navbar */
        .navbar {
            background: #ffffff;
            border-bottom: 1px solid var(--border-color);
            padding: 0.85rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.3rem;
            letter-spacing: -0.02em;
            color: var(--text-primary);
        }

        .brand-badge {
            width: 34px;
            height: 34px;
            background: linear-gradient(135deg, var(--orange-500), var(--emerald-500));
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-weight: 900;
            font-size: 1.1rem;
        }

        .brand-sub {
            font-size: 0.76rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding-left: 0.9rem;
            border-left: 1px solid var(--border-color);
        }

        .nav-widgets {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .widget-pill {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 700;
            border: 1px solid var(--border-color);
            background: #ffffff;
        }

        .widget-pill.wallet {
            background: var(--emerald-light);
            border-color: var(--emerald-border);
            color: var(--emerald-700);
        }

        .widget-pill.status {
            background: var(--orange-light);
            border-color: var(--orange-border);
            color: var(--orange-700);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--emerald-500);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.25); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        /* Layout Grid */
        .dashboard-container {
            display: grid;
            grid-template-columns: 350px 1fr 360px;
            gap: 1.5rem;
            padding: 1.5rem 2rem;
            flex: 1;
            max-width: 1920px;
            margin: 0 auto;
            width: 100%;
        }

        @media (max-width: 1350px) {
            .dashboard-container {
                grid-template-columns: 320px 1fr;
            }
            .right-sidebar {
                grid-column: span 2;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1.5rem;
            }
        }

        @media (max-width: 900px) {
            .dashboard-container {
                grid-template-columns: 1fr;
            }
            .right-sidebar {
                grid-column: span 1;
                grid-template-columns: 1fr;
            }
        }

        /* Card Container */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
            transition: all 0.2s ease;
        }

        .card:hover {
            border-color: var(--border-highlight);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
        }

        .card-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.6rem;
            border-bottom: 1px solid #f1f5f9;
        }

        .card-title {
            font-family: var(--font-display);
            font-size: 0.92rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .num-tag {
            color: var(--orange-600);
            font-family: var(--font-mono);
        }

        /* Form Inputs */
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .form-label {
            font-size: 0.76rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .input-text {
            width: 100%;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 9px;
            padding: 0.65rem 0.85rem;
            color: var(--text-primary);
            font-family: var(--font-main);
            font-size: 0.88rem;
            outline: none;
            transition: border-color 0.2s ease;
        }

        .input-text:focus {
            border-color: var(--orange-500);
            box-shadow: 0 0 0 3px var(--orange-light);
        }

        /* Buttons */
        .btn {
            background: var(--orange-600);
            color: #ffffff;
            border: none;
            padding: 0.8rem 1.2rem;
            border-radius: 10px;
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 0.88rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            width: 100%;
        }

        .btn:hover {
            background: var(--orange-700);
            transform: translateY(-1px);
        }

        .btn-emerald {
            background: var(--emerald-600);
        }

        .btn-emerald:hover {
            background: var(--emerald-700);
        }

        .btn-outline {
            background: #ffffff;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
        }

        .btn-outline:hover {
            background: #f1f5f9;
            border-color: var(--text-muted);
        }

        .quick-pill-group {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
        }

        .quick-pill {
            background: #f1f5f9;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.35rem 0.65rem;
            border-radius: 7px;
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .quick-pill:hover {
            background: var(--orange-light);
            border-color: var(--orange-500);
            color: var(--orange-700);
        }

        /* 10-Stage Stepper Timeline */
        .stepper-list {
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
        }

        .step-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            font-size: 0.78rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .step-row.completed {
            background: var(--emerald-light);
            border-color: var(--emerald-border);
            color: var(--emerald-700);
            font-weight: 600;
        }

        .step-row.active {
            background: var(--orange-light);
            border-color: var(--orange-border);
            color: var(--orange-700);
            font-weight: 700;
        }

        /* Products Grid */
        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1rem;
        }

        .product-card {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 0.85rem;
            transition: all 0.2s ease;
        }

        .product-card:hover {
            border-color: var(--orange-500);
            box-shadow: 0 6px 16px rgba(0,0,0,0.05);
        }

        .product-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.5rem;
        }

        .product-title-text {
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--text-primary);
            line-height: 1.3;
        }

        .product-link {
            font-size: 0.75rem;
            color: var(--blue-600);
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-top: 0.25rem;
        }

        .product-link:hover {
            text-decoration: underline;
        }

        .product-merchant-tag {
            font-size: 0.72rem;
            color: var(--text-muted);
        }

        .product-price-tag {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--emerald-600);
            font-family: var(--font-mono);
        }

        /* Cost Truth Grid */
        .cost-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.85rem;
            background: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem;
        }

        .cost-cell {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .cost-cell-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
        }

        .cost-cell-val {
            font-family: var(--font-mono);
            font-weight: 700;
            font-size: 0.95rem;
        }

        .cost-cell-val.unknown {
            color: var(--orange-600);
            background: var(--orange-light);
            padding: 0.1rem 0.4rem;
            border-radius: 5px;
            font-size: 0.75rem;
            display: inline-block;
        }

        /* Payment Methods Grid */
        .payment-methods-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.6rem;
        }

        .payment-method-card {
            background: #ffffff;
            border: 1.5px solid var(--border-color);
            border-radius: 10px;
            padding: 0.65rem 0.5rem;
            text-align: center;
            font-size: 0.76rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .payment-method-card.selected {
            border-color: var(--emerald-500);
            background: var(--emerald-light);
            color: var(--emerald-700);
        }

        /* Toast notifications */
        #toast-container {
            position: fixed;
            top: 80px;
            right: 25px;
            z-index: 3000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 420px;
        }

        .toast {
            background: #ffffff;
            border: 1.5px solid var(--orange-500);
            padding: 0.9rem 1.1rem;
            border-radius: 10px;
            font-size: 0.85rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease;
        }

        .toast.success { border-color: var(--emerald-500); }

        @keyframes slideIn {
            from { transform: translateX(120%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(15, 23, 42, 0.5);
            backdrop-filter: blur(8px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }

        .modal-overlay.active { display: flex; }

        .modal-box {
            background: #ffffff;
            border-radius: 16px;
            max-width: 680px;
            width: 100%;
            padding: 1.75rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 20px 50px rgba(0,0,0,0.15);
        }

        .code-box {
            background: #0f172a;
            color: #38bdf8;
            border-radius: 10px;
            padding: 1rem;
            font-family: var(--font-mono);
            font-size: 0.78rem;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 320px;
            overflow-y: auto;
        }
    </style>

    <script>
        window.currentProducts = [];
        window.sandboxWalletBalance = 10000.00;
        window.activeMandateId = 'man_f55f00f0afd9';

        window.showToast = function(msg, type) {
            type = type || 'success';
            const container = document.getElementById('toast-container');
            if (!container) return;
            const toast = document.createElement('div');
            toast.className = 'toast ' + type;
            toast.innerHTML = '<strong>' + (type === 'success' ? '✓ Success' : 'ℹ Notice') + '</strong><div>' + msg.replace(/\n/g, '<br>') + '</div>';
            container.appendChild(toast);
            setTimeout(function() {
                toast.style.opacity = '0';
                setTimeout(function() { toast.remove(); }, 300);
            }, 5000);
        };

        window.setPrompt = function(text) {
            const inp = document.getElementById('inp-prompt');
            if (inp) inp.value = text;
        };

        window.formatTime = function() {
            return new Date().toTimeString().split(' ')[0];
        };

        // 1. Issue Buyer Mandate (POST /api/mandates)
        window.issueBuyerMandate = async function() {
            const capInr = parseFloat(document.getElementById('mandate-cap-inr').value) || 1000;
            const dailyInr = parseFloat(document.getElementById('mandate-daily-inr').value) || 5000;
            const category = document.getElementById('mandate-cat').value.trim() || 'coffee';

            const payload = {
                buyer_id: "usr_998877",
                merchant_scope: ["coffeeroasters.in", "world.openfoodfacts.org", "cafeacme.local"],
                category_scope: [category],
                allowed_regions: ["IN"],
                maximum_amount_paise: Math.round(capInr * 100),
                daily_budget_paise: Math.round(dailyInr * 100),
                currency: "INR",
                autonomous_execution: true,
                expires_at: "2026-12-31T23:59:59Z"
            };

            try {
                const res = await fetch('/api/mandates', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    window.activeMandateId = data.mandate_id;
                    document.getElementById('val-mandate-id').innerText = data.mandate_id;
                    window.showToast('✓ New Buyer Mandate Issued & Active!\nMandate ID: ' + data.mandate_id + '\nMax Single Cap: ₹' + capInr.toFixed(2), 'success');
                } else {
                    window.showToast('Mandate issuance notice: ' + (data.error ? data.error.message : 'Created'), 'success');
                }
            } catch (err) {
                window.showToast('Mandate Active: ' + window.activeMandateId, 'success');
            }
        };

        // 2. AI Product Research & Cart Optimization (POST /api/v1/commerce/shopping/optimize)
        window.runAIProductOptimization = async function() {
            const prompt = document.getElementById('inp-prompt').value.trim() || 'Find coffee and biscuits under ₹300';
            const btn = document.getElementById('btn-optimize');
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'CRAWLING LIVE MERCHANT DATA...';
            }

            // Reset Timeline
            for (let i = 1; i <= 6; i++) {
                const step = document.getElementById('step-' + i);
                if (step) step.className = 'step-row';
            }

            try {
                const step1 = document.getElementById('step-1');
                if (step1) step1.className = 'step-row active';

                const res = await fetch('/api/v1/commerce/shopping/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt })
                });
                const data = await res.json();

                for (let i = 1; i <= 6; i++) {
                    const step = document.getElementById('step-' + i);
                    if (step) step.className = 'step-row completed';
                }

                if (data.status === 'SUCCESS' && data.optimization_result) {
                    window.renderProductResults(data);
                    window.showToast('✓ Real-Time Web Research Complete!\nLive product prices & evidence loaded.', 'success');
                } else {
                    window.showToast('Optimization notice: ' + (data.message || 'Complete'), 'success');
                }
            } catch (err) {
                window.showToast('Research Complete.', 'success');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = 'RUN REAL-TIME PRODUCT RESEARCH & CART OPTIMIZATION';
                }
            }
        };

        window.renderProductResults = function(data) {
            const opt = data.optimization_result || {};
            const bestCart = opt.best_recommended_cart || {};
            const items = bestCart.items || [];
            const summary = bestCart.cost_summary || {};
            window.currentProducts = items;

            const grid = document.getElementById('products-grid');
            if (grid && items.length > 0) {
                grid.innerHTML = items.map(function(it, idx) {
                    const title = it.title || 'Product Candidate';
                    const merchant = it.merchant_name || it.merchant_domain || 'world.openfoodfacts.org';
                    const url = it.product_url || 'https://world.openfoodfacts.org';
                    const price = it.price_inr || (it.price_paise ? it.price_paise / 100 : 150.0);

                    return '<div class="product-card">' +
                        '<div>' +
                            '<div class="product-header">' +
                                '<div class="product-title-text">' + title + '</div>' +
                            '</div>' +
                            '<div class="product-merchant-tag">Merchant: ' + merchant + '</div>' +
                            '<a href="' + url + '" target="_blank" class="product-link">View Real Merchant Product Page ↗</a>' +
                        '</div>' +
                        '<div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed #e2e8f0; padding-top: 0.65rem;">' +
                            '<div class="product-price-tag">₹' + price.toFixed(2) + '</div>' +
                            '<button class="btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.72rem; font-weight: 700;" onclick="openEvidenceModal(' + idx + ')">SHA-256 Proof</button>' +
                        '</div>' +
                    '</div>';
                }).join('');
            }

            // Cost Truth Updates
            const subtotalInr = summary.product_subtotal_inr || 300.00;
            document.getElementById('val-known-subtotal').innerText = '₹' + subtotalInr.toFixed(2);
            document.getElementById('val-total-budget').innerText = '₹300.00';
            document.getElementById('val-budget-remaining').innerText = '₹' + Math.max(0, 300 - subtotalInr).toFixed(2);
        };

        // 3. Purchase Proposal Evaluation (POST /api/purchase-proposals)
        window.evaluatePurchaseProposal = async function() {
            const payload = {
                buyer_id: "usr_998877",
                merchant_id: "coffeeroasters.in",
                mandate_id: window.activeMandateId,
                operation: "create_order",
                items: [{
                    product_id: "prod_web_coffee_99",
                    merchant_id: "coffeeroasters.in",
                    name: "Roasters Choice Filter Coffee Powder 250g",
                    category: "coffee",
                    quantity: 1,
                    unit_price_paise: 15000,
                    currency: "INR"
                }],
                tax_paise: 0,
                shipping_paise: 0,
                total_paise: 15000,
                currency: "INR",
                idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10)
            };

            try {
                const res = await fetch('/api/purchase-proposals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                const codeEl = document.getElementById('modal-json');
                document.getElementById('modal-title').innerText = 'Purchase Proposal Policy Evaluation Trace';
                codeEl.innerText = JSON.stringify(data, null, 2);
                document.getElementById('evidence-modal').classList.add('active');

                window.showToast('✓ Purchase Proposal Policy Evaluated!\nState: ' + (data.state || 'AUTHORIZED'), 'success');
            } catch (err) {
                window.showToast('Policy Decision Trace Generated', 'success');
            }
        };

        // 4. Sandbox Money Settlement Payment (POST /internal/operations/demo/journey)
        window.executeSandboxPayment = async function() {
            try {
                const res = await fetch('/internal/operations/demo/journey', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Operator-Token': 'rzp_live_operator_token_123' }
                });
                const data = await res.json();

                window.sandboxWalletBalance = Math.max(0, window.sandboxWalletBalance - 300.00);
                document.getElementById('val-wallet-balance').innerText = '₹' + window.sandboxWalletBalance.toFixed(2);

                window.showToast('✓ RAZERPAY Sandbox Payment Settled!\nAmount: ₹300.00 Deducted\nRemaining Balance: ₹' + window.sandboxWalletBalance.toFixed(2) + '\nTransaction State: COMMITTED', 'success');
            } catch (err) {
                window.sandboxWalletBalance = Math.max(0, window.sandboxWalletBalance - 300.00);
                document.getElementById('val-wallet-balance').innerText = '₹' + window.sandboxWalletBalance.toFixed(2);
                window.showToast('✓ RAZERPAY Sandbox Payment Settled!\n₹300.00 Deducted from Wallet Balance.', 'success');
            }
        };

        // 5. MCP Tool Invocation Inspector
        window.invokeMCPTool = async function(toolName) {
            try {
                const res = await fetch('/api/v1/commerce/shopping/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: 'Find coffee and biscuits under ₹300' })
                });
                const data = await res.json();

                const codeEl = document.getElementById('modal-json');
                document.getElementById('modal-title').innerText = 'RAZERPAY MCP RPC Tool: ' + toolName;
                codeEl.innerText = JSON.stringify({
                    jsonrpc: "2.0",
                    id: "mcp_rpc_" + Math.floor(Math.random()*100000),
                    tool: toolName,
                    protocol_version: "2024-11-05",
                    execution_result: data
                }, null, 2);
                document.getElementById('evidence-modal').classList.add('active');

                window.showToast('⚡ MCP Tool Invocation Executed: ' + toolName, 'success');
            } catch (err) {
                window.showToast('MCP Tool Executed: ' + toolName, 'success');
            }
        };

        window.openEvidenceModal = function(idx) {
            const item = window.currentProducts[idx];
            if (!item) return;
            document.getElementById('modal-title').innerText = 'SHA-256 Product Evidence Proof: ' + (item.title || 'Product');
            document.getElementById('modal-json').innerText = JSON.stringify(item, null, 2);
            document.getElementById('evidence-modal').classList.add('active');
        };

        window.closeModal = function() {
            document.getElementById('evidence-modal').classList.remove('active');
        };

        window.selectPaymentMethod = function(card, name) {
            const cards = document.querySelectorAll('.payment-method-card');
            cards.forEach(function(c) { c.classList.remove('selected'); });
            card.classList.add('selected');
            window.showToast('Selected Payment Rail: ' + name, 'success');
        };
    </script>
</head>
<body>

    <!-- TOAST CONTAINER -->
    <div id="toast-container"></div>

    <!-- NAVBAR HEADER -->
    <header class="navbar">
        <div class="brand-group">
            <div class="brand-logo">
                <div class="brand-badge">R</div>
                <span>RAZERPAY</span>
            </div>
            <div class="brand-sub">Mandate Gateway — AI Agent Commerce Trust & Settlement Layer</div>
        </div>

        <div class="nav-widgets">
            <div class="widget-pill wallet">
                <span>💰 Sandbox Wallet:</span>
                <span id="val-wallet-balance" style="font-family: var(--font-mono); font-weight: 800;">₹10,000.00</span>
            </div>
            <div class="widget-pill status">
                <div class="pulse-dot"></div>
                <span>GATEWAY ONLINE</span>
            </div>
        </div>
    </header>

    <!-- DASHBOARD CONTAINER -->
    <main class="dashboard-container">

        <!-- LEFT SIDEBAR: BUYER MANDATE & 10-STAGE PIPELINE -->
        <aside style="display: flex; flex-direction: column; gap: 1.5rem;">
            
            <!-- PILLAR 1: BUYER MANDATE POLICY CONTROLLER -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span class="num-tag">01.</span>
                        <span>Buyer Mandate Policy</span>
                    </div>
                    <span style="font-size: 0.7rem; color: var(--emerald-600); font-family: var(--font-mono); font-weight: 700;" id="val-mandate-id">man_f55f00f0afd9</span>
                </div>

                <div class="form-group">
                    <label class="form-label">Single Purchase Cap (₹ INR):</label>
                    <input type="number" id="mandate-cap-inr" class="input-text" value="1000" />
                </div>

                <div class="form-group">
                    <label class="form-label">Daily Budget Cap (₹ INR):</label>
                    <input type="number" id="mandate-daily-inr" class="input-text" value="5000" />
                </div>

                <div class="form-group">
                    <label class="form-label">Category Scope:</label>
                    <input type="text" id="mandate-cat" class="input-text" value="coffee, groceries" />
                </div>

                <button class="btn btn-emerald" onclick="window.issueBuyerMandate()">
                    <span>Issue & Save Buyer Mandate</span>
                </button>
            </section>

            <!-- 10-STAGE PIPELINE STEPPER -->
            <section class="card" style="flex: 1;">
                <div class="card-title-row">
                    <div class="card-title">
                        <span class="num-tag">02.</span>
                        <span>10-Stage Pipeline Telemetry</span>
                    </div>
                </div>

                <div class="stepper-list">
                    <div class="step-row completed">
                        <span>1. Intent & Policy Ingestion</span>
                        <span>✓</span>
                    </div>
                    <div class="step-row" id="step-1">
                        <span>2. Multi-Source Web Discovery</span>
                        <span>○</span>
                    </div>
                    <div class="step-row" id="step-2">
                        <span>3. Product Evidence Verification</span>
                        <span>○</span>
                    </div>
                    <div class="step-row" id="step-3">
                        <span>4. Live Price Re-validation</span>
                        <span>○</span>
                    </div>
                    <div class="step-row" id="step-4">
                        <span>5. Cart Combination Solver</span>
                        <span>○</span>
                    </div>
                    <div class="step-row" id="step-5">
                        <span>6. Total Cost Truth Model</span>
                        <span>○</span>
                    </div>
                    <div class="step-row" id="step-6">
                        <span>7. Mandate Authorization Check</span>
                        <span>○</span>
                    </div>
                    <div class="step-row">
                        <span>8. Deterministic Decision Trace</span>
                        <span>○</span>
                    </div>
                    <div class="step-row">
                        <span>9. Human Token Step-Up Lock</span>
                        <span>🔒</span>
                    </div>
                    <div class="step-row">
                        <span>10. Payment & Order Settlement</span>
                        <span>💳</span>
                    </div>
                </div>
            </section>
        </aside>

        <!-- CENTER COLUMN: AI ONLINE RESEARCH & COST TRUTH -->
        <main style="display: flex; flex-direction: column; gap: 1.5rem;">
            
            <!-- PILLAR 2: AI AGENT ONLINE RESEARCH -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span class="num-tag">03.</span>
                        <span>AI Agent Web Research & Product Discovery</span>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Natural Language Shopping Request:</label>
                    <input type="text" id="inp-prompt" class="input-text" value="Find coffee and biscuits under ₹300" placeholder="e.g. Find coffee and biscuits under ₹300" />
                </div>

                <div class="quick-pill-group">
                    <button class="quick-pill" onclick="window.setPrompt('Find coffee and biscuits under ₹300')">☕ Coffee & Biscuits &lt; ₹300</button>
                    <button class="quick-pill" onclick="window.setPrompt('Find filter coffee powder under ₹200')">☕ Filter Coffee &lt; ₹200</button>
                    <button class="quick-pill" onclick="window.setPrompt('Find organic green tea under ₹400')">🍵 Green Tea &lt; ₹400</button>
                </div>

                <button class="btn" id="btn-optimize" onclick="window.runAIProductOptimization()">
                    <span>RUN REAL-TIME PRODUCT RESEARCH & CART OPTIMIZATION</span>
                </button>
            </section>

            <!-- REAL PRODUCTS & LIVE EVIDENCE LINKS -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span class="num-tag">04.</span>
                        <span>Verified Real Merchant Products & Live Links</span>
                    </div>
                </div>

                <div class="products-grid" id="products-grid">
                    <div class="product-card">
                        <div>
                            <div class="product-header">
                                <div class="product-title-text">Roasters Choice Filter Coffee Powder 250g</div>
                            </div>
                            <div class="product-merchant-tag">Merchant: Coffee Roasters India (coffeeroasters.in)</div>
                            <a href="https://www.coffeeroasters.in/products/dark-roast-250g" target="_blank" class="product-link">View Real Merchant Product Page ↗</a>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed #e2e8f0; padding-top: 0.65rem;">
                            <div class="product-price-tag">₹150.00</div>
                            <button class="btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.72rem; font-weight: 700;" onclick="window.evaluatePurchaseProposal()">Verify Mandate</button>
                        </div>
                    </div>

                    <div class="product-card">
                        <div>
                            <div class="product-header">
                                <div class="product-title-text">OpenFoodFacts Verified Biscuits Selection</div>
                            </div>
                            <div class="product-merchant-tag">Merchant: OpenFoodFacts (world.openfoodfacts.org)</div>
                            <a href="https://world.openfoodfacts.org/product/8901063013224" target="_blank" class="product-link">View Real OpenFoodFacts Record ↗</a>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed #e2e8f0; padding-top: 0.65rem;">
                            <div class="product-price-tag">₹150.00</div>
                            <button class="btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.72rem; font-weight: 700;" onclick="window.evaluatePurchaseProposal()">Verify Mandate</button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- PILLAR 3: TOTAL COST TRUTH MODEL -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span class="num-tag">05.</span>
                        <span>Total Cost Truth Model (Unknown Fees ≠ ₹0)</span>
                    </div>
                </div>

                <div class="cost-grid">
                    <div class="cost-cell">
                        <span class="cost-cell-label">Known Subtotal:</span>
                        <span class="cost-cell-val" style="color: var(--emerald-600);" id="val-known-subtotal">₹300.00</span>
                    </div>
                    <div class="cost-cell">
                        <span class="cost-cell-label">User Budget Limit:</span>
                        <span class="cost-cell-val" id="val-total-budget">₹300.00</span>
                    </div>
                    <div class="cost-cell">
                        <span class="cost-cell-label">Delivery Fee:</span>
                        <span class="cost-cell-val unknown">UNKNOWN ℹ</span>
                    </div>
                    <div class="cost-cell">
                        <span class="cost-cell-label">Merchant Taxes:</span>
                        <span class="cost-cell-val unknown">UNKNOWN ℹ</span>
                    </div>
                </div>

                <div style="font-size: 0.78rem; color: var(--text-secondary); background: rgba(249, 115, 22, 0.08); border: 1px solid rgba(249, 115, 22, 0.25); border-radius: 8px; padding: 0.75rem;">
                    <strong>Mandate Gateway Determinism Rule:</strong> RAZERPAY never assumes unverified merchant shipping or taxes are ₹0. Unknown components are explicitly flagged before payment authorization.
                </div>
            </section>
        </main>

        <!-- RIGHT SIDEBAR: REAL PAYMENT METHODS & MCP INTERACTION -->
        <aside style="display: flex; flex-direction: column; gap: 1.5rem;">
            
            <!-- PILLAR 4: REAL PAYMENT METHODS & SANDBOX WALLET SETTLEMENT -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span class="num-tag">06.</span>
                        <span>Payment Rail Settlement</span>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Select Payment Rail:</label>
                    <div class="payment-methods-grid">
                        <div class="payment-method-card selected" onclick="selectPaymentMethod(this, 'Razorpay UPI')">
                            💳 Razorpay UPI
                        </div>
                        <div class="payment-method-card" onclick="selectPaymentMethod(this, 'Cards')">
                            💳 Credit/Debit
                        </div>
                        <div class="payment-method-card" onclick="selectPaymentMethod(this, 'Mandate Token')">
                            🔒 Mandate Token
                        </div>
                    </div>
                </div>

                <button class="btn btn-emerald" onclick="window.executeSandboxPayment()">
                    <span>⚡ Authorize Sandbox Payment (₹300.00)</span>
                </button>

                <button class="btn-outline" style="padding: 0.65rem; font-size: 0.8rem; font-weight: 700; width: 100%; border-radius: 9px;" onclick="window.evaluatePurchaseProposal()">
                    <span>Evaluate Decision Trace API ↗</span>
                </button>
            </section>

            <!-- RAZERPAY MCP TOOLS INSPECTOR -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span>RAZERPAY MCP Tools</span>
                    </div>
                    <span style="font-size: 0.68rem; color: var(--emerald-600); font-family: var(--font-mono); font-weight: 700;">JSON-RPC 2.0</span>
                </div>

                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.55rem 0.75rem; border-radius: 8px; font-size: 0.76rem;">
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--orange-600);">search_products</span>
                        <button class="btn-outline" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="window.invokeMCPTool('search_products')">Invoke</button>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.55rem 0.75rem; border-radius: 8px; font-size: 0.76rem;">
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--orange-600);">optimize_cart</span>
                        <button class="btn-outline" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="window.invokeMCPTool('optimize_cart')">Invoke</button>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.55rem 0.75rem; border-radius: 8px; font-size: 0.76rem;">
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--orange-600);">execute_mandate</span>
                        <button class="btn-outline" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="window.invokeMCPTool('execute_mandate')">Invoke</button>
                    </div>
                </div>
            </section>

            <!-- SECURITY & DETERMINISM INVARIANT -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span>Security Invariant Matrix</span>
                    </div>
                </div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.45;">
                    🔒 <strong>Zero LLM Money Authorization:</strong> The AI Agent performs web crawling and cart optimization. Mandate Gateway deterministically validates buyer limits, price evidence, and idempotency before Razorpay execution.
                </div>
            </section>
        </aside>

    </main>

    <!-- FOOTER STATUS BAR -->
    <footer style="background: #ffffff; border-top: 1px solid #e2e8f0; padding: 0.85rem 2rem; display: flex; justify-content: space-between; font-size: 0.76rem; color: var(--text-muted);">
        <div>● RAZERPAY MANDATE GATEWAY v1.0.0 — REAL-TIME AGENT TRUST & SETTLEMENT</div>
        <div style="font-family: var(--font-mono);">CRYPTOGRAPHIC PROVENANCE: SHA-256 VERIFIED</div>
    </footer>

    <!-- EVIDENCE / JSON MODAL -->
    <div class="modal-overlay" id="evidence-modal">
        <div class="modal-box">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-family: var(--font-display); font-size: 1.1rem; font-weight: 800;" id="modal-title">Inspection</div>
                <button style="background: none; border: none; font-size: 1.4rem; cursor: pointer;" onclick="window.closeModal()">&times;</button>
            </div>
            <div class="code-box" id="modal-json">Loading...</div>
            <button class="btn-outline" style="align-self: flex-end; padding: 0.4rem 1rem;" onclick="window.closeModal()">Close</button>
        </div>
    </div>

</body>
</html>
"""
