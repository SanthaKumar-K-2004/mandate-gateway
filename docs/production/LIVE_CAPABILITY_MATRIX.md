# RAZERPAY — Live Connector Capability Matrix

## Matrix Classifications

| Provider / Domain | Environment | Discovery | Verification | Direct API Order | Signed Handoff | Classification |
|---|---|---|---|---|---|---|
| `world.openfoodfacts.org` | `LIVE` | ✅ Live | ✅ Verified | ❌ No API | ✅ Yes | `LIVE REACHABLE BUT CHECKOUT HANDOFF ONLY` |
| `cafeacme.local` | `SANDBOX` | ✅ Live | ✅ Verified | ✅ Direct API | ✅ Yes | `SANDBOX` |
| Generic Web Stores | `LIVE` | ✅ Live | ✅ Verified | ❌ No API | ✅ Yes | `LIVE REACHABLE BUT CHECKOUT HANDOFF ONLY` |

> [!NOTE]
> Autonomous direct API checkout is supported for merchants with configured OAuth2/API credentials (`RealPlatformConnector`). For arbitrary public merchants without direct APIs, secure signed checkout handoff is used.
