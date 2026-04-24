from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
import qrcode
import base64
from io import BytesIO

from .models.cart import BankCard
from .models.transfer_models import Error, Transfer
from .Resurs import CardResource, TransferResource


# =========================
# BANK CARD ADMIN
# =========================
@admin.register(BankCard)
class BankCardAdmin(ImportExportModelAdmin):
    resource_class = CardResource

    list_display = (
        'card_number',
        'colored_balance',
        'status_tag',
        'phone',
        'expiry_date'
    )

    list_filter = ('status', 'expiry_date', 'balance')
    search_fields = ('card_number', 'phone')
    readonly_fields = ('balance_display',)

    def colored_balance(self, obj):
        color = "green" if obj.balance > 0 else "red"
        return format_html('<b style="color: {};">{} UZS</b>', color, f"{obj.balance:,.2f}")
    colored_balance.short_description = "Joriy Balans"

    def status_tag(self, obj):
        colors = {
            'active': '#28a745',
            'inactive': '#ffc107',
            'expired': '#dc3545',
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
    readonly_fields = ('ext_id', 'created_at', 'updated_at', 'receiving_amount', 'qr_code')

    def ext_id_short(self, obj):
        return obj.ext_id[:13] + "..." if obj.ext_id else "Noma'lum"
    ext_id_short.short_description = "Tranzaksiya ID"

    def amount_with_currency(self, obj):
        curr_map = {643: 'RUB', 840: 'USD', 860: 'UZS'}
        return f"{obj.sending_amount:,.2f} {curr_map.get(obj.currency, '')}"
    amount_with_currency.short_description = "O'tkazma summasi"

    def state_tag(self, obj):
        bg_colors = {
            'created': '#17a2b8',
            'confirmed': '#28a745',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<b style="color: {}; text-transform: uppercase;">● {}</b>',
            bg_colors.get(obj.state, 'black'),
            obj.get_state_display()
        )
    state_tag.short_description = "Holat"

    # ─── QR CODE ──────────────────────────────────────────────
    def qr_code(self, obj):
        try:
            curr_map = {643: 'RUB', 840: 'USD', 860: 'UZS'}
            currency_name = curr_map.get(obj.currency, 'UZS')

            receiving = float(obj.receiving_amount) if obj.receiving_amount else 0.0
            sending = float(obj.sending_amount) if obj.sending_amount else 0.0

            # ✅ Sonlarni oldin string formatga o'tkazamiz
            sending_str = f"{sending:,.2f}"
            receiving_str = f"{receiving:,.2f}"

            state_colors = {
                'created': '#17a2b8',
                'confirmed': '#28a745',
                'cancelled': '#dc3545',
            }
            state_icons = {
                'created': '🔵',
                'confirmed': '✅',
                'cancelled': '❌',
            }
            state_color = state_colors.get(obj.state, '#333')
            state_icon = state_icons.get(obj.state, '❓')

            created_str = obj.created_at.strftime('%d/%m/%Y %H:%M') if obj.created_at else '-'
            confirmed_str = obj.confirmed_at.strftime('%d/%m/%Y %H:%M') if obj.confirmed_at else '-'
            cancelled_str = obj.cancelled_at.strftime('%d/%m/%Y %H:%M') if obj.cancelled_at else '-'

            qr_text = (
                f"=== TRANSFER MA'LUMOTLARI ===\n"
                f"Transfer ID   : {obj.ext_id}\n"
                f"Yuboruvchi    : {obj.sender_card_number}\n"
                f"Qabul qiluvchi: {obj.receiver_card_number}\n"
                f"Summa         : {sending_str} {currency_name}\n"
                f"Qabul summa   : {receiving_str} UZS\n"
                f"Holat         : {obj.state.upper()}\n"
                f"Yaratilgan    : {created_str}\n"
                f"Tasdiqlangan  : {confirmed_str}\n"
                f"Bekor qilingan: {cancelled_str}"
            )

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=7,
                border=3,
            )
            qr.add_data(qr_text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#1a1a2e", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode()

            return format_html(
                '''
                <div style="margin-top:10px; font-family:'Segoe UI',Arial,sans-serif; max-width:720px;">

                    <!-- Header -->
                    <div style="
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        color: white;
                        padding: 14px 20px;
                        border-radius: 12px 12px 0 0;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    ">
                        <span style="font-size:22px;">📱</span>
                        <span style="font-size:16px; font-weight:700; letter-spacing:0.5px;">Transfer QR Code</span>
                        <span style="
                            margin-left: auto;
                            background: {};
                            color: white;
                            padding: 4px 14px;
                            border-radius: 20px;
                            font-size: 12px;
                            font-weight: 700;
                            letter-spacing: 1px;
                        ">{} {}</span>
                    </div>

                    <!-- Body -->
                    <div style="
                        background: #ffffff;
                        border: 1px solid #e0e0e0;
                        border-top: none;
                        border-radius: 0 0 12px 12px;
                        padding: 20px;
                        display: flex;
                        gap: 24px;
                        flex-wrap: wrap;
                        align-items: flex-start;
                    ">
                        <!-- QR rasm -->
                        <div style="text-align:center; flex-shrink:0;">
                            <img
                                src="data:image/png;base64,{}"
                                style="
                                    width: 210px;
                                    height: 210px;
                                    border: 3px solid #1a1a2e;
                                    border-radius: 10px;
                                    display: block;
                                "
                            />
                            <p style="margin:8px 0 0; font-size:11px; color:#999;">
                                📷 Skanerlash uchun kamera oching
                            </p>
                        </div>

                        <!-- Info -->
                        <div style="flex:1; min-width:260px;">

                            <!-- Transfer ID -->
                            <div style="margin-bottom:12px;">
                                <div style="font-size:11px; color:#999; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">🔑 Transfer ID</div>
                                <div style="
                                    font-family: monospace;
                                    font-size: 14px;
                                    font-weight: 700;
                                    color: #1a1a2e;
                                    background: #f0f4ff;
                                    padding: 8px 12px;
                                    border-radius: 8px;
                                    border-left: 4px solid #1a1a2e;
                                ">{}</div>
                            </div>

                            <!-- Kartalar -->
                            <div style="display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap;">
                                <div style="flex:1; min-width:140px;">
                                    <div style="font-size:11px; color:#999; text-transform:uppercase; margin-bottom:4px;">📤 Yuboruvchi</div>
                                    <div style="
                                        font-family: monospace;
                                        font-size: 13px;
                                        font-weight: 600;
                                        color: #7b3f00;
                                        background: #fff8e1;
                                        padding: 7px 10px;
                                        border-radius: 8px;
                                        border-left: 4px solid #ffc107;
                                    ">{}</div>
                                </div>
                                <div style="flex:1; min-width:140px;">
                                    <div style="font-size:11px; color:#999; text-transform:uppercase; margin-bottom:4px;">📥 Qabul qiluvchi</div>
                                    <div style="
                                        font-family: monospace;
                                        font-size: 13px;
                                        font-weight: 600;
                                        color: #1b5e20;
                                        background: #e8f5e9;
                                        padding: 7px 10px;
                                        border-radius: 8px;
                                        border-left: 4px solid #28a745;
                                    ">{}</div>
                                </div>
                            </div>

                            <!-- Summalar -->
                            <div style="display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap;">
                                <div style="flex:1; min-width:120px;">
                                    <div style="font-size:11px; color:#999; text-transform:uppercase; margin-bottom:4px;">💸 Yuborilgan</div>
                                    <div style="
                                        font-size: 16px;
                                        font-weight: 800;
                                        color: #c62828;
                                        background: #fff3f3;
                                        padding: 7px 10px;
                                        border-radius: 8px;
                                        border-left: 4px solid #dc3545;
                                    ">{} <span style="font-size:12px;">{}</span></div>
                                </div>
                                <div style="flex:1; min-width:120px;">
                                    <div style="font-size:11px; color:#999; text-transform:uppercase; margin-bottom:4px;">💰 Qabul qilingan</div>
                                    <div style="
                                        font-size: 16px;
                                        font-weight: 800;
                                        color: #1b5e20;
                                        background: #f1f8e9;
                                        padding: 7px 10px;
                                        border-radius: 8px;
                                        border-left: 4px solid #28a745;
                                    ">{} <span style="font-size:12px;">UZS</span></div>
                                </div>
                            </div>

                            <!-- Vaqtlar -->
                            <div style="
                                display: flex;
                                gap: 8px;
                                flex-wrap: wrap;
                                background: #f8f9fa;
                                padding: 10px;
                                border-radius: 8px;
                            ">
                                <div style="flex:1; min-width:100px; text-align:center;">
                                    <div style="font-size:10px; color:#999; text-transform:uppercase;">🕐 Yaratilgan</div>
                                    <div style="font-size:12px; font-weight:600; color:#333; margin-top:2px;">{}</div>
                                </div>
                                <div style="flex:1; min-width:100px; text-align:center;">
                                    <div style="font-size:10px; color:#999; text-transform:uppercase;">✅ Tasdiqlangan</div>
                                    <div style="font-size:12px; font-weight:600; color:#28a745; margin-top:2px;">{}</div>
                                </div>
                                <div style="flex:1; min-width:100px; text-align:center;">
                                    <div style="font-size:10px; color:#999; text-transform:uppercase;">❌ Bekor qilingan</div>
                                    <div style="font-size:12px; font-weight:600; color:#dc3545; margin-top:2px;">{}</div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
                ''',
                state_color, state_icon, obj.state.upper(),
                encoded,
                obj.ext_id,
                obj.sender_card_number,
                obj.receiver_card_number,
                sending_str, currency_name,   # ✅ {:,.2f} o'rniga tayyor string
                receiving_str,                 # ✅ {:,.2f} o'rniga tayyor string
                created_str,
                confirmed_str,
                cancelled_str,
            )

        except Exception as e:
            return format_html('<p style="color:red;">QR Code xatolik: {}</p>', str(e))

    qr_code.short_description = "📱 QR Code"

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('ext_id', 'state', 'sender_card_number', 'receiver_card_number')
        }),
        ('Pul miqdori va Valyuta', {
            'fields': ('sending_amount', 'receiving_amount', 'currency')
        }),
        ('Xavfsizlik (OTP)', {
            'fields': ('otp', 'try_count'),
            'description': 'OTP kodi va urinishlar soni'
        }),
        ("Vaqt ko'rsatkichlari", {
            'fields': ('created_at', 'confirmed_at', 'cancelled_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('📱 QR Code', {
            'fields': ('qr_code',),
        }),
    )

    def has_delete_permission(self, request, obj=None):
        if obj and obj.state == 'confirmed':
            return False
        return True