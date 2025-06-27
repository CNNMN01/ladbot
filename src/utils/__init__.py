"""
Utility functions and helpers for Ladbot
"""

from .decorators import *
from .pagination import *
from .embeds import *
from .validators import *
from .helpers import *
from .constants import *
from .cog_loader import *

# Global variables for backward compatibility
db = None
settings = {}
embed_color = 0x00ff00
options = {}
option_names = []
icons = {}
emojis = {}
embeds = {}
command_disabled = None

__all__ = [
    'admin_required',
    'guild_setting_enabled',
    'typing_context',
    'PaginatedEmbed',
    'ListPaginator',
    'menu',
    'menus',
    'EmbedBuilder',
    'validate_boolean_input',
    'validate_integer_input',
    'chunks',
    'wait_for_response',
    'format_seconds',
    'CogLoader',
    'Colors',
    'Limits',
    'Emojis'
]