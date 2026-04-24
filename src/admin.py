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
        'colored_balance',
        'status_tag',
        'phone',
        'expiry_date',
        'owner'
    )

    list_filter = ('status', 'expiry_date')
    search_fields = ('card_number', 'phone')

    readonly_fields = ('balance',)

    def masked_card(self, obj):
        return "**** **** **** " + obj.card_number[-4:]

    masked_card.short_description = "Card"

    def colored_balance(self, obj):
        balance = Decimal(obj.balance or 0)
        color = "green" if balance > 0 else "red"

        # return format_html(
        #     '<b style="color:{};">{:,.2f} UZS</b>',
        #     color,
        #     balance
        # )

    colored_balance.short_description = "Balance"

    def status_tag(self, obj):
        colors = {
            'active': 'green',
            'inactive': 'orange',
            'expired': 'red',
            'blocked': 'black',
        }

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:6px;">{}</span>',
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
        'state_tag',
    )

    list_filter = ('state', 'currency')
    search_fields = ('ext_id', 'sender_card_number', 'receiver_card_number')

    readonly_fields = (
        'ext_id',
        'receiving_amount'
    )

    def short_id(self, obj):
        return (obj.ext_id[:10] + "...") if obj.ext_id else "-"

    short_id.short_description = "ID"

    def amount_display(self, obj):
        curr_map = {643: 'RUB', 840: 'USD', 860: 'UZS'}
        return f"{obj.sending_amount:,.2f} {curr_map.get(obj.currency, '')}"

    amount_display.short_description = "Amount"

    def state_tag(self, obj):
        colors = {
            'created': 'blue',
            'confirmed': 'green',
            'cancelled': 'red',
        }

        return format_html(
            '<b style="color:{};">{}</b>',
            colors.get(obj.state, 'black'),
            obj.state
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
        'salary',
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