import os
import django
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from asgiref.sync import sync_to_async

# =========================
# DJANGO INIT
# =========================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import authenticate, get_user_model
from src.models.cart import BankCard

User = get_user_model()

bot = Bot(token="8693429932:AAH5lZbQJMrMJFSAJW5Z1sjIng-ailzMMS0")
dp = Dispatcher(storage=MemoryStorage())


# =========================
# STATES
# =========================
class AppStates(StatesGroup):
    login_user = State()
    login_pass = State()
    card_number = State()
    card_expiry = State()


# =========================
# KEYBOARDS
# =========================
def menu_login():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔑 Login")]],
        resize_keyboard=True
    )


def menu_user():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Karta ulash"), KeyboardButton(text="🗂 Kartalarim")],
            [KeyboardButton(text="🔄 Update"), KeyboardButton(text="🚪 Chiqish")]
        ],
        resize_keyboard=True
    )


def menu_back():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Orqaga")]],
        resize_keyboard=True
    )


def inline_updates():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Versiya 1.1", callback_data="v11"),
         InlineKeyboardButton(text="Versiya 1.2", callback_data="v12")]
    ])


# =========================
# DB FUNCTIONS
# =========================
@sync_to_async
def get_user(user_id):
    if not user_id: return None
    return User.objects.filter(id=user_id).first()


@sync_to_async
def link_card(user, card_num, exp):
    try:
        card = BankCard.objects.get(card_number=card_num)
        if card.expiry_date != exp: return "expiry_error"
        if card.owner: return "taken" if card.owner != user else "already"
        card.owner = user
        card.status = "active"
        card.save()
        return "success"
    except BankCard.DoesNotExist:
        return "not_found"


@sync_to_async
def get_cards(user):
    return list(BankCard.objects.filter(owner=user))


# =========================
# HANDLERS
# =========================

# --- GLOBAL ORQAGA HANDLERI ---
@dp.message(F.text == "⬅️ Orqaga")
async def back_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await get_user(data.get("user_id"))

    await state.set_state(None)  # Holatni bekor qilish

    if user:
        await message.answer("Amal bekor qilindi.", reply_markup=menu_user())
    else:
        await message.answer("Bosh menyu.", reply_markup=menu_login())


@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await get_user(data.get("user_id"))
    if user:
        await message.answer(f"Salom {user.username}", reply_markup=menu_user())
    else:
        await message.answer("Tizimga kirish uchun Login qiling", reply_markup=menu_login())


# --- LOGIN ---
@dp.message(F.text == "🔑 Login")
async def login_start(message: types.Message, state: FSMContext):
    await message.answer("Username:", reply_markup=menu_back())
    await state.set_state(AppStates.login_user)


@dp.message(AppStates.login_user)
async def login_user_handler(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("Password:", reply_markup=menu_back())
    await state.set_state(AppStates.login_pass)


@dp.message(AppStates.login_pass)
async def login_pass_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await sync_to_async(authenticate)(username=data["username"], password=message.text)
    if user:
        await state.update_data(user_id=user.id)
        await message.answer("✔ Login muvaffaqiyatli!", reply_markup=menu_user())
        await state.set_state(None)
    else:
        await message.answer("❌ Xato login yoki parol", reply_markup=menu_login())
        await state.set_state(None)


# --- CARD LINKING ---
@dp.message(F.text == "💳 Karta ulash")
async def card_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("user_id"): return await message.answer("Avval login qiling!", reply_markup=menu_login())
    await message.answer("16 xonali karta raqami:", reply_markup=menu_back())
    await state.set_state(AppStates.card_number)


@dp.message(AppStates.card_number)
async def card_num_handler(message: types.Message, state: FSMContext):
    num = message.text.replace(" ", "")
    if len(num) != 16: return await message.answer("Xato! 16 ta raqam bo'lishi shart. Yoki orqaga qayting.",
                                                   reply_markup=menu_back())
    await state.update_data(card_num=num)
    await message.answer("Muddati (MM/YY):", reply_markup=menu_back())
    await state.set_state(AppStates.card_expiry)


@dp.message(AppStates.card_expiry)
async def card_exp_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await get_user(data.get("user_id"))
    result = await link_card(user, data["card_num"], message.text.strip())

    msgs = {
        "success": "✅ Karta ulandi!",
        "expiry_error": "❌ Sana noto'g'ri!",
        "taken": "⚠️ Karta band!",
        "already": "ℹ️ O'zingizniki",
        "not_found": "❌ Topilmadi"
    }
    await message.answer(msgs.get(result, "Xato"), reply_markup=menu_user())
    await state.set_state(None)


# --- VIEW CARDS & BALANCE ---
@dp.message(F.text == "🗂 Kartalarim")
async def my_cards(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await get_user(data.get("user_id"))
    if not user: return await message.answer("Login qiling", reply_markup=menu_login())

    cards = await get_cards(user)
    if not cards: return await message.answer("Kartalar yo'q")

    total = 0
    text = "💳 **Sizning kartalaringiz:**\n\n"
    for c in cards:
        total += float(c.balance)
        bal = "{:,.2f}".format(float(c.balance)).replace(",", " ")
        text += f"🔹 `{c.card_number[:4]} **** **** {c.card_number[-4:]}`\n"
        text += f"💰 Balans: **{bal} UZS** | 📅 {c.expiry_date}\n\n"

    text += f"━━━━━━━━━━━━━━\n💰 **Umumiy balans:** {'{:,.2f}'.format(total).replace(',', ' ')} UZS"
    await message.answer(text, parse_mode="Markdown")


# --- UPDATES SYSTEM ---
@dp.message(F.text == "🔄 Update")
async def show_updates(message: types.Message):
    await message.answer("Bot versiyalari haqida ma'lumot:", reply_markup=inline_updates())


@dp.callback_query(F.data == "v11")
async def version_11(call: types.CallbackQuery):
    msg = "🚀 **Versiya 1.1**\n\nBoshlang'ich imkoniyatlar: Django integratsiya va import tizimi."
    await call.message.edit_text(msg, parse_mode="Markdown", reply_markup=inline_updates())


@dp.callback_query(F.data == "v12")
async def version_12(call: types.CallbackQuery):
    msg = "🌟 **Versiya 1.2**\n\nYangi: Login, Karta ulash, Balans va Update tizimi."
    await call.message.edit_text(msg, parse_mode="Markdown", reply_markup=inline_updates())


# --- LOGOUT ---
@dp.message(F.text == "🚪 Chiqish")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Chiqdingiz.", reply_markup=menu_login())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())