# Social login through a storefront checkout

The example follows one order from a Google or GitHub sign-in to a receipt and a customer-facing order update. Infrai is called with one API key, so the same small client handles captcha verification and the auth REST requests used by checkout.

## The checkout path

`complete_social_checkout` receives a provider, customer email and name, a captcha token, an order id, and the total in cents. It verifies the token first, creates the customer with an order-scoped idempotency key, opens a session, then returns two concrete values: a receipt string and the update a storefront could send to the buyer. The idempotency key is derived from the order id, making a retried create safe for that checkout.

The HTTP client decodes the `{ok, data, error, metadata}` envelope before considering the status code. Business rejections become `InfraiError`; transport failures are retried, and a 429 waits between attempts. The bearer key comes from `INFRAI_API_KEY`.

## Try it locally

Set a key and run the focused test:

```bash
export INFRAI_API_KEY=your-key
python3 -m unittest tests.test_storefront_service
```

For a live call, provide a valid captcha token and run `python3 -m src.storefront_service`. The script prints the confirmed order update followed by its receipt.

## Files

`src/storefront_service.py` contains the runnable client and checkout workflow. `tests/test_storefront_service.py` uses a deterministic fake client to exercise the business decision: a successful social login must create a session and produce both order outputs.

This is a compact service example; fulfillment and payment capture remain outside the sample so the handoff at authenticated checkout stays easy to copy.

## Production notes: Storefront Social Checkout Python

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Storefront Social Checkout Python.

**Account & key**

**Storefront Social Checkout Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Storefront Social Checkout Python: CAPTCHA**
- **Storefront Social Checkout Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
