# WebKong Discord Bot

Rotates live [WebKong](https://greentie.dev/webkong) activity through a Discord
presence line:

- `Watching Blueberry 29,600 (3-1)` - someone is broadcasting a run
- `Playing Co-op 5-2: 145,000` - a co-op run is live
- `Watching 3 players in the lobby` - people online, nothing to spectate yet

Green dot: there's a game to watch or join. Yellow: there isn't.

## Run locally

```bash
# One-time setup.
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # paste your bot token in

# Every session (.env is not read automatically).
source .venv/bin/activate
set -a && source .env && set +a
python bot.py
```

## Deploy

Hosted on Railway. Pushes to `main` auto-deploy; `DISCORD_TOKEN` is set in the
service's Variables tab. No public domain or healthcheck needed.

## Environment variables

| Variable             | Default                        | Purpose                          |
| -------------------- | ------------------------------ | -------------------------------- |
| `DISCORD_TOKEN`      | (required)                     | Bot token from the Dev Portal.   |
| `WEBKONG_BASE`       | `https://greentie.dev/webkong` | API base URL.                    |
| `ROTATE_INTERVAL_MS` | `45000`                        | Time each frame is shown.        |
| `PORT`               | `3000`                         | Optional healthcheck server.     |
