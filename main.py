"""
DiceRoll Sync — MVP
Единый файл: FastAPI + Telegram Bot + WebSocket + SQLite
"""

import asyncio
import os
import random
import sqlite3
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ─── Настройки ───────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен. Создай .env файл или задай переменную окружения.")
DB_PATH = os.getenv("DB_PATH", "dice_rolls.db")
FRONTEND_PATH = os.getenv("FRONTEND_PATH", "index.html")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# ─── WebSocket менеджер ──────────────────────────────────────
class ConnectionManager:
    """Хранит активные WebSocket-подключения и рассылает сообщения."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Отправить сообщение всем подключённым клиентам."""
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ─── База данных ─────────────────────────────────────────────
def init_db():
    """Создать таблиц rolls, если её нет."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            result INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_roll(player_name: str, result: int, timestamp: str):
    """Сохранить результат броска в SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO rolls (player_name, result, timestamp) VALUES (?, ?, ?)",
        (player_name, result, timestamp)
    )
    conn.commit()
    conn.close()

def get_history(limit: int = 10):
    """Получить последние N бросков из БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT player_name, result, timestamp FROM rolls ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows

def get_stats():
    """Получить общую статистику по всем броскам."""
    from collections import Counter
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT result FROM rolls ORDER BY id ASC"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    results = [r["result"] for r in rows]
    counter = Counter(results)

    avg = sum(results) / len(results)
    most_common_val, most_common_cnt = counter.most_common(1)[0]
    rarest_val, rarest_cnt = counter.most_common()[-1]

    return {
        "total": len(results),
        "avg": round(avg, 1),
        "most_common": most_common_val,
        "most_common_cnt": most_common_cnt,
        "rarest": rarest_val,
        "rarest_cnt": rarest_cnt
    }

# ─── Telegram Bot ────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def parse_dice(expression: str):
    """Парсит выражение вида NdM+K (например: 2d6+7, 3d20, d20, 1d6-1).
    Возвращает (num_dice, sides, modifier) или None при ошибке.
    Игнорирует все пробелы: '2d6 + 3' → '2d6+3'.
    """
    import re
    # Удаляем все пробелы
    expression = expression.replace(" ", "").lower()

    # Паттерн: [N]dM[+/-K]
    match = re.match(r'^(\d+)?d(\d+)([+-]\d+)?$', expression)
    if not match:
        return None

    num_dice = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if num_dice < 1 or num_dice > 100:
        return None
    if sides < 2 or sides > 1000:
        return None

    return (num_dice, sides, modifier)

@dp.message(Command("roll"))
async def cmd_roll(message: Message):
    """Обработка команды /roll [NdM+K] — бросок любого количества кубиков.
    Примеры: /roll, /roll 20, /roll 2d6, /roll 2d6+7, /roll 3d20-2
    """
    parts = message.text.strip().split()
    # Берём всё что после /roll и склеиваем (чтобы работали пробелы: "3d8 + 3")
    expression = " ".join(parts[1:]) if len(parts) > 1 else "d20"

    parsed = parse_dice(expression)
    if parsed is None:
        await message.answer(
            "Неверный формат. Примеры:\n"
            "/roll — d20\n"
            "/roll 2d6 — два d6\n"
            "/roll 2d6+7 — два d6 + 7"
        )
        return

    num_dice, sides, modifier = parsed
    player_name = message.from_user.full_name
    timestamp = datetime.utcnow().isoformat()

    # Бросаем кубики
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    raw_sum = sum(rolls)
    total = raw_sum + modifier

    # Сохраняем в БД (общую сумму)
    save_roll(player_name, total, timestamp)

    # Формируем детализацию
    rolls_str = " + ".join(str(r) for r in rolls)

    if modifier > 0:
        detail = f"({rolls_str}) + {modifier}"
    elif modifier < 0:
        detail = f"({rolls_str}) − {abs(modifier)}"
    else:
        detail = rolls_str if num_dice > 1 else str(rolls[0])

    # Криты (если один кубик и выпал максимум/минимум)
    crit = ""
    if num_dice == 1:
        if rolls[0] == sides:
            crit = " MAX!"
        elif rolls[0] == 1:
            crit = " MIN!"

    # Отправляем в Telegram
    dice_notation = f"{num_dice}d{sides}"
    if modifier > 0:
        dice_notation += f"+{modifier}"
    elif modifier < 0:
        dice_notation += str(modifier)

    await message.answer(
        f"🎲 {player_name} бросил {dice_notation}: {detail} = **{total}**{crit}",
        parse_mode="Markdown"
    )

    # Рассылаем на WebSocket
    await manager.broadcast({
        "player_name": player_name,
        "result": total,
        "dice_notation": dice_notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "timestamp": timestamp
    })

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение с кнопкой Web App."""
    try:
        user = message.from_user
        name = user.full_name or user.first_name or "Игрок"

        text = (
            f"Привет, {name}!\n\n"
            "DiceRoll Sync — бросай кубики!\n\n"
            "Команды:\n"
            "/roll — бросить d20\n"
            "/roll 2d6 — два d6\n"
            "/roll 2d6+7 — два d6 + 7\n"
            "/roll 3d20-2 — три d20 − 2\n"
            "/history — последние 10 бросков\n"
            "/history 20 — последние 20 бросков\n\n"
            "Статистика и история бросков — на панели Мастера."
        )

        # Web App кнопка — только если HTTPS URL
        if WEBAPP_URL and WEBAPP_URL.startswith("https://"):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎲 Бросить кубики", web_app=WebAppInfo(url=WEBAPP_URL))]
            ])
            await message.answer(text, reply_markup=keyboard)
        else:
            await message.answer(text)

        with open("bot.log", "a", encoding="utf-8") as f:
            f.write(f"[START OK] {name}\n")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open("bot.log", "a", encoding="utf-8") as f:
            f.write(f"[START ERROR] {e}\n{tb}\n")
        await message.answer("Привет! Используй /roll для броска.")

