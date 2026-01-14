import asyncio
import json
import os
import logging
from datetime import datetime
from random import shuffle

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

# 🔐 Токен бота от @BotFather
TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

users_file = "users.json"
pairs_file = "pairs.json"


# ---------- Работа с файлами ----------

def load_users():
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_users(users):
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_pairs():
    if os.path.exists(pairs_file):
        with open(pairs_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_pairs(pairs):
    with open(pairs_file, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)


# ---------- Клавиатура ----------

def get_optout_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отказаться от участия", callback_data="optout")]
    ])
    return keyboard


# ---------- Команды ----------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    users = load_users()

    if any(u["id"] == user_id for u in users):
        await message.answer(
            "👋 Ты уже участвуешь в Random Coffee!\n\n"
            "/status — статус участия",
            reply_markup=get_optout_keyboard(),
        )
        return

    user_data = {
        "id": user_id,
        "first_name": message.from_user.first_name or "Без имени",
        "username": message.from_user.username or "",
        "registered_at": datetime.now().isoformat(),
    }

    users.append(user_data)
    save_users(users)

    await message.answer(
        "✅ Ты зарегистрирован на Random Coffee!\n\n"
        "📅 Пары формируются каждое воскресенье в 17:00.\n"
        "☕ В это время ты получишь сообщение с парой для кофе.",
        reply_markup=get_optout_keyboard(),
    )


@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    user_id = message.from_user.id
    users = load_users()

    new_users = [u for u in users if u["id"] != user_id]
    save_users(new_users)

    await message.answer(
        "❌ Ты отказался от участия в Random Coffee.\n"
        "Если захочешь вернуться — нажми /start."
    )


@dp.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    users = load_users()

    if any(u["id"] == user_id for u in users):
        await message.answer(
            "✅ Ты сейчас участвуешь в Random Coffee.\n"
            "Чтобы отказаться, нажми кнопку ниже или используй /stop.",
            reply_markup=get_optout_keyboard(),
        )
    else:
        await message.answer(
            "❌ Ты не участвуешь сейчас.\n"
            "Напиши /start, чтобы присоединиться."
        )


@dp.message(Command("list"))
async def cmd_list(message: Message):
    users = load_users()
    count = len(users)
    await message.answer(f"👥 Всего участников: {count}")


@dp.message(Command("pairs"))
async def cmd_pairs(message: Message):
    pairs = load_pairs()
    if not pairs:
        await message.answer("🍵 Пар пока нет.")
        return

    msg = "🍵 Последние пары:\n\n"
    for i, pair in enumerate(pairs[-5:], 1):
        u1 = f"{pair['user1_name']} (@{pair['user1_username']})"
        u2 = f"{pair['user2_name']} (@{pair['user2_username']})"
        msg += f"{i}. {u1} ↔ {u2}\n"

    await message.answer(msg)


# ---------- Обработка кнопки "Отказаться" ----------

@dp.callback_query(lambda c: c.data == "optout")
async def process_optout(callback: CallbackQuery):
    user_id = callback.from_user.id
    users = load_users()

    new_users = [u for u in users if u["id"] != user_id]
    save_users(new_users)

    await callback.message.edit_text(
        "✅ Ты отказался от участия в Random Coffee.\n"
        "Если захочешь вернуться — напиши /start."
    )
    await callback.answer()


# ---------- Формирование пар ----------

async def form_pairs():
    """Формирует пары и рассылает уведомления."""
    users = load_users()
    if len(users) < 2:
        logging.info("Недостаточно пользователей для пар.")
        return

    user_list = [(u["id"], u) for u in users]
    shuffle(user_list)

    pairs = []
    i = 0
    while i < len(user_list) - 1:
        user1_id, user1_data = user_list[i]
        user2_id, user2_data = user_list[i + 1]

        pair = {
            "user1_id": int(user1_id),
            "user1_name": user1_data["first_name"],
            "user1_username": user1_data.get("username", ""),
            "user2_id": int(user2_id),
            "user2_name": user2_data["first_name"],
            "user2_username": user2_data.get("username", ""),
            "paired_at": datetime.now().isoformat(),
        }
        pairs.append(pair)
        i += 2

    save_pairs(pairs)
    logging.info(f"✅ Сформировано {len(pairs)} пар")

    for pair in pairs:
        try:
            await bot.send_message(
                pair["user1_id"],
                "☕ Твоя пара на кофе!\n\n"
                f"👤 {pair['user2_name']}\n"
                f"@{pair['user2_username']}\n\n"
                "Напишите друг другу! 🎉",
            )
            await bot.send_message(
                pair["user2_id"],
                "☕ Твоя пара на кофе!\n\n"
                f"👤 {pair['user1_name']}\n"
                f"@{pair['user1_username']}\n\n"
                "Напишите друг другу! 🎉",
            )
        except Exception as e:
            logging.error(f"Ошибка уведомления {pair['user1_id']}: {e}")


# ---------- Планировщик ----------

async def scheduler():
    """Каждую минуту проверяет, пора ли формировать пары."""
    from datetime import time

    PAIRS_TIME = time(17, 0)  # 17:00
    while True:
        now = datetime.now()
        if (
            now.weekday() == 6  # воскресенье
            and now.hour == PAIRS_TIME.hour
            and now.minute == PAIRS_TIME.minute
        ):
            await form_pairs()
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)


# ---------- Запуск ----------

async def main():
    logging.info("🚀 Random Coffee Bot запущен!")
    logging.info("Команды: /start /stop /status /list /pairs")
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
