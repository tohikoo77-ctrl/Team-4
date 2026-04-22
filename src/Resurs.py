from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models.cart import BankCard, Transfer


class CardResource(resources.ModelResource):
    """
    BankCard modelini Excel/CSV formatida boshqarish uchun
    """

    class Meta:
        model = BankCard
        # Eksport/Import qilinadigan ustunlar
        fields = ('id', 'card_number', 'expiry_date', 'phone', 'status', 'balance')
        # Qaysi ustun bo'yicha ma'lumotlarni yangilash (asosan card_number orqali)
        import_id_fields = ('card_number',)
        export_order = ('id', 'card_number', 'balance', 'status', 'phone', 'expiry_date')


class TransferResource(resources.ModelResource):
    """
    Transfer modelini Excel/CSV formatida boshqarish uchun
    """
    # Foreign key ustunlarini tushunarliroq qilish (ID o'rniga karta raqami)
    sender = fields.Field(
        column_name='sender',
        attribute='sender',
        widget=ForeignKeyWidget(BankCard, 'card_number'))

    receiver = fields.Field(
        column_name='receiver',
        attribute='receiver',
        widget=ForeignKeyWidget(BankCard, 'card_number'))

    class Meta:
        model = Transfer
        fields = (
            'ext_id', 'sender', 'receiver', 'sending_amount',
            'currency', 'state', 'created_at', 'confirmed_at'
        )
        export_order = fields