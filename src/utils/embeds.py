"""
Embed utilities and templates for Ladbot
"""

import discord
from typing import Dict, Any, Optional, Union


class EmbedBuilder:
    """Helper class for building embeds with consistent styling"""

    def __init__(self, color: int = 0x00ff00):
        self.color = color

    def create_basic_embed(
            self,
            title: Optional[str] = None,
            description: Optional[str] = None,
            color: Optional[int] = None
    ) -> discord.Embed:
        """Create a basic embed with consistent styling"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or self.color
        )
        return embed

    def create_success_embed(self, message: str) -> discord.Embed:
        """Create a success embed"""
        return discord.Embed(
            description=f"✅ {message}",
            color=0x00ff00
        )

    def create_error_embed(self, message: str) -> discord.Embed:
        """Create an error embed"""
        return discord.Embed(
            description=f"❌ {message}",
            color=0xff0000
        )

    def create_warning_embed(self, message: str) -> discord.Embed:
        """Create a warning embed"""
        return discord.Embed(
            description=f"⚠️ {message}",
            color=0xffaa00
        )

    def create_info_embed(self, message: str) -> discord.Embed:
        """Create an info embed"""
        return discord.Embed(
            description=f"ℹ️ {message}",
            color=0x0099ff
        )


def create_embeds_from_dict(embed_data: Dict[str, Any]) -> Dict[str, discord.Embed]:
    """Convert dictionary of embed data to Discord embeds"""
    embeds = {}
    for key, data in embed_data.items():
        embeds[key] = discord.Embed.from_dict(data)
    return embeds