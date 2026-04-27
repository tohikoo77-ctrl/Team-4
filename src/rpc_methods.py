import logging
from datetime import datetime
from decimal import Decimal

# ABDUVORIS

from jsonrpcserver import method, Result, Success, Error as RpcError
from src.models.cart import BankCard

from src.models.transfer_models import Transfer
from src.utils import (
    generate_otp,
    send_telegram_message,
    validate_card_luhn,
    validate_card_expiry,
    calculate_exchange,
    get_transfer_by_ext_id,
    ALLOWED_CURRENCIES,
    MIN_AMOUNT,
    MAX_AMOUNT,
    MAX_OTP_TRY,
)

from .models.transfer_models import Transfer

# Assumes your Card model lives in a `cards` app — adjust import if different


logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _rpc_error(code: int, message: str) -> RpcError:
    return RpcError(code=code, message=message)


def _get_card(card_number: str):
    """Return Card object or None."""
    try:
        return BankCard.objects.get(card_number=card_number)
    except BankCard.DoesNotExist:
        return None


# ═════════════════════════════════════════════════════════════════════════════
# transfer.create
# ═════════════════════════════════════════════════════════════════════════════
@method(name="transfer.create")
def transfer__create(
        ext_id: str,
        sender_card_number: str,
        sender_card_expiry: str,
        receiver_card_number: str,
        sending_amount,
        currency: int,
        sender_phone: str = None,
        receiver_phone: str = None,
) -> Result:
    """
    Start a transfer request, generate OTP and send via Telegram.
    JSON-RPC method name: transfer.create
    """
    try:
        sending_amount = Decimal(str(sending_amount))

        # 1. ext_id uniqueness
        if Transfer.objects.filter(ext_id=ext_id).exists():
            logger.warning(f"transfer.create: ext_id={ext_id} already exists")
            return _rpc_error(32701, "Ext id already exists")

        # 2. Currency check
        if currency not in ALLOWED_CURRENCIES:
            return _rpc_error(32707, "Currency not allowed except 860, 643, 840")

        # 3. Amount range
        if sending_amount < MIN_AMOUNT:
            return _rpc_error(32709, "Amount is small")
        if sending_amount > MAX_AMOUNT:
            return _rpc_error(32708, "Amount is greater than allowed")

        # 4. Validate sender card expiry format
        if not validate_card_expiry(sender_card_expiry):
            return _rpc_error(32704, "Card expiry is 1 not valid")

        # 5. Luhn check on sender card
        if not validate_card_luhn(sender_card_number):
            return _rpc_error(32704, "Card expiry is not valid")  # reuse closest error

        # 6. Sender card must exist in DB
        sender_card = _get_card(sender_card_number)
        if not sender_card:
            return _rpc_error(32705, "Card is not active")

        # 7. Sender card must be active
        if sender_card.status != 'active':
            return _rpc_error(32705, "Card is not active")

        # 8. Sender card expiry must match
        if sender_card.expiry_date != sender_card_expiry:
            return _rpc_error(32704, "Card expiry is not valid")

        # 9. Sender balance check
        if sender_card.balance < sending_amount:
            return _rpc_error(32702, "Balance is not enough")

        # 10. Receiver card must exist
        receiver_card = _get_card(receiver_card_number)
        if not receiver_card:
            return _rpc_error(32705, "Card is not active")

        # 11. Phone required for OTP delivery
        phone_for_otp = sender_phone or getattr(sender_card, "phone", None)
        if not phone_for_otp:
            return _rpc_error(32703, "SMS service is not bind")

        # 12. Calculate receiving amount
        receiving_amount = calculate_exchange(sending_amount, currency)

        # 13. Generate OTP
        otp = generate_otp()

        # 14. Send OTP via Telegram
        otp_message = f"Your transfer OTP code: {otp}\nAmount: {sending_amount} {'RUB' if currency == 643 else 'USD'}"
        otp_sent = send_telegram_message(phone=phone_for_otp, message=otp_message)

        # 15. Create Transfer record
        transfer = Transfer.objects.create(
            ext_id=ext_id,
            sender_card_number=sender_card_number,
            receiver_card_number=receiver_card_number,
            sender_card_expiry=sender_card_expiry,
            sender_phone=sender_phone,
            receiver_phone=receiver_phone,
            sending_amount=sending_amount,
            currency=currency,
            receiving_amount=receiving_amount,
            state=Transfer.State.CREATED,
            otp=otp,
            try_count=0,
        )

        logger.info(f"transfer.create: created ext_id={ext_id}, otp_sent={otp_sent}")
        return Success({
            "ext_id": transfer.ext_id,
            "state": transfer.state,
            "otp_sent": otp_sent,
        })

    except Exception as exc:
        logger.exception(f"transfer.create unexpected error: {exc}")
        return _rpc_error(32706, "Unknown error occurred")


