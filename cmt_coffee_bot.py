import asyncio
import json
import os
import logging
from datetime import datetime, time
from random import shuffle
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F

# Токен бота от @BotFather
TOKEN = "8373377672:AAH22VKRlmNnFXScTz9rj9mxAWc5MULv3cs"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

users_file = "users.json"
pairs_file = "pairs.json"
PAIRS_TIME = time(17, 0)  # Воскресенье 17:00

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

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    users = load_users()
    
    user_data = {
        "id": user_id,
        "first_name": message.from_user.first_name or "Без имени",
        "username": message.from_user.username or "",
        "registered_at": datetime.now().isoformat()
    }
    
    if any(u["id"] == user_id for u in users):
        await message.answer("👋 Ты уже зарегистрирован! /status")
        return
    
    users.append(user_data)
    save_users(users)
    await message.answer(
        "✅ Зарегистрирован на Random Coffee!\n\n"
        "📅 Пары формируются каждое воскресенье в 17:00\n"
        "☕ Получишь уведомление с парой для кофе"
    )

@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    user_id = message.from_user.id
    users = load_users()
    users = [u for u in users if u["id"] != user_id]
    save_users(users)
    await message.answer("❌ Отписался от Random Coffee.")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    users = load_users()
    if any(u["id"] == user_id for u in users):
        await message.answer("✅ Ты в списке на Random Coffee.")
    else:
        await message.answer("❌ Не зарегистрирован. /start")

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
    for i, pair in enumerate(pairs[-5:], 1):  # Последние 5
        u1 = f"{pair['user1_name']} (@{pair['user1_username']})"
        u2 = f"{pair['user2_name']} (@{pair['user2_username']})"
        msg += f"{i}. {u1} ↔ {u2}\n"
    
    await message.answer(msg)

async def form_pairs():
    """Формирует пары в воскресенье 17:00"""
    users = load_users()
    if len(users) < 2:
        logging.info("Недостаточно пользователей")
        return
    
    # user_list как в вашем коде
    user_list = [(u["id"], u) for u in users]
    shuffle(user_list)
    
    pairs = []
    i = 0
    while i < len(user_list) - 1:  # -1 чтобы избежать IndexError
        user1_id, user1_data = user_list[i]
        user2_id, user2_data = user_list[i + 1]
        
        pair = {
            "user1_id": int(user1_id),
            "user1_name": user1_data["first_name"],
            "user1_username": user1_data.get("username", ""),
            "user2_id": int(user2_id),
            "user2_name": user2_data["first_name"],
            "user2_username": user2_data.get("username", ""),
            "paired_at": datetime.now().isoformat()
        }
        pairs.append(pair)
        i += 2
    
    save_pairs(pairs)
    logging.info(f"✅ Сформировано {len(pairs)} пар")
    
    # Уведомления
    for pair in pairs:
        try:
            await bot.send_message(
                pair["user1_id"],
                f"☕ **Твоя пара на кофе!**\n\n"
                f"👤 {pair['user2_name']}\n"
                f"@{pair['user2_username']}\n\n"
                f"Напишите друг другу! 🎉"
            )
            await bot.send_message(
                pair["user2_id"],
                f"☕ **Твоя пара на кофе!**\n\n"
                f"👤 {pair['user1_name']}\n"
                f"@{pair['user1_username']}\n\n"
                f"Напишите друг другу! 🎉"
            )
        except Exception as e:
            logging.error(f"Ошибка уведомления {pair['user1_id']}: {e}")

async def scheduler():
    """Проверяет время для формирования пар"""
    while True:
        now = datetime.now()
        if (now.weekday() == 6 and  # Воскресенье
            now.hour == 17 and 
            now.minute == 0):
            await form_pairs()
            await asyncio.sleep(3600)  # Ждём час до следующей проверки
        else:
            await asyncio.sleep(60)  # Проверяем каждую минуту

async def main():
    logging.info("🚀 Random Coffee Bot запущен!")
    logging.info("Команды: /start /stop /status /list /pairs")
    
    # Запуск планировщика пар в фоне
    asyncio.create_task(scheduler())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
