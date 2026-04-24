"""
Tests for Transfer JSON-RPC API.
Run with:  python manage.py test transfers
"""
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse

from src.models.transfer_models import Transfer
from src.utils import (
    generate_otp,
    validate_card_luhn,
    validate_card_expiry,
    calculate_exchange,
    get_transfer_by_ext_id,
)


# ─── Utility function tests ────────────────────────────────────────────────────

class TestGenerateOTP(TestCase):
    def test_length(self):
        otp = generate_otp()
        self.assertEqual(len(otp), 6)

    def test_numeric(self):
        otp = generate_otp()
        self.assertTrue(otp.isdigit())

    def test_custom_length(self):
        otp = generate_otp(length=4)
        self.assertEqual(len(otp), 4)


class TestLuhnValidation(TestCase):
    def test_valid_card(self):
        # Known valid Luhn number
        self.assertTrue(validate_card_luhn("4532015112830366"))

    def test_invalid_card(self):
        self.assertFalse(validate_card_luhn("1234567890123456"))

    def test_wrong_length(self):
        self.assertFalse(validate_card_luhn("123456789"))

    def test_non_digit(self):
        self.assertFalse(validate_card_luhn("453201511283036A"))


class TestCardExpiry(TestCase):
    def test_valid_future_expiry(self):
        self.assertTrue(validate_card_expiry("12/30"))

    def test_expired_card(self):
        self.assertFalse(validate_card_expiry("01/20"))

    def test_invalid_format(self):
        self.assertFalse(validate_card_expiry("1230"))
        self.assertFalse(validate_card_expiry("13/30"))

    def test_invalid_month(self):
        self.assertFalse(validate_card_expiry("00/30"))


class TestCalculateExchange(TestCase):
    def test_rub_conversion(self):
        result = calculate_exchange(Decimal("1000"), 643)
        self.assertIsInstance(result, Decimal)
        self.assertGreater(result, 0)

    def test_usd_conversion(self):
        result = calculate_exchange(Decimal("100"), 840)
        self.assertIsInstance(result, Decimal)
        self.assertGreater(result, 0)


class TestGetTransferByExtId(TestCase):
    def setUp(self):
        Transfer.objects.create(
            ext_id="tr-test-001",
            sender_card_number="4532015112830366",
            receiver_card_number="4532015112830366",
            sender_card_expiry="12/30",
            sending_amount=Decimal("10000"),
            currency=643,
            state=Transfer.State.CREATED,
            otp="123456",
        )

    def test_found(self):
        t = get_transfer_by_ext_id("tr-test-001")
        self.assertIsNotNone(t)
        self.assertEqual(t.ext_id, "tr-test-001")

    def test_not_found(self):
        t = get_transfer_by_ext_id("tr-nonexistent")
        self.assertIsNone(t)


# ─── RPC endpoint tests ────────────────────────────────────────────────────────

def rpc(client, method, params, req_id=1):
    """Helper to send a JSON-RPC request and return parsed response."""
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
    response = client.post(
        "/api/transfer/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    return response.json()


def make_mock_card(
        card_number="4532015112830366",
        expiry="12/30",
        is_active=True,
        balance=Decimal("100000"),
        phone="998901234567",
):
    card = MagicMock()
    card.card_number = card_number
    card.expiry = expiry
    card.is_active = is_active
    card.balance = balance
    card.phone = phone
    return card


class TestTransferCreate(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("transfers.rpc_methods._get_card")
    @patch("transfers.rpc_methods.send_telegram_message", return_value=True)
    def test_create_success(self, mock_tg, mock_get_card):
        sender = make_mock_card("4532015112830366")
        receiver = make_mock_card("4532736430654178")
        mock_get_card.side_effect = lambda cn: sender if cn == "4532015112830366" else receiver

        resp = rpc(self.client, "transfer.create", {
            "ext_id": "tr-001",
            "sender_card_number": "4532015112830366",
            "sender_card_expiry": "12/30",
            "receiver_card_number": "4532736430654178",
            "sending_amount": 15000,
            "currency": 643,
            "sender_phone": "998901234567",
        })

        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["state"], "created")
        self.assertTrue(resp["result"]["otp_sent"])

    def test_duplicate_ext_id(self):
        Transfer.objects.create(
            ext_id="tr-dup",
            sender_card_number="4532015112830366",
            receiver_card_number="4532015112830366",
            sender_card_expiry="12/30",
            sending_amount=Decimal("10000"),
            currency=643,
            state=Transfer.State.CREATED,
            otp="000000",
        )

        resp = rpc(self.client, "transfer.create", {
            "ext_id": "tr-dup",
            "sender_card_number": "4532015112830366",
            "sender_card_expiry": "12/30",
            "receiver_card_number": "4532736430654178",
            "sending_amount": 15000,
            "currency": 643,
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], 32701)

    def test_invalid_currency(self):
        resp = rpc(self.client, "transfer.create", {
            "ext_id": "tr-bad-cur",
            "sender_card_number": "4532015112830366",
            "sender_card_expiry": "12/30",
            "receiver_card_number": "4532736430654178",
            "sending_amount": 15000,
            "currency": 999,
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], 32707)

    def test_amount_too_small(self):
        resp = rpc(self.client, "transfer.create", {
            "ext_id": "tr-small",
            "sender_card_number": "4532015112830366",
            "sender_card_expiry": "12/30",
            "receiver_card_number": "4532736430654178",
            "sending_amount": 1,
            "currency": 643,
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], 32709)


class TestTransferConfirm(TestCase):
    def setUp(self):
        self.client = Client()
        self.transfer = Transfer.objects.create(
            ext_id="tr-confirm-001",
            sender_card_number="4532015112830366",
            receiver_card_number="4532736430654178",
            sender_card_expiry="12/30",
            sending_amount=Decimal("15000"),
            currency=643,
            state=Transfer.State.CREATED,
            otp="654321",
        )

    def test_correct_otp(self):
        resp = rpc(self.client, "transfer.confirm", {
            "ext_id": "tr-confirm-001",
            "otp": "654321",
        })
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["state"], "confirmed")

    def test_wrong_otp(self):
        resp = rpc(self.client, "transfer.confirm", {
            "ext_id": "tr-confirm-001",
            "otp": "000000",
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], 32712)

    def test_max_tries_exceeded(self):
        self.transfer.try_count = 3
        self.transfer.save()
        resp = rpc(self.client, "transfer.confirm", {
            "ext_id": "tr-confirm-001",
            "otp": "000000",
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], 32711)

    def test_not_found(self):
        resp = rpc(self.client, "transfer.confirm", {
            "ext_id": "tr-missing",
            "otp": "123456",
        })
        self.assertIn("error", resp)


