# WebKong Discord Bot

A tiny Discord presence bot for the Kong League server. It polls the public
[WebKong API](https://greentie.dev/webkong/api-docs.html) and rotates a live
status line in the member-list sidebar:

- `Watching 3 players online` (or `No one playing WebKong` when nobody is on)
- `Watching Blueberry 29,600 (3-1)` when someone is broadcasting a run
- `Playing Co-op 5-2: 145,000` when a co-op run is live, then rotates back out

Each frame shows for `ROTATE_INTERVAL_MS` (default 45s). Frames appear and
disappear based on real activity, so the sidebar reflects what is actually
happening right now.

## Files

- `webkong.py` - API client and frame builder (no Discord knowledge).
- `bot.py` - Discord client, rotation loop, and health endpoint.

## One-time Discord setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a New Application.
2. Open the **Bot** tab, click **Reset Token**, and copy the token. This is your `DISCORD_TOKEN`.
3. No privileged intents are required (setting your own presence needs none).
4. Open **OAuth2 > URL Generator**, tick the `bot` scope, and use the generated URL to invite the bot. Someone with **Manage Server** on Kong League has to approve it.

## Run locally

Requires Python 3.10+. Use `python3` explicitly for the venv setup; on some
machines a bare `python` still resolves to Python 2, which fails with a
`SyntaxError` on the type annotations.

```bash
# One-time setup.
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # then paste your token into .env

# Every session: activate the venv AND load .env into the shell.
source .venv/bin/activate
set -a && source .env && set +a
python bot.py
```

The bot reads plain environment variables and does not parse `.env` itself,
so the `set -a && source .env && set +a` step is required every new shell
session (or use direnv to automate it). Skipping it fails at boot with
`KeyError: 'DISCORD_TOKEN'`.

Within a rotation interval the bot should show a status under its name in the
sidebar.

## Deploy on Coolify

1. Push this folder to a Git repo Coolify can reach.
2. New Resource > Application, pick the repo, build pack **Dockerfile**.
3. Set environment variables: `DISCORD_TOKEN` (required); optionally
   `ROTATE_INTERVAL_MS`, `WEBKONG_BASE`, `PORT`.
4. The container exposes port `3000` with a `/health` route for the healthcheck.
   This is only for Coolify; the bot needs no public domain, so you can leave it
   without a mapped domain.

## Environment variables

| Variable             | Required | Default                        | Purpose                                   |
| -------------------- | -------- | ------------------------------ | ----------------------------------------- |
| `DISCORD_TOKEN`      | yes      | -                              | Bot token from the Developer Portal.      |
| `WEBKONG_BASE`       | no       | `https://greentie.dev/webkong` | API base URL (override for local dev).    |
| `ROTATE_INTERVAL_MS` | no       | `45000`                        | Milliseconds each frame is shown.         |
| `PORT`               | no       | `3000`                         | Port for the Coolify healthcheck server.  |
