import re
import uuid
from datetime import date
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


# =========================
# LUHN ALGORITMI (KARTA VALIDATSIYASI)
# =========================
def luhn_check(card_number):
    """Karta raqami matematik jihatdan to'g'riligini tekshiradi."""
    digits = [int(d) for d in card_number]
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10 == 0


# =========================
# MODELS
# =========================

class BankCard(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("expired", "Expired"),
    )

    card_number = models.CharField(max_length=16, unique=True, verbose_name="Karta raqami")
    expiry_date = models.DateField(verbose_name="Amal qilish muddati")
    phone = models.CharField(max_length=16, verbose_name="Telefon raqami")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="inactive")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Balans")

    def clean(self):
        # Karta raqamini tozalash va Luhn algoritmi bilan tekshirish
        cn = str(self.card_number).replace(" ", "")
        if not cn.isdigit() or len(cn) != 16:
            raise ValidationError({'card_number': "Karta raqami 16 ta raqamdan iborat bo'lishi kerak."})

        if not luhn_check(cn):
            raise ValidationError({'card_number': "Karta raqami xato (Luhn algoritmidan o'tmadi)."})
        self.card_number = cn

        # Telefon raqami formati (+998XXXXXXXXX)
        if self.phone:
            p = str(self.phone).strip()
            if not re.match(r'^\+998\d{9}$', p):
                raise ValidationError({'phone': "Telefon formati noto'g'ri: +998XXXXXXXXX"})
            self.phone = p

        # Amal qilish muddati va balans
        if self.expiry_date and self.expiry_date < date.today():
            self.status = "expired"

        if self.balance < 0:
            raise ValidationError({'balance': "Balans manfiy bo'lishi mumkin emas."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.card_number} ({self.balance} UZS)"


