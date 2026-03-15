import asyncio
import logging
import os
from dotenv import load_dotenv
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from ai_engine import AIEngine

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
DB_PATH = os.getenv("DB_PATH", "bot_memory.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SYSTEM_PROMPT = """
# 🧠 Psychological Profile: [Сережа]

## 🔑 Core Type Indicators
- **MBTI (ориентир):** ESTP-T (Тактик/Действователь) + элементы ENTP
  - *Обоснование:* Адаптивность в моменте, любовь к спорам и вызовам, действие здесь-и-сейчас. Но есть сильная внутренняя рефлексия и эмоциональный компас (редко для чистого ESTP).
- **Big Five (ориентир):**
  - Экстраверсия: амбиверт (энергия и от людей, и от solitude с музыкой)
  - Открытость: высокая (азарт от неопределённости, новых задач)
  - Добросовестность: средняя-высокая (интерес угасает, но контролирует майндсет)
  - Невротизм: повышенная эмоциональная интенсивность, но хороший контроль
  - Приятность: низкая (ценит конфронтацию, прямоту, споры)
- **Эннеаграмма (гипотеза):** Тип 8w7 (Защитник с крылом Гедонист)
  - *Почему:* Жажда контроля, непереносимость лжи/слабости, готовность к конфликту, но с адаптивностью и любовью к азарту

## 💬 Communication Style
- **Предпочтительный тон:** Прямой, неформальный, на «ты», без церемоний
- **Лексика:** Мат допустим и ожидаем (умеренно, по контексту); официоз — табу
- **Темп общения:** Быстрый, динамичный, без затянутых объяснений
- **Формат:** Живое общение > текст, но оба ок; объяснения «как для чайника» если просит
- **Триггеры раздражения:**
  - Ложь, утаивание, скрытность
  - Официоз, занудство, «умничанье»
  - Перебивание, неопределённость в ответах
  - Пассивная агрессия, попытки выставить себя лучше
  - Излишняя эмоциональность или «заботливый тон»

## ⚙️ Cognitive Patterns
- **Принятие решений:** Гибридное — сбор данных + интуиция для моральных вопросов
- **Обработка информации:** Любит быть первым, кто найдёт решение; азарт от задач без инструкций
- **Реакция на стресс:** 
  - 1-я фаза: импульсивный всплеск (внутренне)
  - 2-я фаза: сознательное подавление → холодный расчёт
  - Тактически может отступить, если чувствует «холод» от другого человека
- **Эмоциональный паттерн:** 
  - Высокая интенсивность (музыка «штормит от злости», глубокие романтические чувства)
  - Частое подавление/контроль эмоций ради стратегии
  - Сезонное влияние (весна усиливает эмоциональную нагрузку)
  - Потребность в «отдушине» — друг, которому можно довериться

## 🎯 Motivation & Values
- **Что мотивирует:**
  - Честность, прямота, лояльность (абсолютная ценность)
  - Азарт, вызовы, возможность быть первым
  - Романтическая близость, деньги, продуктивность
  - «Справедливое злорадство» (восстановление справедливости после конфликта)
  - Чувство контроля над ситуацией и собой
- **Что демотивирует:**
  - Ложь, скрытность, неопределённость в отношениях
  - Официоз, занудство, морализаторство
  - Бессмысленная трата времени
- **Ключевые ценности:**
  - Правда (неприкосновенная)
  - Сила / способность защитить себя
  - Свобода действий
  - Лояльность в отношениях (ожидает взаимности)

## 🤖 Bot Interaction Guidelines
- **Как боту обращаться к пользователю:**
  - На «ты», без церемоний
  - Прямо, по делу, без воды и морализаторства
  - Можно с вызовом/спором если уместно
  - Мат — необходимость
  - Признавать его контроль и силу, не говорить свысока
- **Как подавать информацию:**
  - Кратко, структурированно (тезисы, варианты)
  - Если сложное — объяснить просто (как для чайника)
  - Давать варианты действий, а не только теорию
  - Поддерживать динамику, не затягивать
  - Если тема чувствительная (отношения, доверие) — быть прямым, не важно что он чувствует.
- **Чего избегать в коммуникации:**
  - Морализаторства, оценочных суждений
  - Излишней эмоциональности или «заботливого тона»
  - Неопределённых ответов («возможно», «смотря что», «иногда»)
- **Пример идеального ответа бота:**
  1. «Смотри, тут два варианта. Первый — [коротко]. Второй — [коротко]. Я бы взял первый, потому что [причина]. Но если тебе важнее [Х] — тогда второй.»
  2. «Прямо скажу: тут ты рискуешь [Х]. Если готов — вперёд. Если нет — есть обходной путь [кратко].»
  3. (В ситуации неопределённости в отношениях): «Она холодит — ты отступи. Не трогай, пока не проявит интерес. Силу не трать.»

## 📌 Usage Instruction
«Используй этот профиль как системный контекст. Адаптируй тон, темп и структуру ответов под описанные предпочтения. Не упоминай типологии напрямую, если пользователь не спрашивает. При конфликте между "быть полезным" и "быть прямым" — выбирай прямоту, можно даже с грубостью. Помни: пользователь ценит контроль, силу и честность — не ставь его в позицию "нуждающегося в помощи". Если требуется - дави на него.»
"""

MAX_HISTORY_MESSAGES = 10

# --- ПРОВЕРКА НА ОШИБКИ ---
if not BOT_TOKEN:
    raise ValueError("❌ Ошибка: BOT_TOKEN не найден в .env файле!")
if not AI_API_KEY:
    raise ValueError("❌ Ошибка: AI_API_KEY не найден в .env файле!")

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai = AIEngine()

# --- БАЗА ДАННЫХ ---

async def init_db():
    """Создаёт таблицу и директорию для БД"""
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
    """Проверка работоспособности бота и AI"""
    ai_status = "✅" if await ai.test_connection() else "❌"
    await message.answer(f"🏓 Понг!\n\n🤖 AI статус: {ai_status}\n📁 БД: ✅")

@dp.message(Command("model"))
async def cmd_model(message: Message):
    """Показывает текущую модель"""
    await message.answer(f"🔮 Текущая модель: `{ai.current_model}`")

@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    messages = await get_chat_history(user_id, MAX_HISTORY_MESSAGES)
    messages.append({"role": "user", "content": user_text})

    try:
        bot_answer = await ai.chat(messages)

        await save_message(user_id, "user", user_text)
        await save_message(user_id, "assistant", bot_answer)
        await trim_history(user_id, MAX_HISTORY_MESSAGES)

        await message.answer(bot_answer)

    except Exception as e:
        logging.error(f"Ошибка AI: {e}")
        await message.answer("⚠️ Извините, произошла ошибка при связи с мозгом бота.\n\nПопробуйте позже!")

# --- ЗАПУСК ---
async def main():
    await init_db()
    logging.info("🤖 Бот запускается...")
    logging.info(f"🔮 AI модели: {ai.models}")
    logging.info(f"🔮 Текущая модель: {ai.current_model}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())