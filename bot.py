import os
import django
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from asgiref.sync import sync_to_async
from datetime import datetime

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from src.models.cart import BankCard

API_TOKEN = '8693429932:AAH5lZbQJMrMJFSAJW5Z1sjIng-ailzMMS0'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# --- FSM States ---
class AppStates(StatesGroup):
    waiting_for_login_user = State()
    waiting_for_login_pass = State()
    waiting_for_card_number = State()
    waiting_for_card_date = State()


# --- Keyboards ---
def get_login_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔑 Login")]], resize_keyboard=True)


def get_user_menu():
    kb = [
        [KeyboardButton(text="💳 Karta ulash"), KeyboardButton(text="🗂 Kartalarim")],
        [KeyboardButton(text="💰 Umumiy balans")],
        [KeyboardButton(text="🚪 Chiqish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# --- DB Operations ---
@sync_to_async
def get_user_by_id(user_id):
    return User.objects.filter(id=user_id).first()


@sync_to_async
def get_user_cards(user):
    # Foydalanuvchining barcha kartalarini olish
    cards = BankCard.objects.filter(owner=user)
    return list(cards)


@sync_to_async
def link_card_to_user(user, card_num, exp_date):
    # Kartani raqami va muddati orqali bazadan qidirish
    card = BankCard.objects.filter(card_number=card_num, expiry_date=exp_date).first()
    if card:
        if card.owner is None:
            card.owner = user
            card.status = "active"
            card.save()  # ADMIN PANELDA HAM KO'RINADI
            return "success"
        elif card.owner == user:
            return "already_yours"
        else:
            return "already_owned"
    return "not_found"


# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'user_id' in data:
        user = await get_user_by_id(data['user_id'])
        await message.answer(f"Xush kelibsiz, {user.username}!", reply_markup=get_user_menu())
    else:
        await message.answer("Tizimga kirish uchun Login qiling:", reply_markup=get_login_menu())


@dp.message(F.text == "🔑 Login")
async def login_start(message: types.Message, state: FSMContext):
    await message.answer("Username:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AppStates.waiting_for_login_user)


@dp.message(AppStates.waiting_for_login_user)
async def login_user(message: types.Message, state: FSMContext):
    await state.update_data(temp_user=message.text)
    await message.answer("Parol:")
    await state.set_state(AppStates.waiting_for_login_pass)


@dp.message(AppStates.waiting_for_login_pass)
async def login_pass(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await sync_to_async(authenticate)(username=data['temp_user'], password=message.text)

    if user:
        await state.update_data(user_id=user.id)  # SESSiyani saqlash
        await message.answer(f"✅ Login muvaffaqiyatli!", reply_markup=get_user_menu())
        await state.set_state(None)
    else:
        await message.answer("❌ Xato! Qayta urinib ko'ring:", reply_markup=get_login_menu())


# Karta ulash
@dp.message(F.text == "💳 Karta ulash")
async def card_start(message: types.Message, state: FSMContext):
    await message.answer("16 xonali karta raqami:")
    await state.set_state(AppStates.waiting_for_card_number)


@dp.message(AppStates.waiting_for_card_number)
async def card_num(message: types.Message, state: FSMContext):
    num = message.text.replace(" ", "")
    if len(num) == 16:
        await state.update_data(c_num=num)
        await message.answer("Amal qilish muddati (YYYY-MM-DD):")
        await state.set_state(AppStates.waiting_for_card_date)
    else:
        await message.answer("16 ta raqam bo'lishi kerak!")


@dp.message(AppStates.waiting_for_card_date)
async def card_date(message: types.Message, state: FSMContext):
    try:
        exp_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        user = await get_user_by_id(data['user_id'])

        res = await link_card_to_user(user, data['c_num'], exp_date)

        if res == "success":
            await message.answer("✅ Karta muvaffaqiyatli ulandi va admin panelda yangilandi!",
                                 reply_markup=get_user_menu())
        elif res == "already_yours":
            await message.answer("ℹ️ Bu karta sizga allaqachon ulangan.")
        elif res == "already_owned":
            await message.answer("⚠️ Bu karta boshqa odamga tegishli.")
        else:
            await message.answer("❌ Karta topilmadi.")
        await state.set_state(None)
    except Exception as e:
        await message.answer("Xato format! YYYY-MM-DD")


# KARTALARIM RO'YXATI
@dp.message(F.text == "🗂 Kartalarim")
async def my_cards(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await get_user_by_id(data.get('user_id'))
    cards = await get_user_cards(user)

    if cards:
        text = "💳 Sizning kartalaringiz:\n\n"
        for i, card in enumerate(cards, 1):
            text += f"{i}. {card.card_number} | {card.balance} UZS\n"
        await message.answer(text)
    else:
        await message.answer("Sizda hali ulangan kartalar yo'q.")


@dp.message(F.text == "🚪 Chiqish")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Tizimdan chiqdingiz.", reply_markup=get_login_menu())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())