class TestTransferCancel(TestCase):
    def setUp(self):
        self.client = Client()
        self.transfer = Transfer.objects.create(
            ext_id="tr-cancel-001",
            sender_card_number="4532015112830366",
            receiver_card_number="4532736430654178",
            sender_card_expiry="12/30",
            sending_amount=Decimal("15000"),
            currency=643,
            state=Transfer.State.CREATED,
            otp="111111",
        )

    def test_cancel_created(self):
        resp = rpc(self.client, "transfer.cancel", {"ext_id": "tr-cancel-001"})
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["state"], "cancelled")

    def test_cancel_already_confirmed(self):
        self.transfer.state = Transfer.State.CONFIRMED
        self.transfer.save()
        resp = rpc(self.client, "transfer.cancel", {"ext_id": "tr-cancel-001"})
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], 32713)


class TestTransferState(TestCase):
    def setUp(self):
        self.client = Client()
        Transfer.objects.create(
            ext_id="tr-state-001",
            sender_card_number="4532015112830366",
            receiver_card_number="4532736430654178",
            sender_card_expiry="12/30",
            sending_amount=Decimal("15000"),
            currency=643,
            state=Transfer.State.CONFIRMED,
            otp=None,
        )

    def test_get_state(self):
        resp = rpc(self.client, "transfer.state", {"ext_id": "tr-state-001"})
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["state"], "confirmed")

    def test_not_found(self):
        resp = rpc(self.client, "transfer.state", {"ext_id": "tr-missing"})
        self.assertIn("error", resp)


class TestTransferHistory(TestCase):
    def setUp(self):
        self.client = Client()
        Transfer.objects.create(
            ext_id="tr-h-001",
            sender_card_number="4532015112830366",
            receiver_card_number="4532736430654178",
            sender_card_expiry="12/30",
            sending_amount=Decimal("15000"),
            currency=643,
            state=Transfer.State.CONFIRMED,
            otp=None,
        )
        Transfer.objects.create(
            ext_id="tr-h-002",
            sender_card_number="4532015112830366",
            receiver_card_number="4532736430654178",
            sender_card_expiry="12/30",
            sending_amount=Decimal("5000"),
            currency=643,
            state=Transfer.State.CANCELLED,
            otp=None,
        )

    def test_history_all(self):
        resp = rpc(self.client, "transfer.history", {})
        self.assertIn("result", resp)
        self.assertEqual(len(resp["result"]), 2)

    def test_history_by_status(self):
        resp = rpc(self.client, "transfer.history", {"status": "confirmed"})
        self.assertIn("result", resp)
        self.assertEqual(len(resp["result"]), 1)
        self.assertEqual(resp["result"][0]["state"], "confirmed")

    def test_history_by_card(self):
        resp = rpc(self.client, "transfer.history", {"card_number": "4532015112830366"})
        self.assertIn("result", resp)
        self.assertEqual(len(resp["result"]), 2)

    def test_history_empty(self):
        resp = rpc(self.client, "transfer.history", {"card_number": "9999999999999999"})
        self.assertIn("result", resp)
        self.assertEqual(resp["result"], [])
