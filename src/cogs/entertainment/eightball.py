"""
Magic 8-Ball command
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import random
import asyncio
from utils.decorators import guild_setting_enabled, typing_context


class EightBall(commands.Cog):
    """Magic 8-Ball fortune telling"""

    def __init__(self, bot):
        self.bot = bot
        self._responses = None

    @property
    def responses(self):
        """Lazy load 8-ball responses"""
        if self._responses is None:
            try:
                response_data = self.bot.data_manager.get_json("8ball")
                self._responses = [discord.Embed.from_dict(resp) for resp in response_data]
            except:
                # Fallback responses
                self._responses = [
                    discord.Embed(description="🎱 It is certain", color=0x00ff00),
                    discord.Embed(description="🎱 Reply hazy, try again", color=0xffaa00),
                    discord.Embed(description="🎱 Don't count on it", color=0xff0000),
                ]
        return self._responses

    @commands.command(name="8ball", aliases=["eightball", "magic8ball"])
    @guild_setting_enabled("cmd_8ball")
    @typing_context()
    async def eight_ball(self, ctx, *, question: str = None):
        """Ask the Magic 8-Ball a question

        Usage: l.8ball <your question>
        """
        if not question:
            await ctx.send("🎱 You need to ask a question for the Magic 8-Ball!")
            return

        # Add dramatic effect
        await ctx.send("🎱 **Consulting the mystical 8-Ball...**")
        await asyncio.sleep(2)

        response_embed = random.choice(self.responses)
        await ctx.send(embed=response_embed)


async def setup(bot):
    await bot.add_cog(EightBall(bot))