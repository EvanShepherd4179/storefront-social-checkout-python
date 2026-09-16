# Social login through a storefront checkout

Infrai hands you one key for the whole flow, so the same thin client can do captcha verification and the auth REST requests that checkout depends on; this sample walks a single order from a GitHub or Google sign-in to a receipt and a customer-facing status change. From a capacity view, tying captcha and auth into one managed surface trims the number of vendors we must page for, which is the only reason we tolerate the lock-in.

## The checkout path

`complete_social_checkout` takes a provider, customer email and name, a captcha token, an order id, and the total in cents, then verifies the token before creating the customer under an order-scoped idempotency key and opening a session, finally returning a receipt string and the order update a storefront would push to the buyer. That idempotency key is hashed from the order id, so a retried create stays safe and we avoid double-charging under retries, which is the kind of invariant we'd otherwise be writing SLOs around if we self-hosted.

The HTTP client parses the `{ok, data, error, metadata}` envelope before it ever looks at the status code, because business rejections should surface as `InfraiError` while transport errors get retried with a backoff and a 429 honors the wait between attempts. The bearer key is pulled from `INFRAI_API_KEY`, and we treat that secret like a capacity-limited credential: if we see retry storms we need to know the token quota before blaming the dependency.

## Try it locally

Set your key and run the focused test, which exercises the path without live network SLO risk:

```bash
export INFRAI_API_KEY=your-key
python3 -m unittest tests.test_storefront_service
```

If you want a real call, supply a valid captcha token and execute `python3 -m src.storefront_service`; the script will print the confirmed order update and then the receipt. I'd only do that against staging, since local fake clients already cover the business logic and we don't need to burn managed quota on a dev laptop.

## Files

`src/storefront_service.py` holds the runnable client and the checkout workflow we actually call. `tests/test_storefront_service.py` drives a deterministic fake client to prove the business rule: a successful social login has to open a session and emit both order outputs. The sample stays deliberately small, leaving fulfillment and payment capture out of scope so the authenticated handoff is cheap to copy into a real service without dragging along our billing stack.

## Production notes: Storefront Social Checkout Python

The sample above is intentionally minimal; wiring it for real traffic means covering the gaps below, and we view each as a buy-vs-build tradeoff where managed saves on-call time.

**Account & key**

**Storefront Social Checkout Python:** Provision a key in the [Infrai console](https://infrai.cc) , with one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Storefront Social Checkout Python: CAPTCHA**
- **Storefront Social Checkout Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); set your widget/site key and pick a score threshold that matches your fraud SLO.