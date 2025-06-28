"""
Enhanced Bible verse commands with multiple APIs and rich features
"""

import discord
from discord.ext import commands
import aiohttp
import json
import random
import asyncio
from datetime import datetime
from utils.decorators import guild_setting_enabled, typing_context
import logging

logger = logging.getLogger(__name__)


class Bible(commands.Cog):
    """Enhanced Bible verse commands with multiple APIs"""

    def __init__(self, bot):
        self.bot = bot

        # Multiple API endpoints for reliability
        self.apis = {
            'bible_api': "https://bible-api.com",
            'scripture_api': "https://scripture-api.com/api/verses",
            'api_bible': "https://api.bible/v1/bibles/de4e12af7f28f599-02/verses"
        }

        # Popular verses categorized
        self.verse_categories = {
            'love': [
                "1 Corinthians 13:4-8", "John 3:16", "1 John 4:7-8",
                "Romans 8:38-39", "Ephesians 3:17-19"
            ],
            'strength': [
                "Philippians 4:13", "Isaiah 41:10", "Psalms 46:1",
                "2 Timothy 1:7", "Joshua 1:9"
            ],
            'peace': [
                "John 14:27", "Philippians 4:6-7", "Isaiah 26:3",
                "Matthew 11:28-30", "Romans 15:13"
            ],
            'hope': [
                "Jeremiah 29:11", "Romans 8:28", "Psalms 37:4",
                "Isaiah 40:31", "1 Peter 5:7"
            ],
            'wisdom': [
                "Proverbs 3:5-6", "James 1:5", "Proverbs 27:17",
                "Ecclesiastes 3:1", "Psalms 119:105"
            ],
            'popular': [
                "John 3:16", "Romans 8:28", "Philippians 4:13", "Psalms 23:1",
                "Jeremiah 29:11", "Isaiah 41:10", "Matthew 28:20", "Romans 8:38-39",
                "Proverbs 3:5-6", "1 Corinthians 13:4-7", "Psalms 46:1", "John 14:6"
            ]
        }

        # Available translations
        self.translations = {
            'web': 'World English Bible',
            'kjv': 'King James Version',
            'niv': 'New International Version',
            'esv': 'English Standard Version',
            'nlt': 'New Living Translation',
            'nasb': 'New American Standard Bible'
        }

    async def _fetch_verse_primary(self, verse_ref, translation='web'):
        """Fetch verse from primary API (bible-api.com)"""
        try:
            url = f"{self.apis['bible_api']}/{verse_ref}"
            if translation != 'web':
                url += f"?translation={translation}"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'reference': data.get('reference', verse_ref),
                            'text': data.get('text', '').strip(),
                            'translation': data.get('translation_name', self.translations.get(translation, 'Unknown')),
                            'source': 'Bible API'
                        }
                    return None
        except Exception as e:
            logger.warning(f"Primary API failed for {verse_ref}: {e}")
            return None

    async def _fetch_verse_fallback(self, verse_ref):
        """Fallback verse fetching method"""
        fallback_verses = {
            "john 3:16": {
                'reference': 'John 3:16',
                'text': 'For God so loved the world, that he gave his one and only Son, that whoever believes in him should not perish, but have eternal life.',
                'translation': 'World English Bible',
                'source': 'Local Cache'
            },
            "philippians 4:13": {
                'reference': 'Philippians 4:13',
                'text': 'I can do all things through Christ, who strengthens me.',
                'translation': 'World English Bible',
                'source': 'Local Cache'
            },
            "psalms 23:1": {
                'reference': 'Psalms 23:1',
                'text': 'Yahweh is my shepherd: I shall lack nothing.',
                'translation': 'World English Bible',
                'source': 'Local Cache'
            }
        }

        key = verse_ref.lower().replace(" ", " ").strip()
        return fallback_verses.get(key)

    @commands.group(aliases=["verse", "scripture"], invoke_without_command=True)
    @guild_setting_enabled("bible")
    @typing_context()
    async def bible(self, ctx, *, verse: str = None):
        """Get a Bible verse

        Usage:
        l.bible [verse reference] - Get specific verse
        l.bible - Random popular verse
        l.bible random [category] - Random verse from category

        Examples:
        l.bible John 3:16
        l.bible Psalms 23
        l.bible Romans 8:28
        """
        try:
            # If no verse specified, get a random popular one
            if not verse:
                verse = random.choice(self.verse_categories['popular'])
                is_random = True
                category_used = "popular"
            else:
                is_random = False
                category_used = None

            # Clean and format verse reference
            verse = verse.replace(",", "").strip()

            # Try to fetch verse
            verse_data = await self._fetch_verse_primary(verse)

            if not verse_data:
                verse_data = await self._fetch_verse_fallback(verse)

            if not verse_data:
                embed = discord.Embed(
                    description=f"❌ Verse `{verse}` not found. Please check the reference and try again.\n\n**Examples:** `John 3:16`, `Psalms 23:1`, `Romans 8:28`",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Tip",
                    value="Try `l.bible random` for a random verse or `l.bible categories` to see available categories",
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            # Create clean, beautiful embed
            embed = discord.Embed(
                title=f"📖 {verse_data['reference']}",
                description=f"*{verse_data['text']}*",
                color=0x4169E1
            )

            # Only show category if it was a random verse
            if is_random and category_used:
                embed.add_field(
                    name="🎲 Random Verse",
                    value=f"From {category_used.title()} category",
                    inline=True
                )

            # Clean footer without technical details
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in bible command: {e}")
            embed = discord.Embed(
                description="❌ Sorry, there was an error fetching the Bible verse. Please try again later.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    @bible.command(name="random")
    @guild_setting_enabled("bible")
    async def bible_random(self, ctx, category: str = "popular"):
        """Get a random verse from a specific category

        Categories: love, strength, peace, hope, wisdom, popular
        """
        category = category.lower()

        if category not in self.verse_categories:
            available = ", ".join(self.verse_categories.keys())
            embed = discord.Embed(
                description=f"❌ Unknown category `{category}`\n\n**Available categories:** {available}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        verse = random.choice(self.verse_categories[category])

        # Fetch and display the verse with category info
        verse_data = await self._fetch_verse_primary(verse)

        if not verse_data:
            verse_data = await self._fetch_verse_fallback(verse)

        if not verse_data:
            await ctx.send("❌ Sorry, couldn't fetch a verse right now. Please try again.")
            return

        # Create embed with category information
        embed = discord.Embed(
            title=f"📖 {verse_data['reference']}",
            description=f"*{verse_data['text']}*",
            color=0x4169E1
        )

        embed.add_field(
            name=f"🎲 Random {category.title()} Verse",
            value=f"One of {len(self.verse_categories[category])} verses in this category",
            inline=True
        )

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )

        await ctx.send(embed=embed)

    @bible.command(name="daily")
    @guild_setting_enabled("bible")
    async def bible_daily(self, ctx):
        """Get today's inspirational verse"""
        daily_verses = [
            "Philippians 4:13", "Jeremiah 29:11", "Isaiah 41:10",
            "Romans 8:28", "Psalms 46:1", "Matthew 11:28-30",
            "2 Timothy 1:7", "Psalms 37:4", "1 Peter 5:7",
            "John 14:27", "Proverbs 3:5-6", "Joshua 1:9"
        ]

        # Use day of year to get consistent daily verse
        day_of_year = datetime.now().timetuple().tm_yday
        verse = daily_verses[day_of_year % len(daily_verses)]

        # Fetch the verse
        verse_data = await self._fetch_verse_primary(verse)

        if not verse_data:
            verse_data = await self._fetch_verse_fallback(verse)

        if not verse_data:
            await ctx.send("❌ Sorry, couldn't fetch today's verse. Please try again.")
            return

        # Create embed for daily verse
        embed = discord.Embed(
            title=f"📖 {verse_data['reference']}",
            description=f"*{verse_data['text']}*",
            color=0x4169E1
        )

        embed.add_field(
            name=f"📅 Daily Verse - {datetime.now().strftime('%B %d')}",
            value="Today's inspirational message",
            inline=True
        )

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )

        await ctx.send(embed=embed)

    @bible.command(name="search")
    @guild_setting_enabled("bible")
    async def bible_search(self, ctx, *, keywords: str):
        """Search for verses containing specific keywords (coming soon)"""
        embed = discord.Embed(
            title="🔍 Bible Search",
            description="Bible search functionality is coming soon! For now, try these options:",
            color=0xffaa00
        )

        embed.add_field(
            name="📖 Get Specific Verse",
            value="`l.bible John 3:16`",
            inline=False
        )

        embed.add_field(
            name="🎲 Random by Category",
            value="`l.bible random love` or `l.bible random strength`",
            inline=False
        )

        embed.add_field(
            name="📅 Daily Verse",
            value="`l.bible daily`",
            inline=False
        )

        await ctx.send(embed=embed)

    @bible.command(name="categories")
    @guild_setting_enabled("bible")
    async def bible_categories(self, ctx):
        """Show available verse categories"""
        embed = discord.Embed(
            title="📚 Bible Verse Categories",
            description="Available categories for random verses:",
            color=0x4169E1
        )

        for category, verses in self.verse_categories.items():
            sample_verse = verses[0] if verses else "No verses"
            embed.add_field(
                name=f"💫 {category.title()}",
                value=f"{len(verses)} verses\n*Example: {sample_verse}*",
                inline=True
            )

        embed.add_field(
            name="📝 Usage",
            value="`l.bible random [category]`\nExample: `l.bible random love`",
            inline=False
        )

        await ctx.send(embed=embed)

    @bible.command(name="help")
    @guild_setting_enabled("bible")
    async def bible_help(self, ctx):
        """Show detailed help for Bible commands"""
        embed = discord.Embed(
            title="📖 Bible Commands Help",
            description="Complete guide to using Bible commands",
            color=0x4169E1
        )

        commands_help = [
            ("`l.bible [verse]`", "Get a specific verse or random popular verse"),
            ("`l.bible random [category]`", "Random verse from category (love, strength, peace, etc.)"),
            ("`l.bible daily`", "Get today's inspirational verse"),
            ("`l.bible categories`", "Show all available categories"),
            ("`l.bible help`", "Show this help message")
        ]

        for command, description in commands_help:
            embed.add_field(
                name=command,
                value=description,
                inline=False
            )

        embed.add_field(
            name="📝 Examples",
            value=(
                "`l.bible John 3:16` - Get John 3:16\n"
                "`l.bible Psalms 23` - Get Psalms 23\n"
                "`l.bible random love` - Random love verse\n"
                "`l.bible daily` - Today's verse"
            ),
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Bible(bot))