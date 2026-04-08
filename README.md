# 🎲 DiceRoll Sync

Система бросков кубиков в реальном времени с Telegram-ботом и веб-панелью Мастера.

## Возможности

- **Telegram-бот** — бросай кубики командой `/roll`
- **Гибкий формат** — `d20`, `2d6`, `2d6+7`, `3d20 - 2` (пробелы не важны)
- **Web App** — бросай кубики прямо в Telegram через встроенное приложение
- **Панель Мастера** — веб-страница с лентой бросков в реальном времени (WebSocket)
- **Статистика** — среднее, чаще/реже всего выпадающее значение
- **История** — команда `/history` в боте

## Быстрый старт

### 1. Клонирование

```bash
git clone <your-repo-url>
cd se-toolkit-hackathon
```

### 2. Настройка

```bash
cp .env.example .env
# Отредактируй .env — вставь токен бота от @BotFather
```

### 3. Запуск (локально)

```bash
pip install -r requirements.txt
python main.py
```

Открой `http://localhost:8000` — панель Мастера.

### 4. Запуск (Docker)

```bash
docker compose up --build -d
```

## Деплой на VM

1. Скопируй файлы на сервер
2. Настрой HTTPS (Caddy / Nginx + Let's Encrypt)
3. В `.env` укажи `WEBAPP_URL=https://yourdomain.com/app`
4. `docker compose up --build -d`

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие + список команд |
| `/roll` | Бросить d20 |
| `/roll 2d6` | Два d6 |
| `/roll 2d6+7` | Два d6 + 7 |
| `/roll 3d20-2` | Три d20 − 2 |
| `/history` | Последние 10 бросков |
| `/history 20` | Последние 20 бросков |

## Структура проекта

```
├── main.py           # FastAPI + бот + WebSocket + SQLite
├── index.html        # Панель Мастера
├── webapp.html       # Telegram Web App
├── requirements.txt  # Python зависимости
├── Dockerfile
├── docker-compose.yml
├── .env.example      # Шаблон переменных окружения
└── .gitignore
```

## Стек

- **Backend:** FastAPI + uvicorn + websockets
- **Bot:** aiogram 3.x
- **DB:** SQLite
- **Frontend:** HTML + JS + Bootstrap (CDN)
- **Deploy:** Docker
