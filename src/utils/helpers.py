"""
General helper functions
"""

import asyncio
import discord
from discord.ext import commands
from typing import List, TypeVar, Optional, Callable

T = TypeVar('T')


def chunks(lst: List[T], n: int) -> List[List[T]]:
    """Split a list into chunks of size n"""
    return [lst[i * n:(i + 1) * n] for i in range((len(lst) + n - 1) // n)]


async def wait_for_response(
        client: commands.Bot,
        channel: discord.TextChannel,
        user: discord.User,
        timeout: Optional[int] = None
) -> Optional[discord.Message]:
    """Wait for a message response from a specific user in a channel"""
    try:
        message = await client.wait_for(
            "message",
            timeout=timeout,
            check=lambda msg: msg.channel == channel and msg.author == user
        )
        return message
    except asyncio.TimeoutError:
        return None


def format_seconds(seconds: int) -> str:
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


def safe_get_attribute(obj: object, attr_path: str, default=None):
    """Safely get nested attribute from object"""
    attrs = attr_path.split('.')
    current = obj

    try:
        for attr in attrs:
            current = getattr(current, attr)
        return current
    except AttributeError:
        return default


def truncate_text(text: str, max_length: int = 2000, suffix: str = "...") -> str:
    """Truncate text to fit within Discord limits"""
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """Escape markdown characters in text"""
    escape_chars = ['*', '_', '~', '`', '\\', '|']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text