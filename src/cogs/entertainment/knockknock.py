"""
Interactive knock-knock jokes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import random
import asyncio
from utils.decorators import guild_setting_enabled


class KnockKnock(commands.Cog):
    """Interactive knock-knock jokes"""

    def __init__(self, bot):
        self.bot = bot

        # Collection of knock-knock jokes
        self.jokes = [
            ("Lettuce", "Lettuce in, it's cold out here!"),
            ("Cow says", "No, cow says moo!"),
            ("Interrupting cow", "Moo!"),
            ("Boo", "Don't cry, it's just a joke!"),
            ("Tank", "You're welcome!"),
            ("Cargo", "Car go beep beep, vroom vroom!"),
            ("Orange", "Orange you glad I didn't say banana?"),
            ("Broken pencil", "Never mind, it's pointless!"),
            ("Dishes", "Dishes a very bad joke!"),
            ("Nobel", "Nobel, that's why I knocked!"),
            ("Harry", "Harry up and answer the door!"),
            ("Honeydew", "Honeydew you want to hear another joke?"),
            ("Ice cream", "Ice cream every time I see a ghost!"),
            ("Wooden shoe", "Wooden shoe like to hear another joke?"),
            ("Alpaca", "Alpaca the suitcase, you load up the car!"),
        ]

    @commands.command(aliases=["knock"])
    @guild_setting_enabled("knockknock")
    async def knockknock(self, ctx):
        """Start an interactive knock-knock joke"""
        try:
            # Select random joke
            setup, punchline = random.choice(self.jokes)

            # Start the joke
            embed = discord.Embed(
                title="🚪 Knock Knock!",
                description="**Knock knock!**",
                color=0x00ff00
            )
            embed.set_footer(text="Type 'who's there?' to continue...")

            await ctx.send(embed=embed)

            # Wait for "who's there?" response
            def check(message):
                return (
                        message.author == ctx.author and
                        message.channel == ctx.channel and
                        "who" in message.content.lower() and
                        "there" in message.content.lower()
                )

            try:
                await self.bot.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    description="⏰ Knock knock joke timed out! Type 'who's there?' next time.",
                    color=0xff0000
                )
                await ctx.send(embed=timeout_embed)
                return

            # Send the setup
            embed = discord.Embed(
                title="🚪 Knock Knock!",
                description=f"**{setup}**",
                color=0x00ff00
            )
            embed.set_footer(text=f"Type '{setup.lower()} who?' to continue...")

            await ctx.send(embed=embed)

            # Wait for the "setup who?" response
            def check2(message):
                return (
                        message.author == ctx.author and
                        message.channel == ctx.channel and
                        setup.lower() in message.content.lower() and
                        "who" in message.content.lower()
                )

            try:
                await self.bot.wait_for('message', timeout=30.0, check=check2)
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    description=f"⏰ Knock knock joke timed out! Type '{setup.lower()} who?' next time.",
                    color=0xff0000
                )
                await ctx.send(embed=timeout_embed)
                return

            # Deliver the punchline
            embed = discord.Embed(
                title="🎭 Punchline!",
                description=f"**{punchline}**",
                color=0xFFD700
            )

            # Add reaction emojis for feedback
            punchline_msg = await ctx.send(embed=embed)
            await punchline_msg.add_reaction("😂")
            await punchline_msg.add_reaction("👏")
            await punchline_msg.add_reaction("🙄")

        except Exception as e:
            await ctx.send(f"❌ Error with knock-knock joke: {e}")

    @commands.command()
    @guild_setting_enabled("knockknock")
    async def quickknock(self, ctx):
        """Get a quick knock-knock joke without interaction"""
        try:
            setup, punchline = random.choice(self.jokes)

            embed = discord.Embed(
                title="🚪 Quick Knock-Knock Joke",
                color=0x00ff00
            )

            joke_text = f"**Knock knock!**\n*Who's there?*\n**{setup}**\n*{setup} who?*\n**{punchline}**"
            embed.description = joke_text

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Try l.knockknock for interactive version!",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error getting knock-knock joke: {e}")


async def setup(bot):
    await bot.add_cog(KnockKnock(bot))