from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from decimal import Decimal

from .models.cart import BankCard
from .models.transfer_models import Error, Transfer
from .models import User
from .Resurs import CardResource, TransferResource
from django.contrib.auth.admin import UserAdmin


# =========================
# BANK CARD ADMIN
# =========================
@admin.register(BankCard)
class BankCardAdmin(ImportExportModelAdmin):
    resource_class = CardResource

    list_display = (
        'masked_card',
        'colored_balance',   # ← красивый баланс
        'status_tag',
        'phone',
        'expiry_date',
        'owner'
    )

    list_filter = ('status', 'expiry_date')
    search_fields = ('card_number', 'phone')

    def masked_card(self, obj):
        return "**** **** **** " + obj.card_number[-4:]
    masked_card.short_description = "Card"

    def colored_balance(self, obj):
        balance = Decimal(obj.balance or 0)
        color = "#28a745" if balance > 0 else "#dc3545"
        # форматируем: 1000000 → 1,000,000.00
        formatted = f"{balance:,.2f}"
        return format_html(
            '<b style="color:{}; font-size:14px;">{} UZS</b>',
            color,
            formatted
        )
    colored_balance.short_description = "Balans"

    def status_tag(self, obj):
        colors = {
            'active': '#28a745',
            'inactive': '#ffc107',
            'expired': '#dc3545',
            'blocked': '#343a40',
        }
        return format_html(
            '<span style="background:{};color:white;padding:4px 10px;border-radius:6px;font-size:12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status
        )
    status_tag.short_description = "Status"


# =========================
# ERROR ADMIN
# =========================
@admin.register(Error)
class ErrorAdmin(admin.ModelAdmin):
    list_display = ('code', 'uz', 'ru', 'en')
    search_fields = ('code', 'uz', 'ru', 'en')
    list_per_page = 20


# =========================
# TRANSFER ADMIN
# =========================
@admin.register(Transfer)
class TransferAdmin(ImportExportModelAdmin):
    resource_class = TransferResource

    list_display = (
        'short_id',
        'sender_card_number',
        'receiver_card_number',
        'amount_display',
        'receiving_display',  # ← qabul qilingan summa
        'state_tag',
    )

    list_filter = ('state', 'currency')
    search_fields = ('ext_id', 'sender_card_number', 'receiver_card_number')

    readonly_fields = (
        'ext_id',
        'receiving_amount',
        'created_at',
        'updated_at',
    )

    def short_id(self, obj):
        return (obj.ext_id[:10] + "...") if obj.ext_id else "-"
    short_id.short_description = "ID"

    def amount_display(self, obj):
        curr_map = {643: 'RUB', 840: 'USD', 860: 'UZS'}
        # 5000000 → 5,000,000.00
        formatted = f"{obj.sending_amount:,.2f}"
        return format_html(
            '<b style="color:#c62828;">{} {}</b>',
            formatted,
            curr_map.get(obj.currency, '')
        )
    amount_display.short_description = "Yuborilgan"

    def receiving_display(self, obj):
        if obj.receiving_amount:
            formatted = f"{obj.receiving_amount:,.2f}"
            return format_html(
                '<b style="color:#2e7d32;">{} UZS</b>',
                formatted
            )
        return "-"
    receiving_display.short_description = "Qabul qilingan"

    def state_tag(self, obj):
        colors = {
            'created': '#17a2b8',
            'confirmed': '#28a745',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<b style="color:{};">● {}</b>',
            colors.get(obj.state, 'black'),
            obj.state.upper()
        )
    state_tag.short_description = "State"


# =========================
# USER ADMIN
# =========================
@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'phone_number',
        'workplace',
        'salary_display',   # ← красивая зарплата
        'is_married',
        'is_staff',
    )

    list_filter = ('is_married', 'is_staff', 'is_superuser')
    search_fields = ('username', 'phone_number', 'workplace')

    fieldsets = UserAdmin.fieldsets + (
        ("Extra Info", {
            'fields': (
                'phone_number',
                'workplace',
                'salary',
                'is_married',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra Info", {
            'fields': (
                'phone_number',
                'workplace',
                'salary',
                'is_married',
            )
        }),
    )

    def salary_display(self, obj):
        if obj.salary:
            return f"{obj.salary:,.2f} UZS"
        return "-"
    salary_display.short_description = "Salary"