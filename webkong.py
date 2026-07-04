"""WebKong public API client and status-frame builder.

This module knows nothing about Discord; it just turns live WebKong state into
a list of short strings the bot can show. Keeping it separate makes the
rotation logic easy to read and test on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import aiohttp

# Overridable so the same image can point at local dev (127.0.0.1:9014).
BASE_URL = os.environ.get("WEBKONG_BASE", "https://greentie.dev/webkong").rstrip("/")

# A slow WebKong response should never wedge the rotation loop, so bound it.
_TIMEOUT = aiohttp.ClientTimeout(total=8)


@dataclass
class Frame:
    """One thing the bot can show. `kind` picks the verb Discord prefixes."""

    # One of: "watching", "playing". Mapped to a discord ActivityType in bot.py.
    kind: str
    text: str
    # Quiet frames get a yellow presence dot, so the dot color alone signals
    # whether anything is happening on WebKong.
    idle: bool = False


async def _get_json(session: aiohttp.ClientSession, path: str) -> dict | None:
    """Fetch and parse one endpoint, returning None on any failure.

    Returning None lets callers degrade gracefully instead of crashing the bot.
    """
    try:
        async with session.get(
            f"{BASE_URL}{path}",
            timeout=_TIMEOUT,
            headers={"accept": "application/json"},
        ) as response:
            if response.status != 200:
                print(f"WebKong {path} responded {response.status}")
                return None
            return await response.json()
    except Exception as error:  # Network, timeout, or bad JSON all degrade the same way.
        print(f"WebKong {path} request failed: {error}")
        return None


def _format_score(score: int) -> str:
    return f"{score:,}"


def _top_broadcast(broadcasts: list[dict]) -> dict | None:
    """Pick the highest-scoring broadcast so the featured run stays stable."""
    if not broadcasts:
        return None
    best = broadcasts[0]
    for broadcast in broadcasts:
        if broadcast.get("score", 0) > best.get("score", 0):
            best = broadcast
    return best


# Shown only after several consecutive failed polls; the bot rides out brief
# blips on its last known frames so the sidebar does not flicker error text.
UNAVAILABLE_FRAME = Frame("watching", "WebKong: status unavailable", idle=True)

# Discord truncates sidebar activity around 32 visible chars; clamping the name
# keeps the score (the interesting part) from being the piece that gets cut.
_MAX_NAME_LENGTH = 12


async def build_frames(session: aiohttp.ClientSession) -> list[Frame] | None:
    """Build the ordered frames that currently make sense, or None if the API
    is unreachable so the caller can decide how long to trust stale frames.

    The list shrinks and grows with real activity, which is what makes the
    sidebar rotation feel alive rather than canned.
    """
    online = await _get_json(session, "/api/v1/online-players")
    if online is None:
        return None

    frames: list[Frame] = []

    broadcast = _top_broadcast(online.get("singlePlayerBroadcasts", []))
    broadcast_frame: Frame | None = None
    if broadcast:
        name = str(broadcast.get("name") or "Someone")[:_MAX_NAME_LENGTH]
        score = _format_score(broadcast.get("score", 0))
        text = f"{name} {score}"
        # Only show the board when the API actually sent one; "(None-None)"
        # would read worse than no board at all.
        level, stage = broadcast.get("level"), broadcast.get("stage")
        if level is not None and stage is not None:
            text += f" ({level}-{stage})"
        broadcast_frame = Frame("watching", text)
        frames.append(broadcast_frame)

    count = online.get("count", 0)
    # A lone broadcaster's frame already implies someone is online, so skip the
    # redundant count frame and let the live score line hold the screen.
    if count > 0 and not (count == 1 and broadcast):
        noun = "player" if count == 1 else "players"
        frames.append(Frame("watching", f"{count} {noun} online"))
        # The live run is the story and the count is wallpaper: give the run a
        # second slot so it holds the screen for most of the cycle.
        if broadcast_frame:
            frames.append(broadcast_frame)

    # Only hit the co-op endpoint when a run is flagged active, to save a request.
    if online.get("coop", {}).get("active"):
        coop = await _get_json(session, "/api/v1/coop/players")
        frames.append(_coop_frame(coop))

    # True empty state: no count, no broadcast, no co-op. Checking `frames` rather
    # than `count` keeps this from contradicting a live broadcast frame when the
    # API's count doesn't include broadcasters.
    if not frames:
        frames.append(Frame("watching", "No one playing WebKong", idle=True))

    return frames


def _coop_frame(coop: dict | None) -> Frame:
    # The active flag can flip between calls; keep a sensible generic frame if so.
    if not coop or not coop.get("active"):
        return Frame("playing", "Co-op run in progress")
    label = coop.get("level", {}).get("label", "?")
    score = _format_score(coop.get("score", 0))
    return Frame("playing", f"Co-op {label}: {score}")
