from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

# Modellaringiz va Resource fayllarini import qilish
from .models.cart import BankCard
from .models.transfer_models import Error, Transfer
from .Resurs import CardResource, TransferResource


# =========================
# BANK CARD ADMIN
# =========================
@admin.register(BankCard)
class BankCardAdmin(ImportExportModelAdmin):
    # Excel/CSV eksport-import uchun resource klassi
    resource_class = CardResource

    # Ro'yxatda ko'rinadigan ustunlar
    list_display = (
        'card_number',
        'colored_balance',
        'status_tag',
        'phone',
        'expiry_date'
    )

    # Filtrlar
    list_filter = ('status', 'expiry_date', 'balance')

    # Qidiruv maydonlari
    search_fields = ('card_number', 'phone')

    # Faqat o'qish uchun maydonlar
    readonly_fields = ('balance_display',)

    # Balansni chiroyli ko'rsatish (Rangli)
    def colored_balance(self, obj):
        color = "green" if obj.balance > 0 else "red"
        return format_html('<b style="color: {};">{} UZS</b>', color, f"{obj.balance:,.2f}")

    colored_balance.short_description = "Joriy Balans"

    # Statusni chiroyli ko'rsatish
    def status_tag(self, obj):
        colors = {
            'active': '#28a745',  # Yashil
            'inactive': '#ffc107',  # Sariq
            'expired': '#dc3545',  # Qizil
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )

    status_tag.short_description = "Status"

    def balance_display(self, obj):
        return f"{obj.balance:,.2f} UZS"

    balance_display.short_description = "Balans (Tasdiqlangan)"


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
    # Excel/CSV eksport-import uchun resource klassi
    resource_class = TransferResource

    list_display = (
        'ext_id_short',
        'sender_card_number',
        'receiver_card_number',
        'amount_with_currency',
        'state_tag',
        'created_at'
    )

    list_filter = ('state', 'currency', 'created_at')
    search_fields = ('ext_id', 'sender_card_number', 'receiver_card_number')

    # Tahrirlab bo'lmaydigan maydonlar (Moliyaviy xavfsizlik uchun)
    readonly_fields = ('ext_id', 'created_at', 'updated_at', 'receiving_amount')

    # Tranzaksiya ID sini qisqartirib ko'rsatish
    def ext_id_short(self, obj):
        return obj.ext_id[:13] + "..." if obj.ext_id else "Noma'lum"

    ext_id_short.short_description = "Tranzaksiya ID"

    # Summani valyuta bilan ko'rsatish
    def amount_with_currency(self, obj):
        curr_map = {643: 'RUB', 840: 'USD', 860: 'UZS'}
        return f"{obj.sending_amount:,.2f} {curr_map.get(obj.currency, '')}"

    amount_with_currency.short_description = "O'tkazma summasi"

    # Transfer holati (State) uchun rangli teglar
    def state_tag(self, obj):
        bg_colors = {
            'created': '#17a2b8',  # Moviy
            'confirmed': '#28a745',  # Yashil
            'cancelled': '#dc3545',  # Qizil
        }
        return format_html(
            '<b style="color: {}; text-transform: uppercase;">● {}</b>',
            bg_colors.get(obj.state, 'black'),
            obj.get_state_display()
        )

    state_tag.short_description = "Holat"

    # Admin panelda maydonlarni guruhlash (Fieldsets)
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('ext_id', 'state', 'sender_card_number', 'receiver_card_number')
        }),
        ('Pul miqdori va Valyuta', {
            'fields': ('sending_amount', 'receiving_amount', 'currency')
        }),
        ('Xavfsizlik (OTP)', {
            'fields': ('otp', 'try_count'),
            'description': 'OTP kodi va urinishlar soni'
        }),
        ('Vaqt ko\'rsatkichlari', {
            'fields': ('created_at', 'confirmed_at', 'cancelled_at', 'updated_at'),
            'classes': ('collapse',)  # Bu bo'limni yashirib qo'yish imkoniyati
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # Tasdiqlangan pullarni admin ham o'chira olmasligi kerak (Xavfsizlik uchun)
        if obj and obj.state == 'confirmed':
            return False
        return True