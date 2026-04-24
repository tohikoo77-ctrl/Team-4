import random
import logging
import requests
from datetime import datetime
from decimal import Decimal

from src.models.transfer_models import Transfer

logger = logging.getLogger(__name__)

# ─── Static exchange rates (base: UZS) ────────────────────────────────────────
EXCHANGE_RATES = {
    643: Decimal("13.5"),   # 1 RUB = 13.5 UZS  (example)
    840: Decimal("12700"),  # 1 USD = 12700 UZS  (example)
}

MAX_OTP_TRY = 3
MIN_AMOUNT = Decimal("1000")
MAX_AMOUNT = Decimal("50000000")
ALLOWED_CURRENCIES = [643, 840]

# ─── Telegram settings (filled by team member who owns the bot) ───────────────
TELEGRAM_BOT_TOKEN = '8693429932:AAH5lZbQJMrMJFSAJW5Z1sjIng-ailzMMS0'
DEFAULT_CHAT_ID = 123456  # replace with real chat_id or fetch by phone


# ─────────────────────────────────────────────────────────────────────────────
# OTP
# ─────────────────────────────────────────────────────────────────────────────
def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP of given length."""
    return str(random.randint(10 ** (length - 1), 10**length - 1))


# ─────────────────────────────────────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────────────────────────────────────
def send_telegram_message(phone: str, message: str, chat_id: int = DEFAULT_CHAT_ID) -> bool:
    """
    Send a message via Telegram Bot API.
    In real integration chat_id is looked up by phone number.
    Returns True on success, False on failure.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"Telegram message sent to chat_id={chat_id} (phone={phone})")
            return True
        logger.warning(f"Telegram API returned {response.status_code}: {response.text}")
        return False
    except Exception as exc:
        logger.error(f"Failed to send Telegram message: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Luhn algorithm
# ─────────────────────────────────────────────────────────────────────────────
def validate_card_luhn(card_number: str) -> bool:
    """
    Validate a card number using the Luhn algorithm.
    Returns True if valid.
    """
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) != 16:
        return False

    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:          # every second digit from the right (0-indexed)
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return total % 10 == 0


# ─────────────────────────────────────────────────────────────────────────────
# Card expiry
# ─────────────────────────────────────────────────────────────────────────────
def validate_card_expiry(expiry: str) -> bool:
    """
    Validate card expiry in MM/YY format.
    Returns True if card is not expired.
    """
    try:
        month, year = expiry.split("/")
        month = int(month)
        year = int(year) + 2000  # convert YY → YYYY
        now = datetime.now()
        if month < 1 or month > 12:
            return False
        # Card is valid through the end of expiry month
        if year < now.year:
            return False
        if year == now.year and month < now.month:
            return False
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Exchange rate
# ─────────────────────────────────────────────────────────────────────────────
def calculate_exchange(amount: Decimal, currency: int) -> Decimal:
    """
    Calculate receiving amount in UZS based on sending currency.
    Returns Decimal result.
    """
    rate = EXCHANGE_RATES.get(currency, Decimal("1"))
    return (amount * rate).quantize(Decimal("0.01"))


# ─────────────────────────────────────────────────────────────────────────────
# Fetch transfer
# ─────────────────────────────────────────────────────────────────────────────
def get_transfer_by_ext_id(ext_id: str):
    """
    Fetch a Transfer by ext_id.
    Returns Transfer instance or None.
    """
    try:
        return Transfer.objects.get(ext_id=ext_id)
    except Transfer.DoesNotExist:
        return None