from django.db import models
from django.conf import settings


class Credit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=12, decimal_places=2)  # so‘ralgan summa
    years = models.PositiveIntegerField()  # muddat (1–15)

    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    is_approved = models.BooleanField(default=False)
    reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount}"