import uuid
from django.db import models
from django.conf import settings


class Credit(models.Model):
    # 1. ID'ni UUID qilish (agar migratsiyada UUID tanlangan bo'lsa)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=12, decimal_places=2)  # so‘ralgan summa
    years = models.PositiveIntegerField()  # muddat (1–15)

    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Tasdiqlanganlik holati
    is_approved = models.BooleanField(default=False)

    # 2. Bekor qilinganlik holati (Xatolik chiqmasligi uchun default=False shart)
    is_cancelled = models.BooleanField(default=False)

    reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Tasdiqlangan" if self.is_approved else "Rad etilgan"
        if self.is_cancelled:
            status = "Bekor qilingan"
        return f"{self.user.username} - {self.amount} ({status})"

    class Meta:
        verbose_name = "Kredit"
        verbose_name_plural = "Kreditlar"