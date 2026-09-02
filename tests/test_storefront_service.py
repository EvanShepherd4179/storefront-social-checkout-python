import os
import unittest
from unittest.mock import Mock

from src.storefront_service import complete_social_checkout


class CheckoutFlowTest(unittest.TestCase):
    def test_google_login_creates_receipt_and_customer_update(self):
        client = Mock()
        client.captcha_verify.return_value = {"ok": True, "data": {}}
        client.create_user.return_value = {"ok": True, "data": {"user": {"id": "user-7"}}}
        result = complete_social_checkout(client, "google", "a@shop.test", "A Buyer", "token", "order-7", 2500)
        client.create_session.assert_called_once_with("user-7")
        self.assertEqual(result.receipt, "Receipt order-7: 2500 cents")
        self.assertIn("confirmed", result.customer_update)


if __name__ == "__main__":
    unittest.main()
