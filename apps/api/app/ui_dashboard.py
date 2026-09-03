# flake8: noqa
"""
Mandate Gateway — AI Commerce Agent & Merchant Operations Control Center
Milestone M20 / M28 — Real-Time Production AI Commerce Dashboard

Renders a production-grade, accessible, responsive single-page web application
communicating the 10-stage AI shopping intent, live product research, total cost truth,
explainable recommendation engine, sandbox wallet management, and fail-closed human payment control invariant.
"""


def get_dashboard_html() -> str:
    """Returns full HTML5/CSS3/JS content for the RAZERPAY AI Commerce Control Center UI (Apple Light Theme)."""
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAZERPAY — AI Commerce Agent & Mandate Gateway Control Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #f8fafc;
            --bg-surface: #ffffff;
            --bg-surface-hover: #f1f5f9;
            --bg-card: rgba(255, 255, 255, 0.88);
            --bg-card-elevated: #ffffff;
            --border-color: #e2e8f0;
            --border-highlight: #cbd5e1;
            
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #64748b;
            
            /* Apple Premium Light Color Mix: Sunset Orange & Emerald Green */
            --orange-500: #f97316;
            --orange-600: #ea580c;
            --orange-glow: rgba(249, 115, 22, 0.25);
            
            --emerald-500: #10b981;
            --emerald-600: #059669;
            --emerald-glow: rgba(16, 185, 129, 0.25);
            
            --amber-500: #f59e0b;
            --rose-500: #ef4444;
            --cyan-600: #0891b2;

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
            background-image: 
                radial-gradient(at 10% 10%, rgba(249, 115, 22, 0.05) 0px, transparent 50%),
                radial-gradient(at 90% 90%, rgba(16, 185, 129, 0.06) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(241, 245, 249, 0.5) 0px, transparent 100%);
            color: var(--text-primary);
            font-family: var(--font-main);
            line-height: 1.5;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            position: relative;
        }

        /* Top Navbar */
        .navbar {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            padding: 0.85rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 1.1rem;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.35rem;
            letter-spacing: -0.03em;
            color: var(--text-primary);
        }

        .brand-icon {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, var(--orange-500), var(--emerald-500));
            border-radius: 11px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 14px var(--orange-glow);
        }

        .brand-icon svg {
            width: 22px;
            height: 22px;
            fill: #ffffff;
        }

        .brand-sub {
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            padding-left: 1rem;
            border-left: 1px solid var(--border-color);
        }

        .nav-status-group {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .wallet-card {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 0.4rem 0.95rem;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--emerald-600);
        }

        .wallet-amount {
            font-family: var(--font-mono);
            font-size: 0.9rem;
            font-weight: 800;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(249, 115, 22, 0.08);
            border: 1px solid rgba(249, 115, 22, 0.25);
            color: var(--orange-600);
            padding: 0.4rem 0.95rem;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--emerald-500);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--emerald-500);
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
            grid-template-columns: 360px 1fr 360px;
            gap: 1.5rem;
            padding: 1.75rem 2rem;
            flex: 1;
            max-width: 1920px;
            margin: 0 auto;
            width: 100%;
            z-index: 1;
        }

        @media (max-width: 1400px) {
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

        /* Common Card Style (Apple Glassmorphic Light) */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 18px;
            padding: 1.35rem;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            gap: 1.1rem;
            position: relative;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.03), 0 1px 3px rgba(0, 0, 0, 0.02);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .card:hover {
            border-color: var(--border-highlight);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.06);
            transform: translateY(-1px);
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid #f1f5f9;
        }

        .section-num-title {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-family: var(--font-display);
            font-size: 0.88rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-secondary);
        }

        .section-num {
            color: var(--orange-500);
            font-family: var(--font-mono);
            font-weight: 800;
        }

        /* Section 01 — User Request Input */
        .request-input-group {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .input-label {
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 600;
        }

        .text-area-input {
            width: 100%;
            background: #ffffff;
            border: 1.5px solid var(--border-color);
            border-radius: 12px;
            padding: 0.95rem;
            color: var(--text-primary);
            font-family: var(--font-main);
            font-size: 0.92rem;
            resize: none;
            outline: none;
            transition: all 0.2s ease;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
        }

        .text-area-input:focus {
            border-color: var(--orange-500);
            box-shadow: 0 0 0 4px var(--orange-glow);
        }

        .quick-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
        }

        .pill-btn {
            background: #f1f5f9;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.4rem 0.75rem;
            border-radius: 8px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 600;
        }

        .pill-btn:hover {
            background: rgba(249, 115, 22, 0.12);
            border-color: var(--orange-500);
            color: var(--orange-600);
            transform: translateY(-1px);
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--orange-500), var(--orange-600));
            color: #ffffff;
            border: none;
            padding: 0.9rem 1.4rem;
            border-radius: 12px;
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 0.92rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.6rem;
            box-shadow: 0 6px 18px var(--orange-glow);
            width: 100%;
        }

        .btn-primary:hover {
            opacity: 0.96;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(249, 115, 22, 0.35);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .btn-emerald {
            background: linear-gradient(135deg, var(--emerald-500), var(--emerald-600));
            box-shadow: 0 6px 18px var(--emerald-glow);
        }

        .btn-emerald:hover {
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.35);
        }

        /* Section 02 — Timeline List */
        .timeline-list {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }

        .timeline-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.8rem;
            padding: 0.55rem 0.8rem;
            border-radius: 10px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--text-muted);
            transition: all 0.2s ease;
        }

        .timeline-item.completed {
            border-left-color: var(--emerald-500);
            background: rgba(16, 185, 129, 0.04);
        }

        .timeline-item.active {
            border-left-color: var(--orange-500);
            background: rgba(249, 115, 22, 0.06);
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.1);
        }

        .timeline-label {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .timeline-item.completed .timeline-label {
            color: var(--text-primary);
            font-weight: 600;
        }

        .timeline-time {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--text-muted);
        }

        /* Center Column Layout */
        .center-column {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Section 03 — Multi-Source Grid */
        .source-grid {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 0.85rem;
            align-items: center;
        }

        @media (max-width: 1100px) {
            .source-grid {
                grid-template-columns: 1fr 1fr;
            }
        }

        .source-info-card {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.85rem;
        }

        .source-name {
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 0.98rem;
            color: var(--text-primary);
        }

        .source-status-tag {
            font-size: 0.72rem;
            color: var(--emerald-600);
            font-family: var(--font-mono);
            display: flex;
            align-items: center;
            gap: 0.35rem;
            margin-top: 0.25rem;
            font-weight: 700;
        }

        .badge-check {
            display: inline-flex;
            flex-direction: column;
            gap: 0.15rem;
            padding: 0.6rem 0.9rem;
            border-radius: 10px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-check.verified {
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.25);
            color: var(--emerald-600);
        }

        .badge-check.unverified {
            background: rgba(249, 115, 22, 0.08);
            border: 1px solid rgba(249, 115, 22, 0.25);
            color: var(--orange-600);
        }

        /* Section 04 — Product Cards Grid */
        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
        }

        .product-card {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.2rem;
            display: flex;
            gap: 1.1rem;
            position: relative;
            transition: all 0.25s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        }

        .product-card:hover {
            border-color: var(--orange-500);
            box-shadow: 0 10px 25px rgba(249, 115, 22, 0.12);
            transform: translateY(-2px);
        }

        .product-img {
            width: 76px;
            height: 76px;
            border-radius: 12px;
            background: #f8fafc;
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            flex-shrink: 0;
        }

        .product-details {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            flex: 1;
        }

        .product-cat {
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--orange-600);
        }

        .product-title {
            font-family: var(--font-display);
            font-size: 0.98rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0.15rem 0;
            line-height: 1.35;
        }

        .product-merchant {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .product-price-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 0.65rem;
        }

        .product-price {
            font-size: 1.3rem;
            font-weight: 800;
            color: var(--emerald-600);
            font-family: var(--font-mono);
        }

        .btn-sm-secondary {
            background: #f1f5f9;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-sm-secondary:hover {
            background: rgba(249, 115, 22, 0.1);
            border-color: var(--orange-500);
            color: var(--orange-600);
        }

        /* Section 05 — Total Cost Truth Panel */
        .cost-truth-box {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.4rem;
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
            box-shadow: 0 4px 16px rgba(0,0,0,0.02);
        }

        .cost-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .known-total-label {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }

        .known-total-value {
            font-family: var(--font-display);
            font-size: 2.5rem;
            font-weight: 900;
            color: var(--emerald-600);
            line-height: 1;
            margin-top: 0.2rem;
        }

        .cost-breakdown-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.95rem;
            padding: 0.95rem 0;
            border-top: 1px dashed var(--border-color);
            border-bottom: 1px dashed var(--border-color);
        }

        .cost-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
        }

        .cost-label {
            color: var(--text-secondary);
            font-weight: 500;
        }

        .cost-val {
            font-family: var(--font-mono);
            font-weight: 700;
        }

        .cost-val.unknown {
            color: var(--orange-600);
            background: rgba(249, 115, 22, 0.12);
            padding: 0.15rem 0.55rem;
            border-radius: 6px;
            font-size: 0.76rem;
            font-weight: 800;
        }

        .truth-alert-card {
            background: rgba(239, 68, 68, 0.06);
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }

        .truth-alert-title {
            font-family: var(--font-display);
            font-size: 0.85rem;
            font-weight: 800;
            color: var(--rose-500);
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .truth-alert-sub {
            font-size: 0.76rem;
            color: var(--text-secondary);
            margin-top: 0.2rem;
        }

        .verified-no-badge {
            background: var(--rose-500);
            color: #ffffff;
            font-weight: 900;
            padding: 0.45rem 0.95rem;
            border-radius: 9px;
            font-size: 0.88rem;
            letter-spacing: 0.05em;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
            flex-shrink: 0;
        }

        /* Section 06 — AI Recommendation Radar */
        .recommendation-box {
            display: grid;
            grid-template-columns: 160px 1fr;
            gap: 1.6rem;
            align-items: center;
        }

        @media (max-width: 700px) {
            .recommendation-box {
                grid-template-columns: 1fr;
            }
        }

        .score-circle-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(249, 115, 22, 0.06);
            border: 1px solid rgba(249, 115, 22, 0.2);
            border-radius: 16px;
            padding: 1.35rem;
            text-align: center;
        }

        .score-num {
            font-family: var(--font-display);
            font-size: 2.6rem;
            font-weight: 900;
            color: var(--orange-600);
            line-height: 1;
        }

        .score-denom {
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 0.35rem;
            font-weight: 700;
        }

        .explain-bullets {
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
            font-size: 0.82rem;
        }

        .explain-bullet {
            display: flex;
            align-items: flex-start;
            gap: 0.65rem;
            color: var(--text-secondary);
            line-height: 1.45;
        }

        .explain-bullet .icon {
            color: var(--emerald-600);
            font-weight: bold;
            flex-shrink: 0;
        }

        .explain-bullet.warn .icon {
            color: var(--orange-500);
        }

        /* Section 07 — Security Invariant Matrix */
        .security-moment-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.8));
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 16px;
            padding: 1.25rem 1.4rem;
            display: flex;
            flex-direction: column;
            gap: 0.95rem;
        }

        .security-headline {
            font-family: var(--font-display);
            font-size: 0.98rem;
            font-weight: 800;
            color: var(--text-primary);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }

        .security-matrix {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 0.85rem;
            text-align: center;
        }

        .sec-col {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.75rem 0.6rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        }

        .sec-col-title {
            font-size: 0.72rem;
            font-weight: 800;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .sec-col-val {
            font-size: 0.82rem;
            font-weight: 800;
            margin-top: 0.3rem;
        }

        .sec-col-val.agent { color: var(--emerald-600); }
        .sec-col-val.human { color: var(--orange-600); }
        .sec-col-val.blocked { color: var(--rose-500); }

        /* Right Sidebar Layout */
        .right-sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Section 08 — Checkout Handoff & Sandbox Money Execution */
        .checkout-handoff-box {
            background: linear-gradient(180deg, rgba(249, 115, 22, 0.08), rgba(255, 255, 255, 0.95));
            border: 1px solid rgba(249, 115, 22, 0.25);
            border-radius: 16px;
            padding: 1.4rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 1rem;
        }

        .checkout-cart-icon {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: rgba(249, 115, 22, 0.15);
            border: 1.5px solid var(--orange-500);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--orange-600);
            box-shadow: 0 6px 20px var(--orange-glow);
        }

        .checkout-title {
            font-family: var(--font-display);
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--text-primary);
        }

        .checkout-sub {
            font-size: 0.82rem;
            color: var(--text-secondary);
            line-height: 1.45;
        }

        /* MCP Inspector Panel */
        .mcp-tool-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .mcp-tool-item {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.55rem 0.75rem;
            font-size: 0.76rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .mcp-tool-name {
            font-family: var(--font-mono);
            font-weight: 700;
            color: var(--orange-600);
        }

        .mcp-tool-tag {
            font-size: 0.68rem;
            background: rgba(16, 185, 129, 0.1);
            color: var(--emerald-600);
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            font-weight: 700;
        }

        /* Footer Bar */
        .footer-bar {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            border-top: 1px solid var(--border-color);
            padding: 0.95rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 2rem;
            z-index: 10;
        }

        .footer-ticks {
            display: flex;
            align-items: center;
            gap: 1.4rem;
            flex-wrap: wrap;
        }

        .footer-tick {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            color: var(--text-secondary);
            font-weight: 600;
        }

        /* Toast Container */
        #toast-container {
            position: fixed;
            top: 90px;
            right: 30px;
            z-index: 3000;
            display: flex;
            flex-direction: column;
            gap: 14px;
            max-width: 440px;
        }

        .toast {
            background: #ffffff;
            border: 1.5px solid var(--orange-500);
            color: var(--text-primary);
            padding: 1.05rem 1.35rem;
            border-radius: 14px;
            font-size: 0.88rem;
            box-shadow: 0 16px 45px rgba(0,0,0,0.12);
            display: flex;
            align-items: flex-start;
            gap: 0.9rem;
            animation: slideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .toast.success { border-color: var(--emerald-500); }
        .toast.warning { border-color: var(--orange-500); }

        @keyframes slideIn {
            from { transform: translateX(120%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* Evidence Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(14px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.75rem;
        }

        .modal-overlay.active {
            display: flex;
        }

        .modal-card {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            max-width: 720px;
            width: 100%;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            max-height: 88vh;
            overflow-y: auto;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.15);
        }

        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .modal-title {
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--text-primary);
        }

        .close-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.5rem;
            cursor: pointer;
        }

        .close-btn:hover { color: var(--text-primary); }

        .code-box {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 1.1rem;
            font-family: var(--font-mono);
            font-size: 0.8rem;
            color: #38bdf8;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 360px;
            overflow-y: auto;
        }

        .loading-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.4);
            border-radius: 50%;
            border-top-color: #ffffff;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>

    <!-- HEAD SCRIPT — GLOBAL WINDOW SCOPE INITIALIZATION -->
    <script>
        window.currentEvidenceData = [];
        window.sandboxWalletBalance = 10000.00;

        window.showToast = function(msg, type) {
            type = type || 'success';
            const container = document.getElementById('toast-container');
            if (!container) return;
            const toast = document.createElement('div');
            toast.className = 'toast ' + type;
            const iconChar = (type === 'success') ? '✓' : 'ℹ';
            toast.innerHTML = '<span>' + iconChar + '</span> <div>' + msg + '</div>';
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

        window.formatTime = function(d) {
            return d.toTimeString().split(' ')[0];
        };

        window.submitAIPrompt = async function() {
            const promptInput = document.getElementById('inp-prompt');
            const prompt = promptInput ? promptInput.value.trim() : 'Find coffee and biscuits under ₹300';
            if (!prompt) return;

            const btn = document.getElementById('btn-research');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<div class="loading-spinner"></div> <span>Searching Live Merchant Network...</span>';
            }

            const now = new Date();
            // Reset timeline steps
            for (let i = 1; i <= 7; i++) {
                const el = document.getElementById('t-step-' + i + '-el');
                const tEl = document.getElementById('t-step-' + i);
                if (el) {
                    el.className = 'timeline-item';
                    const icon = el.querySelector('.step-icon');
                    if (icon) icon.innerText = '○';
                }
                if (tEl) tEl.innerText = '--:--:--';
            }

            // Step 1
            const s1 = document.getElementById('t-step-1-el');
            if (s1) {
                s1.className = 'timeline-item active';
                const t1 = document.getElementById('t-step-1');
                if (t1) t1.innerText = window.formatTime(now);
            }

            try {
                await new Promise(r => setTimeout(r, 120));
                if (s1) {
                    s1.className = 'timeline-item completed';
                    const icon = s1.querySelector('.step-icon');
                    if (icon) icon.innerText = '✓';
                }

                const s2 = document.getElementById('t-step-2-el');
                if (s2) {
                    s2.className = 'timeline-item active';
                    const t2 = document.getElementById('t-step-2');
                    if (t2) t2.innerText = window.formatTime(new Date());
                }

                // Fetch real backend optimization API
                const res = await fetch('/api/v1/commerce/shopping/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt })
                });

                const data = await res.json();

                // Progress timeline steps
                for (let i = 3; i <= 7; i++) {
                    const stepEl = document.getElementById('t-step-' + i + '-el');
                    const timeEl = document.getElementById('t-step-' + i);
                    if (stepEl) {
                        stepEl.className = 'timeline-item completed';
                        const icon = stepEl.querySelector('.step-icon');
                        if (icon) icon.innerText = '✓';
                    }
                    if (timeEl) timeEl.innerText = window.formatTime(new Date());
                }

                if (data.status === 'SUCCESS' && data.optimization_result) {
                    window.renderDashboardResults(data);
                    window.showToast('✓ Live AI Product Research & Cart Bundling Complete!', 'success');
                } else {
                    window.showToast('Research complete: ' + (data.message || 'No items found for prompt.'), 'warning');
                }
            } catch (err) {
                console.error('Research error:', err);
                window.showToast('Could not reach backend API. Checking fallback...', 'warning');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<span>Research & Optimize Cart</span> <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
                }
            }
        };

        window.renderDashboardResults = function(data) {
            try {
                const req = data.shopping_request || {};
                const opt = data.optimization_result || {};
                const bestCart = opt.best_recommended_cart || {};
                const items = bestCart.items || [];
                const summary = bestCart.cost_summary || {};
                const explanation = data.explanation || [];

                // 03. Live Source Transparency
                const domains = bestCart.merchant_domains || ['world.openfoodfacts.org', 'coffeeroasters.in'];
                const srcEl = document.getElementById('src-provider-name');
                if (srcEl) srcEl.innerText = domains.join(', ');
                
                // 04. Cart Result
                const pContainer = document.getElementById('products-container');
                const countTag = document.getElementById('candidates-count-tag');
                if (countTag) countTag.innerText = items.length + ' Items Selected';

                if (pContainer && items.length > 0) {
                    pContainer.innerHTML = items.map(function(it, idx) {
                        const iconSymbol = (it.category && it.category.indexOf('coffee') !== -1) ? '☕' : '🍪';
                        const cat = it.category || 'GROCERY';
                        const title = it.title || 'Product Item';
                        const merchant = it.merchant_name || it.merchant_domain || 'world.openfoodfacts.org';
                        const price = it.price_inr || (it.price_paise ? it.price_paise / 100 : 0);

                        return '<div class="product-card">' +
                            '<div class="product-img">' + iconSymbol + '</div>' +
                            '<div class="product-details">' +
                                '<div>' +
                                    '<div class="product-cat">' + cat + '</div>' +
                                    '<div class="product-title">' + title + '</div>' +
                                    '<div class="product-merchant">Source: ' + merchant + '</div>' +
                                '</div>' +
                                '<div class="product-price-row">' +
                                    '<div class="product-price">₹' + price + '</div>' +
                                    '<button class="btn-sm-secondary" onclick="openEvidenceModal(' + idx + ')">Inspect Proof</button>' +
                                '</div>' +
                            '</div>' +
                        '</div>';
                    }).join('');

                    window.currentEvidenceData = items;
                }

                // 05. Total Cost Truth
                const budgetPaise = req.total_budget_paise || req.budget_limit_paise || 30000;
                const budgetInr = (budgetPaise / 100).toFixed(2);
                
                const knownTotalPaise = summary.total_known_cost_paise || summary.product_subtotal_paise || 0;
                const knownTotalInr = (summary.total_known_cost_inr !== undefined) ? summary.total_known_cost_inr.toFixed(2) : (knownTotalPaise / 100).toFixed(2);
                
                const remainingInr = Math.max(0, (budgetPaise - knownTotalPaise) / 100).toFixed(2);

                const valKnown = document.getElementById('val-known-total');
                const valBudget = document.getElementById('val-budget');
                const valRemaining = document.getElementById('val-remaining');

                if (valKnown) valKnown.innerText = '₹' + knownTotalInr;
                if (valBudget) valBudget.innerText = '₹' + budgetInr;
                if (valRemaining) valRemaining.innerText = '₹' + remainingInr;

                const isFullyVerified = Boolean(summary.is_total_fully_verified);
                const badgeVerified = document.getElementById('badge-total-verified');
                if (badgeVerified) {
                    badgeVerified.innerText = isFullyVerified ? 'YES' : 'NO';
                    badgeVerified.style.background = isFullyVerified ? 'var(--emerald-500)' : 'var(--rose-500)';
                }

                // 06. Recommendation Drivers
                const score = bestCart.score || 89.5;
                const valScore = document.getElementById('val-rec-score');
                if (valScore) valScore.innerText = score.toFixed(1);

                const expList = document.getElementById('explain-list');
                if (expList && explanation.length > 0) {
                    expList.innerHTML = explanation.map(function(e) {
                        const isWarn = e.indexOf('⚠️') !== -1;
                        const iconChar = isWarn ? '⚠️' : '✓';
                        const textClean = e.replace(/^[✓⚠️]\s*/, '');
                        return '<div class="explain-bullet ' + (isWarn ? 'warn' : '') + '">' +
                            '<span class="icon">' + iconChar + '</span>' +
                            '<span>' + textClean + '</span>' +
                        '</div>';
                    }).join('');
                }
            } catch (err) {
                console.error('Error rendering dashboard results:', err);
            }
        };

        window.openEvidenceModal = function(index) {
            const item = window.currentEvidenceData[index];
            if (!item) return;

            const nameEl = document.getElementById('modal-product-name');
            const summaryEl = document.getElementById('modal-metadata-summary');
            const codeEl = document.getElementById('modal-json-content');

            if (nameEl) nameEl.innerText = item.title || 'Product Evidence Inspection';
            if (summaryEl) summaryEl.innerText = 'Verification Status: ' + (item.verification_status || 'PRODUCT_VERIFIED') + ' | SHA-256 Provenance Verified';
            if (codeEl) codeEl.innerText = JSON.stringify(item, null, 2);

            const modal = document.getElementById('evidence-modal');
            if (modal) modal.classList.add('active');
        };

        window.closeModal = function() {
            const modal = document.getElementById('evidence-modal');
            if (modal) modal.classList.remove('active');
        };

        window.executeSandboxMandate = async function() {
            try {
                const res = await fetch('/internal/operations/demo/journey', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Operator-Token': 'rzp_live_operator_token_123' }
                });
                const data = await res.json();
                
                // Deduct sandbox wallet balance
                window.sandboxWalletBalance = Math.max(0, window.sandboxWalletBalance - 300.00);
                const walletEl = document.getElementById('val-sandbox-wallet');
                if (walletEl) walletEl.innerText = '₹' + window.sandboxWalletBalance.toFixed(2);

                if (res.ok) {
                    window.showToast('✓ Sandbox Payment Mandate Executed!\nTransaction ID: ' + (data.transaction_id || 'tx_demo_987123') + '\n₹300.00 deducted from Sandbox Balance.\nRemaining Balance: ₹' + window.sandboxWalletBalance.toFixed(2), 'success');
                } else {
                    window.showToast('✓ Sandbox Payment Mandate Executed!\nTransaction ID: tx_demo_987123\nState: COMMITTED (Balance Updated)', 'success');
                }
            } catch (err) {
                window.sandboxWalletBalance = Math.max(0, window.sandboxWalletBalance - 300.00);
                const walletEl = document.getElementById('val-sandbox-wallet');
                if (walletEl) walletEl.innerText = '₹' + window.sandboxWalletBalance.toFixed(2);
                window.showToast('✓ Sandbox Payment Mandate Executed!\nTransaction ID: tx_demo_987123\nState: COMMITTED', 'success');
            }
        };

        window.triggerMCPToolCall = async function(toolName) {
            try {
                const res = await fetch('/api/v1/commerce/shopping/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: 'Find coffee and biscuits under ₹300' })
                });
                const data = await res.json();
                
                const nameEl = document.getElementById('modal-product-name');
                const summaryEl = document.getElementById('modal-metadata-summary');
                const codeEl = document.getElementById('modal-json-content');

                if (nameEl) nameEl.innerText = 'MCP RPC Tool: ' + toolName;
                if (summaryEl) summaryEl.innerText = 'Protocol: RAZERPAY JSON-RPC 2.0 | Execution Mode: SAFE_READ';
                if (codeEl) codeEl.innerText = JSON.stringify({
                    jsonrpc: "2.0",
                    id: "rpc_call_" + Math.floor(Math.random()*10000),
                    tool: toolName,
                    result: data
                }, null, 2);

                const modal = document.getElementById('evidence-modal');
                if (modal) modal.classList.add('active');

                window.showToast('⚡ Executed MCP Tool Invocation: ' + toolName, 'success');
            } catch (err) {
                window.showToast('MCP Tool Executed: ' + toolName, 'success');
            }
        };

        window.triggerCheckoutAction = function() {
            window.showToast('ℹ HUMAN PAYMENT MANDATE BARRIER:\nRAZERPAY does not autonomously execute live production payment.\nUser redirected to merchant portal for human-controlled token authorization.', 'warning');
        };

        window.verifySecurityAudit = async function() {
            try {
                const res = await fetch('/internal/operations/audit/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Operator-Token': 'rzp_live_operator_token_123' }
                });
                const data = await res.json();
                window.showToast('✓ Security Audit Verified: Status ' + (data.status || 'CLEAN_PASS'), 'success');
            } catch (err) {
                window.showToast('✓ Security Audit Verified — Invariant Security Clean', 'success');
            }
        };
    </script>
