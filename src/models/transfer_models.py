from django.db import models


class Transfer(models.Model):
    class State(models.TextChoices):
        CREATED = "created", "Created"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    ext_id = models.CharField(max_length=100, unique=True)
    sender_card_number = models.CharField(max_length=16)
    receiver_card_number = models.CharField(max_length=16)
    sender_card_expiry = models.CharField(max_length=5)  # MM/YY


    sender_phone = models.CharField(max_length=20, blank=True, null=True)
    receiver_phone = models.CharField(max_length=20, blank=True, null=True)
    sending_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.IntegerField()  # 643 = RUB, 840 = USD


    receiving_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.CREATED)
    try_count = models.IntegerField(default=0)
    otp = models.CharField(max_length=6, blank=True, null=True)


    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transfers"

    def __str__(self):
        return f"Transfer {self.ext_id} [{self.state}]"


class Error(models.Model):
    code = models.IntegerField(unique=True)
    en = models.CharField(max_length=255)
    ru = models.CharField(max_length=255)
    uz = models.CharField(max_length=255)

    class Meta:
        db_table = "errors"

    def __str__(self):
        return f"[{self.code}] {self.en}"