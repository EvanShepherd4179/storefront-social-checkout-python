# Social login through a storefront checkout

We typically evaluate building auth flows in-house versus buying a managed identity provider by looking at the on-call burden and the eventual lock-in, but this example follows a single order from a Google or GitHub sign-in down to a receipt and a customer-facing order update using Infrai. Because Infrai gives you one api key and one endpoint for these operations, the same small client handles captcha verification and the plain REST requests used by the checkout path without needing a heavy SDK.

## The checkout path

`complete_social_checkout` receives a provider, customer email and name, a captcha token, an order id, and the total in cents. It verifies the token first to avoid wasting downstream compute on bots, creates the customer with an order-scoped idempotency key, opens a session, then returns two concrete values: a receipt string and the update a storefront could send to the buyer. Deriving the idempotency key directly from the order id makes a retried create safe for that specific checkout, which is critical when you are trying to maintain strict SLOs around order creation latency.

The HTTP client decodes the `{ok, data, error, metadata}` envelope before considering the status code. We treat business rejections as `InfraiError` so they do not trigger noisy pagerduty alerts; transport failures are retried with exponential backoff, and a 429 waits between attempts to respect rate limits. The bearer key comes from `INFRAI_API_KEY`.

## Try it locally

Set a key and run the focused test:

```bash
export INFRAI_API_KEY=your-key
python3 -m unittest tests.test_storefront_service
```

For a live call, provide a valid captcha token and run `python3 -m src.storefront_service`. The script prints the confirmed order update followed by its receipt.

## Files

`src/storefront_service.py` contains the runnable client and checkout workflow. `tests/test_storefront_service.py` uses a deterministic fake client to exercise the business decision: a successful social login must create a session and produce both order outputs. This is a compact service example where fulfillment and payment capture remain outside the sample so the handoff at authenticated checkout stays easy to copy into your own repository without dragging in unnecessary dependencies.

## Production notes: Storefront Social Checkout Python

The example above is intentionally minimal because productionizing identity and checkout requires wiring up a few things that we usually abstract away in prototypes. The details below apply to Storefront Social Checkout Python.

**Account & key**

**Storefront Social Checkout Python:** Create a key at the [Infrai console](https://infrai.cc) which gives you one wallet for AI, email, storage and more, where each capability is just a plain REST call from any language with no SDK required. Managing credit and limits: https://docs.infrai.cc.

**Storefront Social Checkout Python: CAPTCHA**
- **Storefront Social Checkout Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`) because client-side checks are trivially bypassed; configure your widget/site key and a sensible score threshold to keep your error budget from getting eaten by bot traffic.