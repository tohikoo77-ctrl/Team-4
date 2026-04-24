import re
import uuid
from datetime import date
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


# =========================
# LUHN ALGORITMI
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
# BANK CARD MODEL
# =========================
class BankCard(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("expired", "Expired"),
    )

    # Karta foydalanuvchiga bog'lanishi (bo'sh qolishi ham mumkin)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cards',
        verbose_name="Karta egasi"
    )

    card_number = models.CharField(max_length=16, unique=True, verbose_name="Karta raqami")
    expiry_date = models.DateField(verbose_name="Amal qilish muddati")
    phone = models.CharField(max_length=16, verbose_name="Telefon raqami")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="inactive")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Balans")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Karta raqamini tozalash
        cn = str(self.card_number).replace(" ", "")
        if not cn.isdigit() or len(cn) != 16:
            raise ValidationError({'card_number': "Karta raqami 16 ta raqamdan iborat bo'lishi kerak."})

        if not luhn_check(cn):
            raise ValidationError({'card_number': "Karta raqami xato (Luhn algoritmidan o'tmadi)."})
        self.card_number = cn

        # Telefon formati
        if self.phone:
            p = str(self.phone).strip()
            if not re.match(r'^\+998\d{9}$', p):
                raise ValidationError({'phone': "Telefon formati noto'g'ri: +998XXXXXXXXX"})

    def save(self, *args, **kwargs):
        # Muddatni tekshirish
        if self.expiry_date and self.expiry_date < date.today():
            self.status = "expired"

        # Agar owner biriktirilgan bo'lsa va inactive bo'lsa -> active qilish
        if self.owner and self.status == "inactive":
            self.status = "active"

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.card_number} | {self.owner.username if self.owner else 'No owner'}"


