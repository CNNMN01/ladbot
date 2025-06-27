"""
Random jokes and humor commands
"""

import sys


import discord
from discord.ext import commands
import aiohttp
import json
import random
from utils.decorators import guild_setting_enabled, typing_context


class Jokes(commands.Cog):
    """Random jokes and humor"""

    def __init__(self, bot):
        self.bot = bot

        # Fallback jokes if API is unavailable
        self.fallback_jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "I told my wife she was drawing her eyebrows too high. She looked surprised.",
            "Why don't programmers like nature? It has too many bugs.",
            "I'm reading a book about anti-gravity. It's impossible to put down!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "What do you call a fake noodle? An impasta!",
            "Why did the coffee file a police report? It got mugged!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a dinosaur that crashes his car? Tyrannosaurus Wrecks!"
        ]

    @commands.command(aliases=["joke"])
    @guild_setting_enabled("jokes")
    @typing_context()
    async def jokes(self, ctx, category: str = "any"):
        """Get a random joke

        Usage: l.jokes [category]
        Categories: programming, misc, dark, pun, spooky, christmas
        """
        try:
            # Try to get joke from API
            joke_text = await self._get_api_joke(category)

            if not joke_text:
                # Fallback to local jokes
                joke_text = random.choice(self.fallback_jokes)
                source = "Local Database"
            else:
                source = "JokeAPI"

            # Create embed
            embed = discord.Embed(
                title="😂 Random Joke",
                description=joke_text,
                color=0xFFD700
            )

            embed.add_field(
                name="Category",
                value=category.title() if category != "any" else "Random",
                inline=True
            )

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Source: {source}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            # Final fallback
            joke_text = random.choice(self.fallback_jokes)
            embed = discord.Embed(
                title="😂 Random Joke",
                description=joke_text,
                color=0xFFD700
            )
            await ctx.send(embed=embed)

    async def _get_api_joke(self, category):
        """Get joke from JokeAPI"""
        try:
            # JokeAPI URL
            url = "https://v2.jokeapi.dev/joke/Any"

            # Filter out potentially inappropriate content
            params = {
                "blacklistFlags": "nsfw,religious,political,racist,sexist,explicit",
                "type": "single"  # Only single-part jokes for simplicity
            }

            if category != "any":
                url = f"https://v2.jokeapi.dev/joke/{category}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get("error"):
                            return None

                        if data.get("type") == "single":
                            return data.get("joke")
                        elif data.get("type") == "twopart":
                            # Combine setup and delivery for two-part jokes
                            setup = data.get("setup", "")
                            delivery = data.get("delivery", "")
                            return f"{setup}\n\n{delivery}"

            return None

        except Exception:
            return None

    @commands.command()
    @guild_setting_enabled("jokes")
    async def dadjoke(self, ctx):
        """Get a dad joke"""
        try:
            # Dad joke API
            url = "https://icanhazdadjoke.com/"
            headers = {"Accept": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        joke_text = data.get("joke", "")
                    else:
                        joke_text = random.choice(self.fallback_jokes)

            embed = discord.Embed(
                title="👨 Dad Joke",
                description=joke_text,
                color=0x8B4513
            )

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Source: icanhazdadjoke.com",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception:
            # Fallback
            joke_text = random.choice(self.fallback_jokes)
            embed = discord.Embed(
                title="👨 Dad Joke",
                description=joke_text,
                color=0x8B4513
            )
            await ctx.send(embed=embed)

    @commands.command()
    @guild_setting_enabled("jokes")
    async def pun(self, ctx):
        """Get a random pun"""
        puns = [
            "I wondered why the ball kept getting bigger. Then it hit me.",
            "I'm reading a book about anti-gravity. It's impossible to put down!",
            "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
            "I used to hate facial hair, but then it grew on me.",
            "I decided to sell my vacuum cleaner — it was just gathering dust!",
            "I'm terrified of elevators, so I'm going to start taking steps to avoid them.",
            "What do you call a fish wearing a crown? King Fish!",
            "I lost my job at the bank. A woman asked me to check her balance, so I pushed her over.",
            "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
            "I haven't slept for ten days, because that would be too long."
        ]

        pun_text = random.choice(puns)

        embed = discord.Embed(
            title="🎭 Random Pun",
            description=pun_text,
            color=0xFF69B4
        )

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Jokes(bot))