"""
Laugh and reaction commands
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import random
from utils.decorators import guild_setting_enabled


class Laugh(commands.Cog):
    """Laugh and reaction commands"""

    def __init__(self, bot):
        self.bot = bot

        self.laugh_variations = [
            "😂", "🤣", "😆", "😄", "😃", "😁", "😊",
            "HAHAHA!", "LOL!", "LMAO!", "That's hilarious!",
            "I can't stop laughing!", "Good one!", "😂😂😂",
            "Hehe!", "Ahaha!", "Bahaha!", "Muahahaha!",
            "That cracked me up!", "I'm dying! 😂"
        ]

        self.reaction_gifs = [
            "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif",
            "https://media.giphy.com/media/l0HlvtIPzPdt2usKs/giphy.gif",
            "https://media.giphy.com/media/8fen5LSZcHQ5O/giphy.gif"
        ]

    @commands.command(aliases=["lol", "haha"])
    @guild_setting_enabled("laugh")
    async def laugh(self, ctx):
        """Make the bot laugh"""
        laugh_text = random.choice(self.laugh_variations)

        embed = discord.Embed(
            description=laugh_text,
            color=0xFFD700
        )

        # Add random GIF occasionally
        if random.random() < 0.3:  # 30% chance
            gif_url = random.choice(self.reaction_gifs)
            embed.set_image(url=gif_url)

        await ctx.send(embed=embed)

    @commands.command()
    @guild_setting_enabled("laugh")
    async def clap(self, ctx):
        """Clapping reaction"""
        clap_variations = ["👏", "👏👏👏", "Bravo!", "Well done!", "Amazing!", "*clap clap clap*"]
        response = random.choice(clap_variations)

        await ctx.send(response)

    @commands.command()
    @guild_setting_enabled("laugh")
    async def cheer(self, ctx):
        """Cheering reaction"""
        cheer_variations = [
            "🎉 Hooray!", "🎊 Woohoo!", "🥳 Awesome!", "🎈 Yay!",
            "🎆 Fantastic!", "✨ Amazing!", "🌟 Brilliant!"
        ]
        response = random.choice(cheer_variations)

        embed = discord.Embed(
            description=response,
            color=0x00ff00
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Laugh(bot))