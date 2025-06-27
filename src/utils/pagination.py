"""
Enhanced pagination system for Ladbot
Modernized version of the old menu system
"""

import discord
from discord.ext import commands
import asyncio
from typing import List, Callable, Optional, Union, Dict, Any


class PaginatedEmbed:
    """Modern pagination system for embeds"""

    def __init__(self, ctx: commands.Context, embeds: List[discord.Embed], timeout: int = 60):
        self.ctx = ctx
        self.embeds = embeds
        self.timeout = timeout
        self.current_page = 0
        self.message: Optional[discord.Message] = None

        # Emojis for pagination
        self.emojis = {
            "first": "⏮️",
            "previous": "◀️",
            "next": "▶️",
            "last": "⏭️",
            "stop": "⏹️"
        }

    async def start(self) -> None:
        """Start the pagination"""
        if not self.embeds:
            return

        # Add footer with page numbers
        self._update_footer()

        # Send initial message
        self.message = await self.ctx.send(embed=self.embeds[self.current_page])

        # Add reactions if more than one page
        if len(self.embeds) > 1:
            for emoji in self.emojis.values():
                await self.message.add_reaction(emoji)

            # Start listening for reactions
            await self._listen_for_reactions()

    def _update_footer(self) -> None:
        """Update footer with page information"""
        for i, embed in enumerate(self.embeds):
            if embed.footer.text:
                embed.set_footer(text=f"Page {i + 1}/{len(self.embeds)} • {embed.footer.text}")
            else:
                embed.set_footer(text=f"Page {i + 1}/{len(self.embeds)}")

    async def _listen_for_reactions(self) -> None:
        """Listen for reaction events"""

        def check(reaction, user):
            return (
                    reaction.message.id == self.message.id and
                    user == self.ctx.author and
                    str(reaction.emoji) in self.emojis.values()
            )

        while True:
            try:
                reaction, user = await self.ctx.bot.wait_for(
                    'reaction_add', timeout=self.timeout, check=check
                )

                emoji = str(reaction.emoji)

                if emoji == self.emojis["first"]:
                    self.current_page = 0
                elif emoji == self.emojis["previous"]:
                    self.current_page = max(0, self.current_page - 1)
                elif emoji == self.emojis["next"]:
                    self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
                elif emoji == self.emojis["last"]:
                    self.current_page = len(self.embeds) - 1
                elif emoji == self.emojis["stop"]:
                    break

                # Update the message
                await self.message.edit(embed=self.embeds[self.current_page])

                # Remove user's reaction
                try:
                    await self.message.remove_reaction(reaction, user)
                except discord.Forbidden:
                    pass

            except asyncio.TimeoutError:
                break

        # Clean up reactions
        try:
            await self.message.clear_reactions()
        except discord.Forbidden:
            pass


class ListPaginator:
    """Paginate a list of items into embeds"""

    def __init__(self, items: List[Any], items_per_page: int = 10, title: str = "Items"):
        self.items = items
        self.items_per_page = items_per_page
        self.title = title

    def create_embeds(self, color: int = 0x00ff00) -> List[discord.Embed]:
        """Create embeds from the items"""
        embeds = []

        for i in range(0, len(self.items), self.items_per_page):
            chunk = self.items[i:i + self.items_per_page]

            embed = discord.Embed(title=self.title, color=color)

            description = ""
            for j, item in enumerate(chunk, start=i + 1):
                if isinstance(item, dict) and "name" in item and "value" in item:
                    embed.add_field(
                        name=item["name"],
                        value=item["value"],
                        inline=item.get("inline", False)
                    )
                else:
                    description += f"{j}. {str(item)}\n"

            if description:
                embed.description = description

            embeds.append(embed)

        return embeds


# Backward compatibility functions
async def menu(client, ctx, generator):
    """Legacy menu function for backward compatibility"""
    embeds = []
    gen = generator(ctx.author)

    try:
        total_pages = await gen.__anext__()
        for _ in range(total_pages):
            embed = await gen.__anext__()
            embeds.append(embed)
    except StopAsyncIteration:
        pass
    finally:
        await gen.aclose()

    if embeds:
        paginator = PaginatedEmbed(ctx, embeds)
        await paginator.start()


class menus:
    """Legacy menus class for backward compatibility"""

    @staticmethod
    async def list(client, ctx, generator):
        await menu(client, ctx, generator)

    @staticmethod
    async def reload(client, ctx, generator):
        await menu(client, ctx, generator)