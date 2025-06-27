"""
Constants used throughout Ladbot
"""

from enum import Enum


class Colors:
    """Color constants for embeds"""
    PRIMARY = 0x00ff00
    SUCCESS = 0x00ff00
    ERROR = 0xff0000
    WARNING = 0xffaa00
    INFO = 0x0099ff
    SECONDARY = 0x6c757d


class Limits:
    """Discord API limits"""
    EMBED_TITLE_MAX = 256
    EMBED_DESCRIPTION_MAX = 4096
    EMBED_FIELD_NAME_MAX = 256
    EMBED_FIELD_VALUE_MAX = 1024
    EMBED_FOOTER_MAX = 2048
    EMBED_AUTHOR_NAME_MAX = 256
    EMBED_TOTAL_MAX = 6000
    MESSAGE_MAX = 2000


class Emojis:
    """Common emoji constants"""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"

    # Pagination
    FIRST = "⏮️"
    PREVIOUS = "◀️"
    NEXT = "▶️"
    LAST = "⏭️"
    STOP = "⏹️"


class DefaultSettings:
    """Default bot settings"""
    PREFIX = "l."
    TIMEOUT = 60
    ITEMS_PER_PAGE = 10
    MAX_SEARCH_RESULTS = 100