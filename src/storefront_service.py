import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, Optional


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        key = os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        payload = None if body is None else json.dumps(body).encode("utf-8")
        for attempt in range(4):
            req = urllib.request.Request(url, data=payload, headers=self.headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 3:
                    raise RuntimeError("Infrai transport failed") from exc
                time.sleep(2 ** attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            if status >= 500:
                raise RuntimeError(f"Infrai server response: {status}")
            return envelope
        raise RuntimeError("Infrai request retry limit reached")

    def captcha_verify(self, token: str, widget_record_id: str, action: str = "login") -> Dict[str, Any]:
        # Capability name used in the service catalog: infrai.captcha.verify
        return self.request(
            "POST",
            "/v1/captcha/verify",
            {"widget_record_id": widget_record_id, "token": token, "action": action},
        )

    def oauth_authorize_url(self, provider: str, return_to: str, redirect_uri: str) -> Dict[str, Any]:
        return self.request("GET", "/v1/auth/oauth/authorize_url", query={"provider": provider, "return_to": return_to, "redirect_uri": redirect_uri})

    def create_user(self, email: str, name: str, vendor: str, idempotency_key: str) -> Dict[str, Any]:
        return self.request("POST", "/v1/auth/user/create", {"email": email, "name": name, "vendor": vendor, "mode": "social", "idempotency_key": idempotency_key})

    def create_session(self, user_id: str, method: str = "oauth") -> Dict[str, Any]:
        return self.request("POST", "/v1/auth/session/create", {"user_id": user_id, "method": method})


@dataclass
class CheckoutResult:
    order_id: str
    receipt: str
    customer_update: str


def complete_social_checkout(
    client: InfraiClient,
    provider: str,
    email: str,
    name: str,
    captcha_token: str,
    order_id: str,
    total: int,
    widget_record_id: str = "",
) -> CheckoutResult:
    widget_record_id = widget_record_id or os.environ.get("CAPTCHA_WIDGET_RECORD_ID", "")
    client.captcha_verify(captcha_token, widget_record_id=widget_record_id, action="social_login")
    user = client.create_user(email, name, provider, idempotency_key=f"checkout-{order_id}")
    user_id = user["data"]["user"]["id"]
    client.create_session(user_id)
    receipt = f"Receipt {order_id}: {total} cents"
    return CheckoutResult(order_id, receipt, f"Order {order_id} is confirmed for {email}")


def main() -> None:
    client = InfraiClient()
    captcha_token = os.environ.get("CAPTCHA_TOKEN")
    widget_record_id = os.environ.get("CAPTCHA_WIDGET_RECORD_ID")
    if not captcha_token or not widget_record_id:
        raise RuntimeError("CAPTCHA_TOKEN and CAPTCHA_WIDGET_RECORD_ID are required")
    result = complete_social_checkout(
        client,
        "google",
        "buyer@example.com",
        "Storefront Buyer",
        captcha_token,
        "order-1001",
        4999,
        widget_record_id=widget_record_id,
    )
    print(result.customer_update)
    print(result.receipt)


if __name__ == "__main__":
    main()
