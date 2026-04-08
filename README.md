# 🎲 DiceRoll Sync

A real-time dice rolling system with a Telegram bot, Web App, and live Master dashboard — built for tabletop RPG sessions.

## Demo

**Master Dashboard** — real-time roll feed with statistics:

![Master Dashboard](https://via.placeholder.com/800x400/1a1a2e/ffffff?text=Master+Dashboard+—+Real-time+Roll+Feed)

**Telegram Web App** — in-app dice roller:

![Web App](https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Telegram+Web+App+—+Dice+Roller)

## Product Context

### End Users

- **Tabletop RPG players** (D&D, Pathfinder, etc.) who need to roll dice during sessions
- **Game Masters** who want to track all player rolls in real time on a shared screen
- **Remote gaming groups** playing online who need a shared dice rolling tool

### Problem

During tabletop sessions, players roll dice physically or use separate apps. The Game Master has no central view of all rolls, and remote players struggle to share results quickly. Existing solutions are either too complex or lack real-time sync.

### Solution

DiceRoll Sync provides a single Telegram bot that all players can use to roll dice. Results instantly appear on the Master's web dashboard — no page reload, no extra apps. Players can also use the built-in Telegram Web App for a visual dice roller.

## Features

### Implemented

- [x] Telegram bot with `/roll` command (flexible notation: `d20`, `2d6`, `2d6+7`, `3d20 - 2`)
- [x] Telegram Web App with quick-roll buttons (d4, d6, d8, d10, d12, d20, d100) and custom input
- [x] Master Dashboard with real-time WebSocket roll feed
- [x] Live statistics: average, most common, rarest roll
- [x] Roll history via `/history` command
- [x] SQLite persistence
- [x] Docker deployment
- [x] Critical roll highlighting (nat 20 / nat 1)

### Not Yet Implemented

- [ ] Multi-table support (separate rooms)
- [ ] Roll macros (e.g., `/attack`, `/save`)
- [ ] Player authentication
- [ ] Roll history export (CSV/PDF)
- [ ] Sound effects on critical rolls
- [ ] Mobile-responsive Master Dashboard improvements

## Usage

### Telegram Bot

| Command | Description |
|---|---|
| `/start` | Welcome message + command list |
| `/roll` | Roll d20 |
| `/roll 2d6` | Roll two d6 |
| `/roll 2d6+7` | Roll two d6 + 7 (spaces allowed) |
| `/roll 3d20-2` | Roll three d20 − 2 |
| `/history` | Last 10 rolls |
| `/history 20` | Last 20 rolls |

### Web App

Open the bot → tap **🎲 Бросить кубики** → use quick buttons or type custom notation.

### Master Dashboard

Open `http://<host>:8000/` in a browser. All rolls appear in real time via WebSocket.

## Deployment

### Target Environment

- **OS:** Ubuntu 24.04 LTS (or any Linux with Docker support)
- **RAM:** 256 MB minimum
- **Disk:** 1 GB minimum (for Docker + SQLite)

### Prerequisites

The following must be installed on the VM:

- **Docker** (24.0+)
- **Docker Compose** (2.20+, included with Docker Desktop)
- **Git**
- A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)

### Step-by-Step Instructions

#### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Re-login for group changes to take effect
```

#### 2. Clone the Repository

```bash
git clone https://github.com/ProPupok/se-toolkit-hackathon.git ~/diceroll-sync
cd ~/diceroll-sync
```

#### 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

Set your bot token:

```
BOT_TOKEN=your_token_from_botfather
WEBAPP_URL=
DB_PATH=dice_rolls.db
FRONTEND_PATH=index.html
```

#### 4. Start the Service

```bash
docker compose up --build -d
```

#### 5. Verify

```bash
docker compose logs -f
```

Open `http://<VM_IP>:8000/` — the Master Dashboard should load.

#### 6. (Optional) Enable HTTPS for Web App

Telegram Web App buttons require HTTPS. Use Caddy for automatic TLS:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

Configure Caddy (`/etc/caddy/Caddyfile`):

```
yourdomain.com {
    reverse_proxy localhost:8000
}
```

```bash
sudo systemctl restart caddy
```

Update `.env`:

```
WEBAPP_URL=https://yourdomain.com/app
```

Restart:

```bash
docker compose down && docker compose up -d
```

### Useful Commands

```bash
docker compose logs -f      # View logs in real time
docker compose restart      # Restart the service
docker compose down         # Stop and remove containers
docker compose ps           # Check container status
```

## Project Structure

```
├── main.py           # FastAPI + Telegram bot + WebSocket + SQLite
├── index.html        # Master Dashboard (real-time roll feed)
├── webapp.html       # Telegram Web App (dice roller)
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container image definition
├── docker-compose.yml # Multi-container orchestration
├── .env.example      # Environment variables template
├── .gitignore        # Git ignore rules (secrets excluded)
└── LICENSE           # MIT License
```

## Tech Stack

- **Backend:** FastAPI + uvicorn + websockets
- **Bot:** aiogram 3.x
- **Database:** SQLite
- **Frontend:** HTML + JavaScript + Bootstrap 5 (CDN)
- **Deploy:** Docker + Docker Compose

## License

This project is licensed under the [MIT License](LICENSE).
