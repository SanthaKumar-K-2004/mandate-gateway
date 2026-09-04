# RAZORPAY — Commerce Connector Architecture (M24)

## Abstract Connector Interface
All merchant integrations implement the `CommerceConnector` abstract base class ([`apps/api/commerce/connectors/base.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/connectors/base.py)):

```python
class CommerceConnector(abc.ABC):
    def get_capability(merchant_id: str, domain: str) -> CheckoutCapability: ...
    def revalidate_product(product: VerifiedProduct) -> CommerceConnectorResult: ...
    def prepare_checkout(request_id: str, product: VerifiedProduct, buyer_id: str) -> CommerceConnectorResult: ...
    def verify_order(order_id: str, payment_transaction_id: str) -> CommerceConnectorResult: ...
```

## Registry & Domain Mapping
`CommerceConnectorRegistry` ([`apps/api/commerce/connector_registry.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/connector_registry.py)) maintains an explicit map of seller domains to registered connectors. Unintegrated domains automatically resolve to `GenericWebCheckoutConnector`.

## Generic Web Checkout Connector & Security Rules
- Unintegrated merchant stores resolve to `GenericWebCheckoutConnector`.
- Provides secure redirect handoffs (`CHECKOUT_HANDOFF`).
- **Security Rule**: URL validator strictly blocks open redirects, `javascript:` URLs, `data:` URIs, `file:` schemes, and loopback/SSRF addresses (`127.0.0.1`, `169.254.169.254`).
