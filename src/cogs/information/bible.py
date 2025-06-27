"""
Bible verse commands
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import aiohttp
import json
import random
from utils.decorators import guild_setting_enabled, typing_context


class Bible(commands.Cog):
    """Bible verse commands"""

    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://bible-api.com"

        # Popular verses for random selection
        self.popular_verses = [
            "John 3:16", "Romans 8:28", "Philippians 4:13", "Psalms 23:1",
            "Jeremiah 29:11", "Isaiah 41:10", "Matthew 28:20", "Romans 8:38-39",
            "Proverbs 3:5-6", "1 Corinthians 13:4-7", "Psalms 46:1", "John 14:6"
        ]

    @commands.command(aliases=["verse", "scripture"])
    @guild_setting_enabled("bible")
    @typing_context()
    async def bible(self, ctx, *, verse: str = None):
        """Get a Bible verse

        Usage: l.bible [verse reference]
        Examples:
        l.bible - Random popular verse
        l.bible John 3:16
        l.bible Psalms 23
        l.bible Romans 8:28
        """
        try:
            # If no verse specified, get a random popular one
            if not verse:
                verse = random.choice(self.popular_verses)
                is_random = True
            else:
                is_random = False

            # Clean and format verse reference
            verse = verse.replace(",", "").strip()

            # Fetch verse from Bible API
            url = f"{self.api_url}/{verse}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        embed = discord.Embed(
                            description=f"❌ Verse `{verse}` not found. Please check the reference and try again.\n\nExample: `John 3:16` or `Psalms 23:1`",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                        return
                    elif response.status != 200:
                        await ctx.send("❌ Bible service is currently unavailable. Please try again later.")
                        return

                    data = await response.json()

            # Parse the response
            reference = data.get("reference", verse)
            text = data.get("text", "").strip()
            translation = data.get("translation_name", "World English Bible")

            if not text:
                await ctx.send(f"❌ No text found for `{verse}`")
                return

            # Create embed
            embed = discord.Embed(
                title=f"📖 {reference}",
                description=text,
                color=0x4169E1
            )

            embed.add_field(
                name="Translation",
                value=translation,
                inline=True
            )

            if is_random:
                embed.add_field(
                    name="Type",
                    value="Random Verse",
                    inline=True
                )

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Bible API",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except KeyError as e:
            await ctx.send(f"❌ Error parsing Bible verse: {e}")
        except Exception as e:
            await ctx.send(f"❌ Error fetching Bible verse: {e}")

    @commands.command()
    @guild_setting_enabled("bible")
    async def dailyverse(self, ctx):
        """Get a daily inspirational verse"""
        daily_verses = [
            "Philippians 4:13", "Jeremiah 29:11", "Isaiah 41:10",
            "Romans 8:28", "Psalms 46:1", "Matthew 11:28-30",
            "2 Timothy 1:7", "Psalms 37:4", "1 Peter 5:7"
        ]

        # Use day of year to get consistent daily verse
        import datetime
        day_of_year = datetime.datetime.now().timetuple().tm_yday
        verse = daily_verses[day_of_year % len(daily_verses)]

        await self.bible.callback(self, ctx, verse=verse)


async def setup(bot):
    await bot.add_cog(Bible(bot))