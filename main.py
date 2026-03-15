import asyncio
import logging
import os
from dotenv import load_dotenv
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from huggingface_hub import InferenceClient

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot_memory.db")
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-2-2b-it")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SYSTEM_PROMPT = """
Ты — полезный и саркастичный помощник. 
Твоя задача — отвечать кратко и по делу.
(Вставь сюда свой промпт)
"""

MAX_HISTORY_MESSAGES = 10

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = InferenceClient(token=HF_TOKEN)

# --- БАЗА ДАННЫХ ---

async def init_db():
    """Создаёт таблицу и директорию для БД"""
    # Создаём директорию если не существует (для Railway)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON messages(user_id)
        """)
        await db.commit()
    logging.info(f"📁 База данных инициализирована: {DB_PATH}")

async def get_chat_history(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT role, content FROM messages 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, limit * 2))
        
        rows = await cursor.fetchall()
        rows.reverse()
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for row in rows:
            messages.append({"role": row["role"], "content": row["content"]})
        
        return messages

async def save_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO messages (user_id, role, content) 
            VALUES (?, ?, ?)
        """, (user_id, role, content))
        await db.commit()

async def clear_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        await db.commit()

async def trim_history(user_id: int, max_messages: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM messages 
            WHERE user_id = ? 
            AND id NOT IN (
                SELECT id FROM messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            )
        """, (user_id, user_id, max_messages * 2))
        await db.commit()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await clear_history(message.from_user.id)
    await message.answer("👋 Привет! Я готов к общению.\n\n🗑 История переписки очищена.\n\n💬 Напиши мне что-нибудь!")

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    await clear_history(message.from_user.id)
    await message.answer("🗑 История переписки очищена!")

@dp.message(Command("history"))
async def cmd_history(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT COUNT(*) as count FROM messages WHERE user_id = ?
        """, (message.from_user.id,))
        row = await cursor.fetchone()
        count = row[0] if row else 0
    
    await message.answer(f"📊 В памяти сохранено сообщений: {count}")

@dp.message(Command("ping"))
async def cmd_ping(message: Message):
    """Проверка работоспособности бота"""
    await message.answer("🏓 Понг! Бот работает исправно.")

@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    messages = await get_chat_history(user_id, MAX_HISTORY_MESSAGES)
    messages.append({"role": "user", "content": user_text})

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL_ID,
            messages=messages,
            temperature=0.7,
            max_tokens=512
        )
        
        bot_answer = response.choices[0].message.content

        await save_message(user_id, "user", user_text)
        await save_message(user_id, "assistant", bot_answer)
        await trim_history(user_id, MAX_HISTORY_MESSAGES)

        await message.answer(bot_answer)

    except Exception as e:
        logging.error(f"Ошибка HF API: {e}")
        await message.answer("⚠️ Извините, произошла ошибка при связи с мозгом бота.\n\nПопробуйте позже!")

# --- ЗАПУСК ---
async def main():
    await init_db()
    logging.info("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())