@dp.message(Command("history"))
async def cmd_history(message: Message):
    """Показать историю бросков."""
    parts = message.text.strip().split()
    limit = 10

    if len(parts) > 1:
        try:
            limit = int(parts[1])
            if limit < 1 or limit > 50:
                await message.answer("Покажи от 1 до 50 записей. Пример: /history 20")
                return
        except ValueError:
            await message.answer("Укажи число. Пример: /history 20")
            return

    rows = get_history(limit)

    if not rows:
        await message.answer("История пуста. Сделай первый бросок: /roll")
        return

    # Формируем сообщение
    lines = []
    for i, row in enumerate(reversed(rows), 1):
        time_short = row["timestamp"][11:16]  # HH:MM
        lines.append(f"{i}. {row['player_name']} → {row['result']} ({time_short})")

    text = f"📜 Последние {len(rows)} бросков:\n" + "\n".join(lines)

    # Добавляем общую статистику
    stats = get_stats()
    if stats:
        text += (
            f"\n\n📊 Статистика (всего {stats['total']} бросков):"
            f"\nСреднее: {stats['avg']}"
            f"\nЧаще всего: {stats['most_common']} ({stats['most_common_cnt']} раз)"
            f"\nРеже всего: {stats['rarest']} ({stats['rarest_cnt']} раз)"
        )

    await message.answer(text)

async def start_bot_polling():
    """Запуск бота в фоновом режиме."""
    try:
        print("[BOT] Connecting to Telegram...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"[BOT] Error: {e}")

# ─── FastAPI приложение ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте и очистка при остановке."""
    init_db()
    print("[OK] Database initialized")
    # Запускаем бота в фоне
    bot_task = asyncio.create_task(start_bot_polling())
    print("[OK] Telegram bot started")
    yield
    # Останавливаем бота
    bot_task.cancel()
    try:
        await bot.session.close()
    except Exception:
        pass

app = FastAPI(title="DiceRoll Sync", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """Отдать HTML-страницу Мастера."""
    with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/app", response_class=HTMLResponse)
async def get_webapp():
    """Отдать HTML-страницу Telegram Web App."""
    with open("webapp.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/roll")
async def api_roll(request: Request):
    """API endpoint для Web App — бросок кубиков."""
    body = await request.json()
    player_name = body.get("player_name", "Игрок")
    expression = body.get("expression", "d20")

    parsed = parse_dice(expression)
    if parsed is None:
        return {"error": "Неверный формат"}

    num_dice, sides, modifier = parsed
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    timestamp = datetime.utcnow().isoformat()

    save_roll(player_name, total, timestamp)

    rolls_str = " + ".join(str(r) for r in rolls)
    if modifier > 0:
        detail = f"({rolls_str}) + {modifier}"
    elif modifier < 0:
        detail = f"({rolls_str}) − {abs(modifier)}"
    else:
        detail = rolls_str if num_dice > 1 else str(rolls[0])

    dice_notation = f"{num_dice}d{sides}"
    if modifier > 0:
        dice_notation += f"+{modifier}"
    elif modifier < 0:
        dice_notation += str(modifier)

    # Рассылаем на WebSocket
    await manager.broadcast({
        "player_name": player_name,
        "result": total,
        "dice_notation": dice_notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "timestamp": timestamp
    })

    return {
        "dice_notation": dice_notation,
        "rolls": rolls,
        "detail": detail,
        "total": total
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для подключения Мастера."""
    await manager.connect(websocket)
    print(f"[WS] Master connected. Active: {len(manager.active_connections)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"[WS] Master disconnected. Active: {len(manager.active_connections)}")

# ─── Запуск ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("[*] Starting DiceRoll Sync on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
