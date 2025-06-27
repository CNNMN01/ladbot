"""
General utility tools and commands
"""

import sys


import discord
from discord.ext import commands
from utils.decorators import guild_setting_enabled
import base64
import hashlib


class Tools(commands.Cog):
    """General utility tools"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def encode(self, ctx, *, text: str):
        """Encode text to base64"""
        try:
            encoded = base64.b64encode(text.encode()).decode()

            embed = discord.Embed(
                title="🔒 Base64 Encoder",
                color=0x00ff00
            )
            embed.add_field(name="Original", value=f"```{text[:100]}```", inline=False)
            embed.add_field(name="Encoded", value=f"```{encoded[:100]}```", inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error encoding: {e}")

    @commands.command()
    async def decode(self, ctx, *, encoded_text: str):
        """Decode base64 text"""
        try:
            decoded = base64.b64decode(encoded_text.encode()).decode()

            embed = discord.Embed(
                title="🔓 Base64 Decoder",
                color=0x00ff00
            )
            embed.add_field(name="Encoded", value=f"```{encoded_text[:100]}```", inline=False)
            embed.add_field(name="Decoded", value=f"```{decoded[:100]}```", inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error decoding: {e}")

    @commands.command()
    async def hash(self, ctx, *, text: str):
        """Generate hash of text"""
        try:
            md5_hash = hashlib.md5(text.encode()).hexdigest()
            sha256_hash = hashlib.sha256(text.encode()).hexdigest()

            embed = discord.Embed(
                title="🔐 Text Hasher",
                color=0x00ff00
            )
            embed.add_field(name="Original", value=f"```{text[:50]}```", inline=False)
            embed.add_field(name="MD5", value=f"```{md5_hash}```", inline=False)
            embed.add_field(name="SHA256", value=f"```{sha256_hash[:50]}...```", inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error hashing: {e}")

    @commands.command()
    async def reverse(self, ctx, *, text: str):
        """Reverse text"""
        reversed_text = text[::-1]

        embed = discord.Embed(
            title="🔄 Text Reverser",
            color=0x00ff00
        )
        embed.add_field(name="Original", value=f"```{text}```", inline=False)
        embed.add_field(name="Reversed", value=f"```{reversed_text}```", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def count(self, ctx, *, text: str):
        """Count characters, words, and lines in text"""
        char_count = len(text)
        word_count = len(text.split())
        line_count = len(text.split('\n'))

        embed = discord.Embed(
            title="📊 Text Counter",
            color=0x00ff00
        )
        embed.add_field(name="Characters", value=char_count, inline=True)
        embed.add_field(name="Words", value=word_count, inline=True)
        embed.add_field(name="Lines", value=line_count, inline=True)
        embed.add_field(name="Text Preview", value=f"```{text[:100]}```", inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tools(bot))