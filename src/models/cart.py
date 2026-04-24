import re
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings  # settings.AUTH_USER_MODEL uchun


# =========================
# LUHN ALGORITHM
# =========================
def luhn_check(card_number: str) -> bool:
    """Karta raqami haqiqatda mavjud bo'lishi mumkinligini tekshiradi"""
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
        ("active", "Faol"),
        ("inactive", "Nofaol"),
        ("expired", "Muddati o'tgan"),
        ("blocked", "Bloklangan"),
    )

    # get_user_model() o'rniga settings.AUTH_USER_MODEL ishlatildi
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cards",
        verbose_name="Egasi"
    )

    card_number = models.CharField(
        "Karta raqami",
        max_length=16,
        unique=True,
        help_text="16 xonali raqam"
    )

    expiry_date = models.CharField(
        "Amal qilish muddati",
        max_length=5,
        help_text="Format: MM/YY (masalan: 12/26)"
    )

    phone = models.CharField(
        "Bog'langan telefon",
        max_length=16
    )

    status = models.CharField(
        "Holati",
        max_length=10,
        choices=STATUS_CHOICES,
        default="inactive"
    )

    balance = models.DecimalField(
        "Balans",
        max_digits=15,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bank kartasi"
        verbose_name_plural = "Bank kartalari"
        ordering = ['-created_at']

    # =========================
    # VALIDATION
    # =========================
    def clean(self):
        super().clean()

        if self.card_number:
            cn = str(self.card_number).replace(" ", "").strip()
            if not cn.isdigit() or len(cn) != 16:
                raise ValidationError({"card_number": "Karta raqami 16 ta raqamdan iborat bo'lishi shart!"})
            if not luhn_check(cn):
                raise ValidationError({"card_number": "Karta raqami xato (Luhn tekshiruvi xatosi)"})
            self.card_number = cn

        if self.expiry_date:
            if not re.match(r'^(0[1-9]|1[0-2])\/\d{2}$', self.expiry_date):
                raise ValidationError({"expiry_date": "Format xato! Namuna: 12/26"})

        if self.phone:
            if not re.match(r'^\+998\d{9}$', self.phone):
                raise ValidationError({"phone": "Telefon formati: +998XXXXXXXXX"})

    # =========================
    # SAVE LOGIC
    # =========================
    def save(self, *args, **kwargs):
        if self.owner and self.status == "inactive":
            self.status = "active"

        # Bu metod clean() ni va boshqa validatorlarni ishga tushiradi
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # HELPERS
    # =========================
    @property
    def mask_number(self):
        """Kartani maskalash: 8600 **** **** 1234"""
        if self.card_number and len(self.card_number) == 16:
            return f"{self.card_number[:4]} **** **** {self.card_number[-4:]}"
        return self.card_number

    # =========================
    # STRING
    # =========================
    def __str__(self):
        owner_str = self.owner.username if self.owner else "Egasiz"
        return f"{self.mask_number} ({owner_str})"