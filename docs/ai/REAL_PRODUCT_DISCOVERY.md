# RAZORPAY — Real Product Discovery Architecture (M23)

## Overview
RAZORPAY transitions product discovery from mock data to real-time live external sources using `LiveDataOrchestrator` and `ProductTruthValidator`.

## Provider Hierarchy
1. **Tavily Search API (`TavilyWebSearchProvider`)**: Real-time web product search (`TAVILY_API_KEY`).
2. **Brave Search API (`BraveWebSearchProvider`)**: Fallback real-time search API (`BRAVE_SEARCH_API_KEY`).
3. **Open-Source Public Search (`OpenSourceWebSearchProvider`)**: Free public commerce API (no API key required).

## Verification States & Badges
- **`VERIFIED`**: Verified live source evidence from active search APIs.
- **`SOURCE_BACKED`**: Verified open-source or public commerce catalog evidence.
- **`STALE`**: Evidence retrieval timestamp exceeds freshness window.
- **`CONFLICTED`**: Multiple sources yield conflicting prices or stock status.
- **`UNVERIFIED`**: Price or product ID missing from source evidence. Automatic payment execution is strictly prohibited.

## Evidence Preservation
Every candidate product preserves:
`source_provider`, `source_url`, `retrieval_timestamp`, `product_evidence`, `price_evidence`, `merchant_evidence`, `availability_evidence`, `verification_status`.
