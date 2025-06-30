"""
Magic 8-Ball command - Fixed version
"""

import sys
import os
import json
from pathlib import Path

import discord
from discord.ext import commands
import random
import asyncio
from utils.decorators import guild_setting_enabled, typing_context
import logging

logger = logging.getLogger(__name__)


class EightBall(commands.Cog):
    """Magic 8-Ball fortune telling"""

    def __init__(self, bot):
        self.bot = bot
        self._responses = None

    @property
    def responses(self):
        """Lazy load 8-ball responses with multiple fallback methods"""
        if self._responses is None:
            self._responses = self._load_responses()
        return self._responses

    def _load_responses(self):
        """Load 8ball responses from multiple possible sources"""
        # Method 1: Try bot data manager
        try:
            if hasattr(self.bot, 'data_manager'):
                response_data = self.bot.data_manager.get_json("8ball")
                if response_data:
                    logger.info(f"Loaded {len(response_data)} 8ball responses from data manager")
                    return [discord.Embed.from_dict(resp) for resp in response_data]
        except Exception as e:
            logger.warning(f"Failed to load 8ball responses from data manager: {e}")

        # Method 2: Try direct file access
        try:
            # Try multiple possible paths
            possible_paths = [
                Path("data/json/8ball.json"),
                Path("data/8ball.json"),
                Path("src/data/json/8ball.json"),
                Path("8ball.json")
            ]

            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                        if response_data:
                            logger.info(f"Loaded {len(response_data)} 8ball responses from {path}")
                            return [discord.Embed.from_dict(resp) for resp in response_data]
        except Exception as e:
            logger.warning(f"Failed to load 8ball responses from file: {e}")

        # Method 3: Hardcoded fallback responses (always works)
        logger.info("Using hardcoded 8ball responses as fallback")
        return [
            # Positive responses (green)
            discord.Embed(description="🎱 It is certain", color=0x00ff00),
            discord.Embed(description="🎱 It is decidedly so", color=0x00ff00),
            discord.Embed(description="🎱 Without a doubt", color=0x00ff00),
            discord.Embed(description="🎱 Yes definitely", color=0x00ff00),
            discord.Embed(description="🎱 You may rely on it", color=0x00ff00),
            discord.Embed(description="🎱 As I see it, yes", color=0x00ff00),
            discord.Embed(description="🎱 Most likely", color=0x00ff00),
            discord.Embed(description="🎱 Outlook good", color=0x00ff00),
            discord.Embed(description="🎱 Yes", color=0x00ff00),
            discord.Embed(description="🎱 Signs point to yes", color=0x00ff00),

            # Neutral responses (yellow)
            discord.Embed(description="🎱 Reply hazy, try again", color=0xffaa00),
            discord.Embed(description="🎱 Ask again later", color=0xffaa00),
            discord.Embed(description="🎱 Better not tell you now", color=0xffaa00),
            discord.Embed(description="🎱 Cannot predict now", color=0xffaa00),
            discord.Embed(description="🎱 Concentrate and ask again", color=0xffaa00),

            # Negative responses (red)
            discord.Embed(description="🎱 Don't count on it", color=0xff0000),
            discord.Embed(description="🎱 My reply is no", color=0xff0000),
            discord.Embed(description="🎱 My sources say no", color=0xff0000),
            discord.Embed(description="🎱 Outlook not so good", color=0xff0000),
            discord.Embed(description="🎱 Very doubtful", color=0xff0000),
        ]

    @commands.command(name="8ball", aliases=["eightball", "magic8ball"])
    @guild_setting_enabled("8ball")
    @typing_context()
    async def eight_ball(self, ctx, *, question: str = None):
        """Ask the Magic 8-Ball a question

        Usage: l.8ball <your question>
        Examples:
        l.8ball Will it rain tomorrow?
        l.8ball Should I eat pizza?
        """
        if not question:
            embed = discord.Embed(
                description="🎱 You need to ask a question for the Magic 8-Ball!\n\nExample: `l.8ball Will I have a good day?`",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        # Add dramatic effect
        thinking_msg = await ctx.send("🎱 **Consulting the mystical 8-Ball...**")
        await asyncio.sleep(2)

        # Get random response
        try:
            response_embed = random.choice(self.responses)

            # Add question to embed footer
            response_embed.set_footer(text=f"Question: {question[:100]}{'...' if len(question) > 100 else ''}")

            # Edit the thinking message with the response
            await thinking_msg.edit(content="", embed=response_embed)

        except Exception as e:
            logger.error(f"Error in 8ball command: {e}")
            # Emergency fallback
            emergency_embed = discord.Embed(
                description="🎱 The Magic 8-Ball is cloudy right now, try again later!",
                color=0xffaa00
            )
            await thinking_msg.edit(content="", embed=emergency_embed)


async def setup(bot):
    await bot.add_cog(EightBall(bot))