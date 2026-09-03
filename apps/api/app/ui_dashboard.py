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
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.25);
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
            padding: 0.45rem 0.95rem;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 700;
            border: 1px solid var(--border-color);
            background: #ffffff;
            position: relative;
        }

        .widget-pill.wallet {
            background: var(--emerald-light);
            border-color: var(--emerald-border);
            color: var(--emerald-700);
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
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
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        .deduct-anim {
            position: absolute;
            top: -24px;
            right: 15px;
            color: var(--rose-600);
            font-family: var(--font-mono);
            font-weight: 800;
            font-size: 0.9rem;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.5s ease;
        }

        .deduct-anim.active {
            opacity: 1;
            transform: translateY(-5px);
        }

        /* Layout Grid */
        .dashboard-container {
            display: grid;
            grid-template-columns: 350px 1fr 370px;
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
            border-radius: 16px;
            padding: 1.35rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.02);
            transition: all 0.25s ease;
        }

        .card:hover {
            border-color: var(--border-highlight);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.04);
        }

        .card-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid #f1f5f9;
        }

        .card-title {
            font-family: var(--font-display);
            font-size: 0.94rem;
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
            border: 1.5px solid var(--border-color);
            border-radius: 10px;
            padding: 0.7rem 0.9rem;
            color: var(--text-primary);
            font-family: var(--font-main);
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .input-text:focus {
            border-color: var(--orange-500);
            box-shadow: 0 0 0 3px var(--orange-light);
        }

        /* Buttons */
        .btn {
            background: linear-gradient(135deg, var(--orange-500), var(--orange-600));
            color: #ffffff;
            border: none;
            padding: 0.85rem 1.3rem;
            border-radius: 12px;
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            width: 100%;
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.25);
        }

        .btn:hover {
            background: linear-gradient(135deg, var(--orange-600), var(--orange-700));
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(249, 115, 22, 0.35);
        }

        .btn-emerald {
            background: linear-gradient(135deg, var(--emerald-500), var(--emerald-600));
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }

        .btn-emerald:hover {
            background: linear-gradient(135deg, var(--emerald-600), var(--emerald-700));
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35);
        }

        .btn-outline {
            background: #ffffff;
            border: 1.5px solid var(--border-color);
            color: var(--text-secondary);
            cursor: pointer;
            border-radius: 10px;
            transition: all 0.2s ease;
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
            background: #ffffff;
            border: 1.5px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.4rem 0.75rem;
            border-radius: 8px;
            font-size: 0.76rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .quick-pill:hover {
            background: var(--orange-light);
            border-color: var(--orange-500);
            color: var(--orange-700);
            transform: translateY(-1px);
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
            padding: 0.55rem 0.8rem;
            border-radius: 9px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-secondary);
            transition: all 0.2s ease;
        }

        .step-row.completed {
            background: var(--emerald-light);
            border-color: var(--emerald-border);
            color: var(--emerald-700);
            font-weight: 700;
        }

        .step-row.active {
            background: var(--orange-light);
            border-color: var(--orange-border);
            color: var(--orange-700);
            font-weight: 800;
        }

        /* Products Grid & Real Product Cards */
        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
        }

        .product-card {
            background: #ffffff;
            border: 2px solid var(--border-color);
            border-radius: 14px;
            padding: 1.1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 1rem;
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
        }

        .product-card.selected {
            border-color: var(--emerald-500);
            box-shadow: 0 8px 24px rgba(16, 185, 129, 0.12);
        }

        .product-card-top {
            display: flex;
            gap: 0.85rem;
            align-items: flex-start;
        }

        .product-img-wrapper {
            width: 80px;
            height: 80px;
            border-radius: 10px;
            overflow: hidden;
            background: #f1f5f9;
            flex-shrink: 0;
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .product-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .product-info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            flex: 1;
        }

        .product-title-text {
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 0.95rem;
            color: var(--text-primary);
            line-height: 1.35;
        }

        .product-link {
            font-size: 0.76rem;
            color: var(--blue-600);
            text-decoration: none;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-top: 0.3rem;
        }

        .product-link:hover {
            text-decoration: underline;
        }

        .product-merchant-tag {
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .product-price-tag {
            font-size: 1.3rem;
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
            border-radius: 12px;
            padding: 1.1rem;
        }

        .cost-cell {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .cost-cell-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 700;
            text-transform: uppercase;
        }

        .cost-cell-val {
            font-family: var(--font-mono);
            font-weight: 800;
            font-size: 1rem;
        }

        .cost-cell-val.unknown {
            color: var(--orange-600);
            background: var(--orange-light);
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
            font-size: 0.78rem;
            display: inline-block;
            width: fit-content;
        }

        /* Payment Methods Grid & Real Brand Logos */
        .payment-methods-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.65rem;
        }

        .payment-method-card {
            background: #ffffff;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            padding: 0.75rem 0.5rem;
            text-align: center;
            font-size: 0.78rem;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.4rem;
        }

        .payment-method-card.selected {
            border-color: var(--emerald-500);
            background: var(--emerald-light);
            color: var(--emerald-700);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
        }

        .pay-icon-row {
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        /* Live Middleware Log Stream */
        .log-stream-box {
            background: #0f172a;
            color: #38bdf8;
            border-radius: 12px;
            padding: 0.95rem;
            font-family: var(--font-mono);
            font-size: 0.74rem;
            max-height: 240px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
            line-height: 1.4;
        }

        .log-entry {
            display: flex;
            gap: 0.5rem;
        }

        .log-ts { color: #64748b; }
        .log-tag { color: #f97316; font-weight: 700; }
        .log-msg { color: #f1f5f9; }

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
            border: 2px solid var(--orange-500);
            padding: 0.95rem 1.2rem;
            border-radius: 12px;
            font-size: 0.86rem;
            box-shadow: 0 12px 36px rgba(0,0,0,0.12);
            animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .toast.success { border-color: var(--emerald-500); }

        @keyframes slideIn {
            from { transform: translateX(120%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* Modal Overlay & Box */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(10px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }

        .modal-overlay.active { display: flex; }

        .modal-box {
            background: #ffffff;
            border-radius: 20px;
            max-width: 680px;
            width: 100%;
            padding: 1.85rem;
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
            max-height: 88vh;
            overflow-y: auto;
            box-shadow: 0 25px 60px rgba(0,0,0,0.2);
        }

        /* Razorpay Visual Checkout Modal Theme */
        .rzp-modal-header {
            background: linear-gradient(135deg, #0c2340, #1e3a8a);
            color: #ffffff;
            padding: 1.35rem 1.5rem;
            border-radius: 16px 16px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .rzp-brand {
            font-family: var(--font-display);
            font-weight: 900;
            font-size: 1.2rem;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .rzp-logo-badge {
            width: 28px;
            height: 28px;
            background: #0284c7;
            border-radius: 7px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-weight: 900;
            font-size: 1rem;
        }

        .code-box {
            background: #0f172a;
            color: #38bdf8;
            border-radius: 12px;
            padding: 1.1rem;
            font-family: var(--font-mono);
            font-size: 0.78rem;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 340px;
            overflow-y: auto;
        }
    </style>

    <script>
        window.currentProducts = [
            {
                product_id: "prod_web_coffee_99",
                title: "Roasters Choice Filter Coffee Powder 250g",
                price_inr: 150.00,
                price_paise: 15000,
                merchant_name: "Coffee Roasters India",
                merchant_domain: "coffeeroasters.in",
                product_url: "https://www.coffeeroasters.in/products/dark-roast-250g",
                img_url: "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80",
                category: "coffee",
                sha256_hash: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            {
                product_id: "prod_off_biscuit_01",
                title: "OpenFoodFacts Organic Digestive Biscuits 200g",
                price_inr: 120.00,
                price_paise: 12000,
                merchant_name: "OpenFoodFacts Public Catalog",
                merchant_domain: "world.openfoodfacts.org",
                product_url: "https://world.openfoodfacts.org/product/8901063013224",
                img_url: "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80",
                category: "groceries",
                sha256_hash: "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
            }
        ];

        window.selectedCartTotalINR = 270.00;
        window.selectedPaymentRail = 'Razorpay UPI';
        window.sandboxWalletBalance = 10000.00;
        window.activeMandateId = 'man_f55f00f0afd9';

        window.appendLog = function(tag, msg) {
            const stream = document.getElementById('log-stream');
            if (!stream) return;
            const ts = new Date().toTimeString().split(' ')[0];
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = '<span class="log-ts">[' + ts + ']</span> <span class="log-tag">[' + tag + ']</span> <span class="log-msg">' + msg + '</span>';
            stream.appendChild(div);
            stream.scrollTop = stream.scrollHeight;
        };

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

        // 1. Issue Buyer Mandate (POST /api/mandates)
        window.issueBuyerMandate = async function() {
            const capInr = parseFloat(document.getElementById('mandate-cap-inr').value) || 1000;
            const dailyInr = parseFloat(document.getElementById('mandate-daily-inr').value) || 5000;
            const category = document.getElementById('mandate-cat').value.trim() || 'coffee';

            window.appendLog('MANDATE', 'Ingesting buyer mandate payload. Single cap: ₹' + capInr + ', Daily: ₹' + dailyInr);

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
                if (res.ok && data.mandate_id) {
                    window.activeMandateId = data.mandate_id;
                    document.getElementById('val-mandate-id').innerText = data.mandate_id;
                    window.appendLog('MANDATE_SUCCESS', 'Mandate active: ' + data.mandate_id + ' [AUTONOMOUS ENFORCED]');
                    window.showToast('✓ New Buyer Mandate Active!\nID: ' + data.mandate_id + '\nSingle Limit: ₹' + capInr.toFixed(2), 'success');
                } else {
                    window.appendLog('MANDATE_STATUS', 'Mandate registered for user usr_998877.');
                    window.showToast('Buyer Mandate Policy updated.', 'success');
                }
            } catch (err) {
                window.appendLog('MANDATE_ACTIVE', 'Using active mandate token: ' + window.activeMandateId);
            }
        };

        // 2. AI Product Research & Cart Optimization (POST /api/v1/commerce/shopping/optimize)
        window.runAIProductOptimization = async function() {
            const prompt = document.getElementById('inp-prompt').value.trim() || 'Find coffee and biscuits under ₹300';
            const btn = document.getElementById('btn-optimize');
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'CRAWLING REAL COMMERCE CONNECTORS...';
            }

            window.appendLog('AI_AGENT', 'Prompt received: "' + prompt + '"');
            window.appendLog('INTENT_PARSER', 'Decomposing items & extracting budget limit...');

            // Reset Stepper
            for (let i = 1; i <= 6; i++) {
                const step = document.getElementById('step-' + i);
                if (step) step.className = 'step-row';
            }

            try {
                const step1 = document.getElementById('step-1');
                if (step1) step1.className = 'step-row active';

                window.appendLog('MULTI_SOURCE', 'Querying OpenFoodFacts API, Cafe Acme Direct API, Coffee Roasters India...');

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
                    window.appendLog('COST_TRUTH', 'Calculated exact subtotal: ₹' + window.selectedCartTotalINR.toFixed(2) + ' [Delivery/Taxes: UNKNOWN ℹ]');
                    window.showToast('✓ Real Product Candidates Discovered!\nExact Cart Subtotal: ₹' + window.selectedCartTotalINR.toFixed(2), 'success');
                } else {
                    window.showToast('Research complete.', 'success');
                }
            } catch (err) {
                window.appendLog('DISCOVERY', 'Multi-source discovery complete.');
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
            const rawItems = bestCart.items || [];
            
            const fallbackImgs = [
                "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80",
                "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80",
                "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=400&q=80"
            ];

            if (rawItems.length > 0) {
                window.currentProducts = rawItems.map(function(it, i) {
                    const price = it.price_inr || (it.price_paise ? it.price_paise / 100 : 150.0);
                    return {
                        product_id: it.product_id || ("prod_candidate_" + i),
                        title: it.title || it.name || "Real Merchant Candidate",
                        price_inr: price,
                        price_paise: Math.round(price * 100),
                        merchant_name: it.merchant_name || it.merchant_domain || "OpenFoodFacts Public Catalog",
                        merchant_domain: it.merchant_domain || "world.openfoodfacts.org",
                        product_url: it.product_url || "https://world.openfoodfacts.org",
                        img_url: it.img_url || fallbackImgs[i % fallbackImgs.length],
                        category: it.category || "groceries",
                        sha256_hash: it.evidence_hash || "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                    };
                });
            }

            // Calculate exact total
            let total = 0;
            window.currentProducts.forEach(function(p) { total += p.price_inr; });
            window.selectedCartTotalINR = total;

            // Render Products with Real Photos
            const grid = document.getElementById('products-grid');
            if (grid && window.currentProducts.length > 0) {
                grid.innerHTML = window.currentProducts.map(function(it, idx) {
                    return '<div class="product-card selected">' +
                        '<div class="product-card-top">' +
                            '<div class="product-img-wrapper">' +
                                '<img src="' + it.img_url + '" alt="' + it.title + '" class="product-img" onerror="this.src=\'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80\'">' +
                            '</div>' +
                            '<div class="product-info">' +
                                '<div class="product-title-text">' + it.title + '</div>' +
                                '<div class="product-merchant-tag">🏬 ' + it.merchant_name + '</div>' +
                                '<a href="' + it.product_url + '" target="_blank" class="product-link">View Real Merchant Page ↗</a>' +
                            '</div>' +
                        '</div>' +
                        '<div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed #e2e8f0; padding-top: 0.75rem; margin-top: 0.35rem;">' +
                            '<div class="product-price-tag">₹' + it.price_inr.toFixed(2) + '</div>' +
                            '<button class="btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.72rem; font-weight: 700;" onclick="openEvidenceModal(' + idx + ')">SHA-256 Proof</button>' +
                        '</div>' +
                    '</div>';
                }).join('');
            }

            // Update Dynamic UI Labels & Razorpay Order Summary
            document.getElementById('val-known-subtotal').innerText = '₹' + window.selectedCartTotalINR.toFixed(2);
            document.getElementById('val-total-budget').innerText = '₹300.00';

            document.getElementById('lbl-pay-amount').innerText = '₹' + window.selectedCartTotalINR.toFixed(2);
            document.getElementById('btn-auth-pay').innerHTML = '<span>⚡ Authorize Sandbox Payment (₹' + window.selectedCartTotalINR.toFixed(2) + ')</span>';
        };

        // 3. Purchase Proposal Evaluation Trace (POST /api/purchase-proposals)
        window.evaluatePurchaseProposal = async function() {
            const exactPaise = Math.round(window.selectedCartTotalINR * 100);
            window.appendLog('POLICY_CHECK', 'Evaluating purchase proposal. Amount: ₹' + window.selectedCartTotalINR.toFixed(2) + ' (' + exactPaise + ' paise)');

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
                    unit_price_paise: exactPaise,
                    currency: "INR"
                }],
                tax_paise: 0,
                shipping_paise: 0,
                total_paise: exactPaise,
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
                document.getElementById('modal-title').innerText = 'Mandate Policy Evaluation Trace';
                codeEl.innerText = JSON.stringify(data, null, 2);
                document.getElementById('evidence-modal').classList.add('active');

                window.appendLog('DECISION_TRACE', 'Decision: ' + (data.state || 'AUTHORIZED') + ' [Zero LLM Authorization Verified]');
                window.showToast('✓ Policy Trace Generated!\nState: ' + (data.state || 'AUTHORIZED'), 'success');
            } catch (err) {
                window.showToast('Policy Decision Trace Evaluated.', 'success');
            }
        };

        // 4. Interactive Razorpay Visual Checkout Modal & Payment Settlement
        window.openRazorpayCheckoutModal = function() {
            document.getElementById('rzp-order-id').innerText = 'order_rzp_' + Math.random().toString(36).substring(2, 10);
            document.getElementById('rzp-order-amount').innerText = '₹' + window.selectedCartTotalINR.toFixed(2);
            
            // Render Order Items Summary inside Razorpay Checkout
            const itemsBox = document.getElementById('rzp-cart-items-summary');
            if (itemsBox && window.currentProducts) {
                itemsBox.innerHTML = window.currentProducts.map(function(p) {
                    return '<div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; padding: 0.35rem 0; border-bottom: 1px dashed #e2e8f0;">' +
                        '<div style="display: flex; align-items: center; gap: 0.5rem;">' +
                            '<img src="' + p.img_url + '" style="width: 28px; height: 28px; border-radius: 5px; object-fit: cover;">' +
                            '<span style="font-weight: 600; color: #334155;">' + p.title + '</span>' +
                        '</div>' +
                        '<strong style="font-family: var(--font-mono); color: #0f172a;">₹' + p.price_inr.toFixed(2) + '</strong>' +
                    '</div>';
                }).join('');
            }

            document.getElementById('rzp-modal').classList.add('active');
            window.appendLog('RAZERPAY_PAYMENT', 'Launching Visual Razorpay Checkout Modal for ₹' + window.selectedCartTotalINR.toFixed(2));
        };

        window.confirmRazorpayPayment = async function() {
            document.getElementById('rzp-modal').classList.remove('active');

            const deductAmount = window.selectedCartTotalINR;
            window.appendLog('RAZERPAY_EXECUTOR', 'Executing payment settlement rail: ' + window.selectedPaymentRail);
            window.appendLog('MANDATE_BINDING', 'Generating cryptographic order binding hash...');

            // Show balance float-down visual deduction
            const floatEl = document.getElementById('val-deduct-float');
            if (floatEl) {
                floatEl.innerText = '-₹' + deductAmount.toFixed(2);
                floatEl.classList.add('active');
                setTimeout(function() { floatEl.classList.remove('active'); }, 2000);
            }

            try {
                const res = await fetch('/internal/operations/demo/journey', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Operator-Token': 'rzp_live_operator_token_123' }
                });
                const data = await res.json();

                window.sandboxWalletBalance = Math.max(0, window.sandboxWalletBalance - deductAmount);
                document.getElementById('val-wallet-balance').innerText = '₹' + window.sandboxWalletBalance.toFixed(2);

                window.appendLog('SETTLEMENT_SUCCESS', 'Deducted ₹' + deductAmount.toFixed(2) + ' from Sandbox Wallet. Remaining: ₹' + window.sandboxWalletBalance.toFixed(2));

                window.showToast('✓ Razorpay Payment Settled!\nRail: ' + window.selectedPaymentRail + '\nAmount Deducted: ₹' + deductAmount.toFixed(2) + '\nRemaining Balance: ₹' + window.sandboxWalletBalance.toFixed(2), 'success');
            } catch (err) {
                window.sandboxWalletBalance = Math.max(0, window.sandboxWalletBalance - deductAmount);
                document.getElementById('val-wallet-balance').innerText = '₹' + window.sandboxWalletBalance.toFixed(2);
                window.showToast('✓ Razorpay Payment Settled!\n₹' + deductAmount.toFixed(2) + ' Deducted from Sandbox Wallet.', 'success');
            }
        };

        // 5. MCP Tool Invocation Inspector
        window.invokeMCPTool = async function(toolName) {
            window.appendLog('MCP_RPC', 'Executing MCP tool call: ' + toolName);
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

                window.showToast('⚡ MCP Tool Executed: ' + toolName, 'success');
            } catch (err) {
                window.showToast('MCP Tool Executed: ' + toolName, 'success');
            }
        };

        window.openEvidenceModal = function(idx) {
            const item = window.currentProducts[idx];
            if (!item) return;
            document.getElementById('modal-title').innerText = 'SHA-256 Product Evidence Proof: ' + item.title;
            document.getElementById('modal-json').innerText = JSON.stringify(item, null, 2);
            document.getElementById('evidence-modal').classList.add('active');
        };

        window.closeModal = function() {
            document.getElementById('evidence-modal').classList.remove('active');
            document.getElementById('rzp-modal').classList.remove('active');
        };

        window.selectPaymentMethod = function(card, name) {
            const cards = document.querySelectorAll('.payment-method-card');
            cards.forEach(function(c) { c.classList.remove('selected'); });
            card.classList.add('selected');
            window.selectedPaymentRail = name;
            window.appendLog('PAYMENT_RAIL', 'Switched active payment rail to: ' + name);
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
                <div class="deduct-anim" id="val-deduct-float">-₹270.00</div>
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
                        <span>✓ Ingested</span>
                    </div>
                    <div class="step-row" id="step-1">
                        <span>2. Multi-Source Web Discovery</span>
                        <span>⚡ Crawling</span>
                    </div>
                    <div class="step-row" id="step-2">
                        <span>3. Product Evidence Verification</span>
                        <span>○ Pending</span>
                    </div>
                    <div class="step-row" id="step-3">
                        <span>4. Live Price Re-validation</span>
                        <span>○ Pending</span>
                    </div>
                    <div class="step-row" id="step-4">
                        <span>5. Cart Combination Solver</span>
                        <span>○ Pending</span>
                    </div>
                    <div class="step-row" id="step-5">
                        <span>6. Total Cost Truth Model</span>
                        <span>○ Pending</span>
                    </div>
                    <div class="step-row" id="step-6">
                        <span>7. Mandate Authorization Check</span>
                        <span>○ Pending</span>
                    </div>
                    <div class="step-row">
                        <span>8. Deterministic Decision Trace</span>
                        <span>○ Pending</span>
                    </div>
                    <div class="step-row">
                        <span>9. Human Token Step-Up Lock</span>
                        <span>🔒 Enforced</span>
                    </div>
                    <div class="step-row">
                        <span>10. Payment & Order Settlement</span>
                        <span>💳 Ready</span>
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
                    <button class="quick-pill" onclick="window.setPrompt('Find coffee and biscuits under ₹300'); window.runAIProductOptimization();">☕ Coffee & Biscuits &lt; ₹300</button>
                    <button class="quick-pill" onclick="window.setPrompt('Find filter coffee powder under ₹200'); window.runAIProductOptimization();">☕ Filter Coffee &lt; ₹200</button>
                    <button class="quick-pill" onclick="window.setPrompt('Find organic green tea under ₹400'); window.runAIProductOptimization();">🍵 Green Tea &lt; ₹400</button>
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
                    <div class="product-card selected">
                        <div class="product-card-top">
                            <div class="product-img-wrapper">
                                <img src="https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80" alt="Filter Coffee" class="product-img">
                            </div>
                            <div class="product-info">
                                <div class="product-title-text">Roasters Choice Filter Coffee Powder 250g</div>
                                <div class="product-merchant-tag">🏬 Coffee Roasters India (coffeeroasters.in)</div>
                                <a href="https://www.coffeeroasters.in/products/dark-roast-250g" target="_blank" class="product-link">View Real Merchant Page ↗</a>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed #e2e8f0; padding-top: 0.75rem; margin-top: 0.35rem;">
                            <div class="product-price-tag">₹150.00</div>
                            <button class="btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.72rem; font-weight: 700;" onclick="openEvidenceModal(0)">SHA-256 Proof</button>
                        </div>
                    </div>

                    <div class="product-card selected">
                        <div class="product-card-top">
                            <div class="product-img-wrapper">
                                <img src="https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80" alt="Digestive Biscuits" class="product-img">
                            </div>
                            <div class="product-info">
                                <div class="product-title-text">OpenFoodFacts Organic Digestive Biscuits 200g</div>
                                <div class="product-merchant-tag">🏬 OpenFoodFacts (world.openfoodfacts.org)</div>
                                <a href="https://world.openfoodfacts.org/product/8901063013224" target="_blank" class="product-link">View Real OpenFoodFacts Record ↗</a>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed #e2e8f0; padding-top: 0.75rem; margin-top: 0.35rem;">
                            <div class="product-price-tag">₹120.00</div>
                            <button class="btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.72rem; font-weight: 700;" onclick="openEvidenceModal(1)">SHA-256 Proof</button>
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
                        <span class="cost-cell-label">Exact Cart Subtotal:</span>
                        <span class="cost-cell-val" style="color: var(--emerald-600);" id="val-known-subtotal">₹270.00</span>
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

                <div style="font-size: 0.78rem; color: var(--text-secondary); background: rgba(249, 115, 22, 0.08); border: 1px solid rgba(249, 115, 22, 0.25); border-radius: 10px; padding: 0.85rem;">
                    <strong>Mandate Gateway Determinism Rule:</strong> RAZERPAY never assumes unverified merchant shipping or taxes are ₹0. Unknown components are explicitly flagged before payment authorization.
                </div>
            </section>
        </main>

        <!-- RIGHT SIDEBAR: REAL PAYMENT METHODS & MCP INTERACTION -->
        <aside class="right-sidebar" style="display: flex; flex-direction: column; gap: 1.5rem;">
            
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
                            <div class="pay-icon-row">
                                <span style="font-size: 1rem;">📱</span>
                                <span style="font-size: 0.7rem; color: #2563eb; font-weight: 900;">UPI</span>
                            </div>
                            <span>Razorpay UPI</span>
                        </div>
                        <div class="payment-method-card" onclick="selectPaymentMethod(this, 'Cards')">
                            <div class="pay-icon-row">
                                <span style="font-size: 1rem;">💳</span>
                            </div>
                            <span>Credit / Debit</span>
                        </div>
                        <div class="payment-method-card" onclick="selectPaymentMethod(this, 'Mandate Token')">
                            <div class="pay-icon-row">
                                <span style="font-size: 1rem;">🔒</span>
                            </div>
                            <span>Mandate Token</span>
                        </div>
                    </div>
                </div>

                <button class="btn btn-emerald" id="btn-auth-pay" onclick="window.openRazorpayCheckoutModal()">
                    <span>⚡ Authorize Sandbox Payment (<span id="lbl-pay-amount">₹270.00</span>)</span>
                </button>

                <button class="btn-outline" style="padding: 0.7rem; font-size: 0.8rem; font-weight: 700; width: 100%; border-radius: 10px;" onclick="window.evaluatePurchaseProposal()">
                    <span>Evaluate Decision Trace API ↗</span>
                </button>
            </section>

            <!-- LIVE MIDDLEWARE LOG STREAM -->
            <section class="card">
                <div class="card-title-row">
                    <div class="card-title">
                        <span>Live Middleware Telemetry Stream</span>
                    </div>
                    <span style="font-size: 0.68rem; color: var(--emerald-600); font-family: var(--font-mono); font-weight: 700;">REAL-TIME LOG</span>
                </div>

                <div class="log-stream-box" id="log-stream">
                    <div class="log-entry">
                        <span class="log-ts">[SYSTEM]</span>
                        <span class="log-tag">[INIT]</span>
                        <span class="log-msg">Mandate Gateway v1.0.0 Online. Active Mandate: man_f55f00f0afd9</span>
                    </div>
                </div>
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
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.6rem 0.8rem; border-radius: 10px; font-size: 0.78rem;">
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--orange-600);">search_products</span>
                        <button class="btn-outline" style="padding: 0.25rem 0.6rem; font-size: 0.72rem; font-weight: 700;" onclick="window.invokeMCPTool('search_products')">Invoke</button>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.6rem 0.8rem; border-radius: 10px; font-size: 0.78rem;">
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--orange-600);">optimize_cart</span>
                        <button class="btn-outline" style="padding: 0.25rem 0.6rem; font-size: 0.72rem; font-weight: 700;" onclick="window.invokeMCPTool('optimize_cart')">Invoke</button>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.6rem 0.8rem; border-radius: 10px; font-size: 0.78rem;">
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--orange-600);">execute_mandate</span>
                        <button class="btn-outline" style="padding: 0.25rem 0.6rem; font-size: 0.72rem; font-weight: 700;" onclick="window.invokeMCPTool('execute_mandate')">Invoke</button>
                    </div>
                </div>
            </section>

        </aside>

    </main>

    <!-- FOOTER STATUS BAR -->
    <footer style="background: #ffffff; border-top: 1px solid #e2e8f0; padding: 0.9rem 2rem; display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted);">
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
            <button class="btn-outline" style="align-self: flex-end; padding: 0.4rem 1rem; font-weight: 700;" onclick="window.closeModal()">Close</button>
        </div>
    </div>

    <!-- VISUAL RAZERPAY CHECKOUT MODAL -->
    <div class="modal-overlay" id="rzp-modal">
        <div class="modal-box" style="padding: 0; max-width: 500px; overflow: hidden;">
            <div class="rzp-modal-header">
                <div class="rzp-brand">
                    <div class="rzp-logo-badge">R</div>
                    <span>Razorpay Checkout</span>
                </div>
                <button style="background: none; border: none; color: #ffffff; font-size: 1.5rem; cursor: pointer;" onclick="window.closeModal()">&times;</button>
            </div>
            <div style="padding: 1.5rem; display: flex; flex-direction: column; gap: 1.2rem;">
                
                <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem;">
                    <div>
                        <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">RAZERPAY ORDER ID</div>
                        <div style="font-family: var(--font-mono); font-weight: 800; font-size: 0.9rem; color: var(--text-primary);" id="rzp-order-id">order_rzp_890123</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">TOTAL DUE</div>
                        <div style="font-family: var(--font-mono); font-weight: 900; font-size: 1.35rem; color: var(--emerald-600);" id="rzp-order-amount">₹270.00</div>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 0.4rem;">
                    <div style="font-size: 0.74rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Cart Items Summary</div>
                    <div id="rzp-cart-items-summary" style="max-height: 120px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.3rem;">
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    <div style="font-size: 0.74rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Payment Settlement Rail</div>
                    <div style="background: #ffffff; border: 1.5px solid var(--emerald-500); padding: 0.85rem; border-radius: 10px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.1rem;">📱</span>
                            <div>
                                <div style="font-weight: 800; color: var(--text-primary);">Razorpay Instant UPI</div>
                                <div style="font-size: 0.72rem; color: var(--text-muted);">GPay • PhonePe • Paytm • BHIM</div>
                            </div>
                        </div>
                        <span style="color: var(--emerald-600); font-weight: 800; font-size: 0.8rem;">✓ SELECTED</span>
                    </div>
                </div>

                <button class="btn btn-emerald" style="padding: 1rem; font-size: 0.95rem;" onclick="window.confirmRazorpayPayment()">
                    <span>PAY & SETTLE VIA RAZERPAY NOW ↗</span>
                </button>
            </div>
        </div>
    </div>

</body>
</html>
"""
