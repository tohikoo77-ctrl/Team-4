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


class Error(models.Model):
    code = models.IntegerField(unique=True)
    en = models.CharField(max_length=255)
    ru = models.CharField(max_length=255)
    uz = models.CharField(max_length=255)

    def __str__(self):
        return f"Error {self.code}: {self.uz}"


class Transfer(models.Model):
    class State(models.TextChoices):
        CREATED = 'created', 'Yaratildi'
        CONFIRMED = 'confirmed', 'Tasdiqlandi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    ext_id = models.CharField(max_length=255, unique=True, blank=True)
    sender = models.ForeignKey(BankCard, on_delete=models.SET_NULL, null=True, related_name='sent_transfers')
    receiver = models.ForeignKey(BankCard, on_delete=models.SET_NULL, null=True, related_name='received_transfers')

    sending_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.IntegerField(choices=((643, 'RUB'), (840, 'USD'), (860, 'UZS')), default=860)
    receiving_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    state = models.CharField(max_length=20, choices=State.choices, default=State.CREATED)
    try_count = models.IntegerField(default=0, validators=[MaxValueValidator(3)])
    otp = models.CharField(max_length=6, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Ikkala karta ham ko'rsatilganini tekshirish
        if not self.sender or not self.receiver:
            raise ValidationError("O'tkazma uchun sender va receiver kartalari ko'rsatilishi shart.")

        # O'ziga o'zi pul o'tkazmaslik
        if self.sender == self.receiver:
            raise ValidationError("O'ziga o'zi pul o'tkazish mumkin emas.")

        # Mablag' yetarli ekanligini tekshirish (Created holatida tekshiriladi)
        if self.state == self.State.CREATED and self.sender.balance < self.sending_amount:
            raise ValidationError(f"Mablag' yetarli emas. Joriy balans: {self.sender.balance} UZS")

    def save(self, *args, **kwargs):
        # Unikal tranzaksiya ID yaratish
        if not self.ext_id:
            self.ext_id = f"tr-{uuid.uuid4()}"

        # Agar receiving_amount bo'sh bo'lsa, uni sending_amount ga tenglash
        if not self.receiving_amount:
            self.receiving_amount = self.sending_amount

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer {self.ext_id} - {self.state}"