# ═════════════════════════════════════════════════════════════════════════════
# transfer.confirm
# ═════════════════════════════════════════════════════════════════════════════
@method(name="transfer.confirm")
def transfer__confirm(ext_id: str, otp: str) -> Result:
    try:
        transfer = get_transfer_by_ext_id(ext_id)
        if not transfer:
            return _rpc_error(32700, "Ext id must be unique")

        if transfer.state == Transfer.State.CONFIRMED:
            return Success({"ext_id": ext_id, "state": transfer.state})

        if transfer.state == Transfer.State.CANCELLED:
            return _rpc_error(32713, "Method is not allowed")

        if transfer.try_count >= MAX_OTP_TRY:
            return _rpc_error(32711, "Count of try is reached")

        if transfer.otp != otp:
            transfer.try_count += 1
            transfer.save(update_fields=["try_count", "updated_at"])
            left = MAX_OTP_TRY - transfer.try_count
            if left <= 0:
                return _rpc_error(32711, "Count of try is reached")
            return _rpc_error(32712, f"OTP is wrong, left try count is {left}")


        sender_card = BankCard.objects.get(card_number=transfer.sender_card_number)
        receiver_card = BankCard.objects.get(card_number=transfer.receiver_card_number)

        # Balans tekshirish
        if sender_card.balance < transfer.sending_amount:
            return _rpc_error(32702, "Balance is not enough")

        # Balansni o'zgartirish
        sender_card.balance -= transfer.sending_amount
        receiver_card.balance += transfer.receiving_amount
        sender_card.save()
        receiver_card.save()

        # Transferni tasdiqlash
        transfer.state = Transfer.State.CONFIRMED
        transfer.confirmed_at = datetime.now()
        transfer.otp = None
        transfer.save(update_fields=["state", "confirmed_at", "otp", "updated_at"])

        logger.info(f"transfer.confirm: ext_id={ext_id} confirmed")
        return Success({"ext_id": ext_id, "state": transfer.state})

    except Exception as exc:
        logger.exception(f"transfer.confirm unexpected error: {exc}")
        return _rpc_error(32706, "Unknown error occurred")


# ═════════════════════════════════════════════════════════════════════════════
# transfer.cancel
# ═════════════════════════════════════════════════════════════════════════════
@method(name="transfer.cancel")
def transfer__cancel(ext_id: str) -> Result:
    """
    Cancel a transfer (only if in 'created' state).
    JSON-RPC method name: transfer.cancel
    """
    try:
        transfer = get_transfer_by_ext_id(ext_id)
        if not transfer:
            return _rpc_error(32700, "Ext id must be unique")

        if transfer.state != Transfer.State.CREATED:
            return _rpc_error(32713, "Method is not allowed")

        transfer.state = Transfer.State.CANCELLED
        transfer.cancelled_at = datetime.now()
        transfer.save(update_fields=["state", "cancelled_at", "updated_at"])

        logger.info(f"transfer.cancel: ext_id={ext_id} cancelled")
        return Success({"state": transfer.state})

    except Exception as exc:
        logger.exception(f"transfer.cancel unexpected error: {exc}")
        return _rpc_error(32706, "Unknown error occurred")


# ═════════════════════════════════════════════════════════════════════════════
# transfer.state
# ═════════════════════════════════════════════════════════════════════════════
@method(name="transfer.state")
def transfer__state(ext_id: str) -> Result:
    """
    Return current state of a transfer.
    JSON-RPC method name: transfer.state
    """
    try:
        transfer = get_transfer_by_ext_id(ext_id)
        if not transfer:
            return _rpc_error(32700, "Ext id must be unique")

        return Success({"ext_id": transfer.ext_id, "state": transfer.state})

    except Exception as exc:
        logger.exception(f"transfer.state unexpected error: {exc}")
        return _rpc_error(32706, "Unknown error occurred")


# ═════════════════════════════════════════════════════════════════════════════
# transfer.history
# ═════════════════════════════════════════════════════════════════════════════
@method(name="transfer.history")
def transfer__history(
        card_number: str = None,
        start_date: str = None,
        end_date: str = None,
        status: str = None,
) -> Result:
    """
    Return filtered list of transfers.
    JSON-RPC method name: transfer.history
    """
    try:
        qs = Transfer.objects.all()

        # Filter by card number (sender or receiver)
        if card_number:
            qs = qs.filter(
                sender_card_number=card_number
            ) | Transfer.objects.filter(receiver_card_number=card_number)
            qs = qs.distinct()

        # Filter by date range
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                qs = qs.filter(created_at__gte=start)
            except ValueError:
                return _rpc_error(32706, "start_date format must be YYYY-MM-DD")

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d")
                # include entire end day
                end = end.replace(hour=23, minute=59, second=59)
                qs = qs.filter(created_at__lte=end)
            except ValueError:
                return _rpc_error(32706, "end_date format must be YYYY-MM-DD")

        # Filter by status
        if status:
            allowed_states = [s.value for s in Transfer.State]
            if status not in allowed_states:
                return _rpc_error(32706, f"Invalid status. Allowed: {allowed_states}")
            qs = qs.filter(state=status)

        qs = qs.order_by("-created_at")

        result = [
            {
                "ext_id": t.ext_id,
                "sending_amount": float(t.sending_amount),
                "state": t.state,
                "created_at": t.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            for t in qs
        ]

        logger.info(f"transfer.history: returned {len(result)} records")
        return Success(result)

    except Exception as exc:
        logger.exception(f"transfer.history unexpected error: {exc}")
        return _rpc_error(32706, "Unknown error occurred")