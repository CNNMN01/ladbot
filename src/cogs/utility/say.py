"""
Say command - make the bot repeat text
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
from utils.decorators import guild_setting_enabled, admin_required
from utils.validators import sanitize_input


class Say(commands.Cog):
    """Text repeating command"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @guild_setting_enabled("say")
    async def say(self, ctx, *, text: str = None):
        """Make the bot say something

        Usage: l.say <message>
        """
        if not text:
            await ctx.send(f"Usage: `{self.bot.command_prefix}say <message>`")
            return

        # Sanitize input to prevent abuse
        clean_text = sanitize_input(text, max_length=1900)

        # Check for mentions and only allow if admin
        if "@" in clean_text and not any(role.permissions.administrator for role in ctx.author.roles):
            clean_text = clean_text.replace("@", "@\u200b")  # Add zero-width space

        try:
            # Delete the original command message if possible
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        await ctx.send(clean_text)


async def setup(bot):
    await bot.add_cog(Say(bot))