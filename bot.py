"""Discord presence bot that rotates live WebKong activity in the sidebar.

The bot holds no state beyond a frame cursor: every tick it refetches live
WebKong data, rebuilds the list of relevant frames, and shows the next one.
"""

from __future__ import annotations

import os

import aiohttp
import discord
from aiohttp import web
from discord.ext import tasks

from webkong import UNAVAILABLE_FRAME, Frame, build_frames

# How long each status frame stays on screen before rotating. Discord's gateway
# tolerates ~5 presence updates per minute, but clients cache presence and can
# lag on fast flips, so a slower cadence reads more reliably than it costs.
ROTATE_SECONDS = int(os.environ.get("ROTATE_INTERVAL_MS", "45000")) / 1000

# Some hosts want a port to health-check; the bot needs no inbound traffic itself.
HEALTH_PORT = int(os.environ.get("PORT", "3000"))

# Failing loud at boot beats a bot that silently never connects.
TOKEN = os.environ["DISCORD_TOKEN"]

_ACTIVITY_TYPES = {
    "watching": discord.ActivityType.watching,
    "playing": discord.ActivityType.playing,
}

# Ride out this many consecutive failed polls on the last known frames before
# admitting "status unavailable", so one blip never flickers error text.
_MAX_STALE_TICKS = 3


class WebKongBot(discord.Client):
    def __init__(self) -> None:
        # No privileged intents are needed just to set our own presence.
        super().__init__(intents=discord.Intents.none())
        self._session: aiohttp.ClientSession | None = None
        self._frames: list[Frame] = []
        self._cursor = 0
        self._failed_ticks = 0

    async def setup_hook(self) -> None:
        # One shared session for the process lifetime, reused across polls.
        self._session = aiohttp.ClientSession()
        await _start_health_server()
        self.rotate.start()

    async def close(self) -> None:
        self.rotate.cancel()
        if self._session is not None:
            await self._session.close()
        await super().close()

    @tasks.loop(seconds=ROTATE_SECONDS)
    async def rotate(self) -> None:
        assert self._session is not None
        # Refetch every tick so the shown frame reflects near-live state.
        fresh = await build_frames(self._session)
        if fresh is not None:
            self._frames = fresh
            self._failed_ticks = 0
        else:
            self._failed_ticks += 1
            if self._failed_ticks >= _MAX_STALE_TICKS or not self._frames:
                self._frames = [UNAVAILABLE_FRAME]
        # Wrap the cursor to the (possibly changed) frame count each time.
        frame = self._frames[self._cursor % len(self._frames)]
        self._cursor = (self._cursor + 1) % len(self._frames)
        await self.change_presence(
            status=discord.Status.idle if frame.idle else discord.Status.online,
            activity=discord.Activity(
                type=_ACTIVITY_TYPES.get(frame.kind, discord.ActivityType.watching),
                name=frame.text,
            ),
        )

    @rotate.before_loop
    async def _before_rotate(self) -> None:
        # Presence calls fail until the gateway is ready, so wait for login first.
        await self.wait_until_ready()


async def _start_health_server() -> None:
    """Serve a 200 on /health for hosts whose healthchecks need an HTTP target."""

    async def handle(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app = web.Application()
    app.add_routes([web.get("/", handle), web.get("/health", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=HEALTH_PORT)
    await site.start()
    print(f"Health endpoint listening on :{HEALTH_PORT}")


if __name__ == "__main__":
    WebKongBot().run(TOKEN)