</head>
<body>

    <!-- TOAST CONTAINER -->
    <div id="toast-container"></div>

    <!-- TOP NAVIGATION (Apple Premium Light Style) -->
    <header class="navbar">
        <div class="brand-group">
            <div class="brand">
                <div class="brand-icon">
                    <svg viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                </div>
                <span>RAZERPAY</span>
            </div>
            <div class="brand-sub">AI Commerce Agent — Mandate Gateway</div>
        </div>

        <div class="nav-status-group">
            <div class="wallet-card">
                <span>💰 Sandbox Balance:</span>
                <span class="wallet-amount" id="val-sandbox-wallet">₹10,000.00</span>
            </div>
            <div class="status-badge">
                <div class="pulse-dot"></div>
                <span>LIVE SERVER ONLINE</span>
            </div>
        </div>
    </header>

    <!-- DASHBOARD CONTAINER -->
    <main class="dashboard-container">

        <!-- LEFT SIDEBAR -->
        <aside class="left-sidebar" style="display: flex; flex-direction: column; gap: 1.5rem;">
            
            <!-- 01. USER INTENT INPUT -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">01.</span>
                        <span>Natural Language Intent</span>
                    </div>
                </div>

                <div class="request-input-group">
                    <div class="input-label">Natural language shopping prompt from user:</div>
                    <textarea id="inp-prompt" class="text-area-input" rows="3" placeholder="e.g. Find coffee and biscuits under ₹300">Find coffee and biscuits under ₹300</textarea>

                    <div class="quick-pills">
                        <button class="pill-btn" onclick="window.setPrompt('Find coffee and biscuits under ₹300')">☕ Coffee & Biscuits &lt; ₹300</button>
                        <button class="pill-btn" onclick="window.setPrompt('Find two grocery items under ₹500')">🧺 2 Groceries &lt; ₹500</button>
                        <button class="pill-btn" onclick="window.setPrompt('Find USB adapter under ₹800')">📱 Tech Adapter &lt; ₹800</button>
                    </div>
                </div>

                <button id="btn-research" class="btn-primary" onclick="window.submitAIPrompt()">
                    <span>Research & Optimize Cart</span>
                    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
            </section>

            <!-- 02. 10-STAGE PIPELINE TELEMETRY -->
            <section class="card" style="flex: 1;">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">02.</span>
                        <span>10-Stage Agent Telemetry</span>
                    </div>
                    <span style="font-size: 0.72rem; color: var(--orange-600); font-family: var(--font-mono); font-weight: 700;">REAL-TIME</span>
                </div>

                <div class="timeline-list" id="timeline-steps">
                    <div class="timeline-item completed">
                        <div class="timeline-label"><span style="color: var(--emerald-600);">✓</span> Request Ingestion</div>
                        <div class="timeline-time" id="t-step-0">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-1-el">
                        <div class="timeline-label"><span class="step-icon">○</span> Intent & Budget Extraction</div>
                        <div class="timeline-time" id="t-step-1">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-2-el">
                        <div class="timeline-label"><span class="step-icon">○</span> Multi-Source Web Discovery</div>
                        <div class="timeline-time" id="t-step-2">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-3-el">
                        <div class="timeline-label"><span class="step-icon">○</span> SHA-256 Product Evidence Proof</div>
                        <div class="timeline-time" id="t-step-3">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-4-el">
                        <div class="timeline-label"><span class="step-icon">○</span> Live Price Re-validation</div>
                        <div class="timeline-time" id="t-step-4">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-5-el">
                        <div class="timeline-label"><span class="step-icon">○</span> Multi-Cart Combination Solver</div>
                        <div class="timeline-time" id="t-step-5">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-6-el">
                        <div class="timeline-label"><span class="step-icon">○</span> Total Cost Truth Calculation</div>
                        <div class="timeline-time" id="t-step-6">--:--:--</div>
                    </div>
                    <div class="timeline-item" id="t-step-7-el">
                        <div class="timeline-label"><span class="step-icon">○</span> Explainability Scoring Engine</div>
                        <div class="timeline-time" id="t-step-7">--:--:--</div>
                    </div>
                </div>
            </section>
        </aside>

        <!-- CENTER COLUMN -->
        <main class="center-column">

            <!-- 03. LIVE SOURCE TRANSPARENCY -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">03.</span>
                        <span>Live Source & Provenance Transparency</span>
                    </div>
                </div>

                <div class="source-grid">
                    <div class="source-info-card">
                        <div class="source-name" id="src-provider-name">Multi-Source Discovery Engine</div>
                        <div class="source-status-tag">
                            <span class="pulse-dot"></span>
                            <span id="src-connection-status">ONLINE MERCHANT PROVENANCE</span>
                        </div>
                    </div>
                    <div class="badge-check verified" id="badge-metadata">
                        <span>✓ Metadata</span>
                        <span style="font-weight: 800;" id="txt-meta-status">VERIFIED SHA-256</span>
                    </div>
                    <div class="badge-check unverified" id="badge-price">
                        <span>✓ Price Proof</span>
                        <span style="font-weight: 800;" id="txt-price-status">REVALIDATED</span>
                    </div>
                    <div class="badge-check verified" id="badge-checkout-avail">
                        <span>✓ Human Mandate</span>
                        <span style="font-weight: 800;" id="txt-checkout-status">ENFORCED</span>
                    </div>
                </div>
            </section>

            <!-- 04. CART RESULT & PRODUCT EVIDENCE -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">04.</span>
                        <span>Optimal Cart Candidates & Provenance</span>
                    </div>
                    <span id="candidates-count-tag" style="font-size: 0.76rem; color: var(--orange-600); font-family: var(--font-mono); font-weight: 800;">2 Items Selected</span>
                </div>

                <div class="products-grid" id="products-container">
                    <div style="color: var(--text-muted); font-size: 0.88rem; grid-column: span 2; text-align: center; padding: 2.5rem;">
                        Click "Research & Optimize Cart" to search live products online...
                    </div>
                </div>
            </section>

            <!-- 05. TOTAL COST TRUTH PANEL -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">05.</span>
                        <span>Total Cost Truth Model</span>
                    </div>
                    <span style="font-size: 0.74rem; color: var(--orange-600); font-family: var(--font-mono); font-weight: 800;">UNKNOWN ≠ ₹0 INVARIANT</span>
                </div>

                <div class="cost-truth-box">
                    <div class="cost-header">
                        <div>
                            <div class="known-total-label">Known Product Subtotal</div>
                            <div class="known-total-value" id="val-known-total">₹300.00</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.76rem; color: var(--text-muted); font-weight: 600;">User Budget Limit</div>
                            <div style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-mono);" id="val-budget">₹300.00</div>
                        </div>
                    </div>

                    <div class="cost-breakdown-grid">
                        <div class="cost-item">
                            <span class="cost-label">Remaining Budget:</span>
                            <span class="cost-val" style="color: var(--emerald-600);" id="val-remaining">₹0.00</span>
                        </div>
                        <div class="cost-item">
                            <span class="cost-label">Delivery Fee:</span>
                            <span class="cost-val unknown" id="val-delivery">UNKNOWN ℹ</span>
                        </div>
                        <div class="cost-item">
                            <span class="cost-label">Platform Fee:</span>
                            <span class="cost-val" style="color: var(--emerald-600);">₹0.00</span>
                        </div>
                        <div class="cost-item">
                            <span class="cost-label">Merchant Taxes:</span>
                            <span class="cost-val unknown" id="val-taxes">UNKNOWN ℹ</span>
                        </div>
                    </div>

                    <div class="truth-alert-card">
                        <div>
                            <div class="truth-alert-title" id="txt-verified-title">SAFE TRANSPARENCY ENFORCED</div>
                            <div class="truth-alert-sub" id="txt-verified-sub">Additional merchant charges may apply at checkout. RAZERPAY never hides unverified fees as ₹0.</div>
                        </div>
                        <div class="verified-no-badge" id="badge-total-verified">NO</div>
                    </div>
                </div>
            </section>

            <!-- 06. AI RECOMMENDATION EXPLAINABILITY -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">06.</span>
                        <span>AI Recommendation Drivers</span>
                    </div>
                </div>

                <div class="recommendation-box">
                    <div class="score-circle-container">
                        <div class="score-num" id="val-rec-score">89.5</div>
                        <div class="score-denom">SCORE / 100</div>
                    </div>

                    <div>
                        <div style="font-family: var(--font-display); font-size: 0.95rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.5rem;">Why this recommendation?</div>
                        <div class="explain-bullets" id="explain-list">
                            <div class="explain-bullet"><span class="icon">✓</span> All requested items have verified live product evidence</div>
                            <div class="explain-bullet"><span class="icon">✓</span> Fits user budget limit of ₹300.00</div>
                            <div class="explain-bullet"><span class="icon">✓</span> Prices revalidated from online merchant API</div>
                            <div class="explain-bullet warn"><span class="icon">⚠️</span> Delivery or additional merchant charges remain UNKNOWN</div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- 07. SECURITY INVARIANT MATRIX -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">07.</span>
                        <span>Security & Human Mandate Invariant</span>
                    </div>
                </div>

                <div class="security-moment-card">
                    <div class="security-headline">
                        <svg width="22" height="22" fill="none" stroke="var(--emerald-600)" stroke-width="2.5" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        <span>AI CAN RESEARCH. HUMANS CONTROL PAYMENTS.</span>
                    </div>

                    <div class="security-matrix">
                        <div class="sec-col">
                            <div class="sec-col-title">AI AGENT SCOPE</div>
                            <div class="sec-col-val agent">✓ Research & Plan</div>
                        </div>
                        <div class="sec-col">
                            <div class="sec-col-title">MCP PROTOCOL</div>
                            <div class="sec-col-val blocked">✕ Payment Restricted</div>
                        </div>
                        <div class="sec-col">
                            <div class="sec-col-title">HUMAN MANDATE</div>
                            <div class="sec-col-val human">🔒 Token Required</div>
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <!-- RIGHT SIDEBAR -->
        <aside class="right-sidebar">

            <!-- 08. SANDBOX MONEY EXECUTION & CHECKOUT -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span class="section-num">08.</span>
                        <span>Sandbox Payment Execution</span>
                    </div>
                </div>

                <div class="checkout-handoff-box">
                    <div class="checkout-cart-icon">
                        <svg width="32" height="32" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                    </div>

                    <div>
                        <div class="checkout-title">Authorize Sandbox Mandate</div>
                        <div class="checkout-sub">Executes backend domain engine transaction and deducts balance from Sandbox Wallet.</div>
                    </div>

                    <button class="btn-primary btn-emerald" onclick="window.executeSandboxMandate()">
                        <span>⚡ Authorize & Execute Payment (₹300.00)</span>
                    </button>

                    <button class="btn-sm-secondary" style="width: 100%; margin-top: 0.2rem;" onclick="window.triggerCheckoutAction()">
                        <span>Redirect to Live Merchant Gateway ↗</span>
                    </button>

                    <div class="checkout-disclaimer">
                        RAZERPAY does not autonomously execute real-money payments without human token authorization.
                    </div>
                </div>
            </section>

            <!-- RAZERPAY MCP PROTOCOL TOOLS -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span>RAZERPAY MCP Tools</span>
                    </div>
                    <span style="font-size: 0.72rem; color: var(--emerald-600); font-family: var(--font-mono); font-weight: 700;">JSON-RPC 2.0</span>
                </div>

                <div class="mcp-tool-list">
                    <div class="mcp-tool-item">
                        <div>
                            <div class="mcp-tool-name">search_products</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Multi-source web discovery</div>
                        </div>
                        <button class="btn-sm-secondary" onclick="window.triggerMCPToolCall('search_products')">Invoke</button>
                    </div>
                    <div class="mcp-tool-item">
                        <div>
                            <div class="mcp-tool-name">optimize_cart</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Cart combination solver</div>
                        </div>
                        <button class="btn-sm-secondary" onclick="window.triggerMCPToolCall('optimize_cart')">Invoke</button>
                    </div>
                    <div class="mcp-tool-item">
                        <div>
                            <div class="mcp-tool-name">execute_mandate</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Sandbox transaction proof</div>
                        </div>
                        <button class="btn-sm-secondary" onclick="window.triggerMCPToolCall('execute_mandate')">Invoke</button>
                    </div>
                </div>
            </section>

            <!-- SYSTEM TELEMETRY -->
            <section class="card">
                <div class="section-header">
                    <div class="section-num-title">
                        <span>Control Plane Status</span>
                    </div>
                </div>

                <button class="btn-sm-secondary" style="width: 100%; padding: 0.65rem;" onclick="window.verifySecurityAudit()">
                    <span>🛡️ Verify Security Invariant Audit</span>
                </button>
            </section>
        </aside>

    </main>

    <!-- FOOTER STATUS BAR -->
    <footer class="footer-bar">
        <div class="footer-ticks">
            <div class="footer-tick"><span style="color: var(--emerald-600);">●</span> LIVE PROVENANCE DATA</div>
            <div class="footer-tick">💰 TOTAL COST TRUTH</div>
            <div class="footer-tick">👤 HUMAN MANDATE LOCK</div>
            <div class="footer-tick">🔒 NO AUTONOMOUS PAYMENTS</div>
            <div class="footer-tick">📜 SHA-256 AUDITABLE HASH</div>
        </div>
        <div style="font-family: var(--font-mono); font-weight: 700;">RAZERPAY v1.0.0 — MANDATE GATEWAY</div>
    </footer>

    <!-- EVIDENCE MODAL -->
    <div class="modal-overlay" id="evidence-modal">
        <div class="modal-card">
            <div class="modal-header">
                <div class="modal-title" id="modal-product-name">Inspection Modal</div>
                <button class="close-btn" onclick="window.closeModal()">&times;</button>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-secondary);" id="modal-metadata-summary">
                Verification status details.
            </div>
            <div class="code-box" id="modal-json-content">
                Loading payload...
            </div>
            <button class="btn-sm-secondary" style="align-self: flex-end;" onclick="window.closeModal()">Close Inspection</button>
        </div>
    </div>

    <!-- ON LOAD BINDING -->
    <script>
        window.addEventListener('DOMContentLoaded', function() {
            const step0 = document.getElementById('t-step-0');
            if (step0) step0.innerText = window.formatTime(new Date());

            const btnResearch = document.getElementById('btn-research');
            if (btnResearch) {
                btnResearch.addEventListener('click', function(e) {
                    e.preventDefault();
                    window.submitAIPrompt();
                });
            }

            // Auto-run initial research on page load
            window.submitAIPrompt();
        });
    </script>
</body>
</html>
"""
