"""
Cryptocurrency price information
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import aiohttp
import json
from utils.decorators import guild_setting_enabled, typing_context


class Crypto(commands.Cog):
    """Cryptocurrency price commands"""

    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.coinbase.com/v2/exchange-rates"

        # Popular crypto symbols
        self.crypto_symbols = {
            'bitcoin': 'BTC',
            'btc': 'BTC',
            'ethereum': 'ETH',
            'eth': 'ETH',
            'dogecoin': 'DOGE',
            'doge': 'DOGE',
            'litecoin': 'LTC',
            'ltc': 'LTC',
            'cardano': 'ADA',
            'ada': 'ADA',
            'solana': 'SOL',
            'sol': 'SOL',
            'chainlink': 'LINK',
            'link': 'LINK',
            'polygon': 'MATIC',
            'matic': 'MATIC'
        }

    @commands.command(aliases=["price", "coin"])
    @guild_setting_enabled("crypto")
    @typing_context()
    async def crypto(self, ctx, crypto_name: str = None):
        """Get cryptocurrency price in USD

        Usage: l.crypto <cryptocurrency>
        Examples: l.crypto bitcoin, l.crypto ETH, l.crypto doge
        """
        if not crypto_name:
            embed = discord.Embed(
                title="💰 Crypto Price Checker",
                description=f"Get current cryptocurrency prices!\n\nUsage: `{self.bot.command_prefix}crypto <coin>`",
                color=0x00ff00
            )

            popular_coins = "BTC, ETH, DOGE, LTC, ADA, SOL, LINK, MATIC"
            embed.add_field(
                name="Popular Coins",
                value=popular_coins,
                inline=False
            )

            embed.add_field(
                name="Examples",
                value=f"`{self.bot.command_prefix}crypto bitcoin`\n`{self.bot.command_prefix}crypto ETH`\n`{self.bot.command_prefix}crypto doge`",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        try:
            # Normalize crypto name
            crypto_symbol = self.crypto_symbols.get(crypto_name.lower(), crypto_name.upper())

            # Fetch price data from Coinbase API
            async with aiohttp.ClientSession() as session:
                params = {"currency": crypto_symbol}
                async with session.get(self.api_url, params=params) as response:
                    if response.status != 200:
                        await ctx.send("❌ Crypto service is currently unavailable. Please try again later.")
                        return

                    data = await response.json()

            # Check if crypto exists
            if crypto_symbol not in data["data"]["rates"]:
                embed = discord.Embed(
                    description=f"❌ Cryptocurrency `{crypto_name}` not found.\nTry popular coins like: BTC, ETH, DOGE, LTC",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            # Get price data
            usd_rate = float(data["data"]["rates"][crypto_symbol])
            price_usd = 1 / usd_rate  # Convert to USD price

            # Format price nicely
            if price_usd >= 1:
                formatted_price = f"${price_usd:,.2f}"
            elif price_usd >= 0.01:
                formatted_price = f"${price_usd:.4f}"
            else:
                formatted_price = f"${price_usd:.8f}"

            # Create embed
            embed = discord.Embed(
                title=f"💰 {crypto_symbol} Price",
                description=f"**Current Price: {formatted_price} USD**",
                color=0xFFD700
            )

            # Add price breakdown
            embed.add_field(
                name="💵 USD",
                value=formatted_price,
                inline=True
            )

            # Calculate other amounts
            embed.add_field(
                name="🧮 For $100",
                value=f"{100 / price_usd:.4f} {crypto_symbol}",
                inline=True
            )

            embed.add_field(
                name="🧮 For $1000",
                value=f"{1000 / price_usd:.4f} {crypto_symbol}",
                inline=True
            )

            # Get crypto emoji
            crypto_emoji = self._get_crypto_emoji(crypto_symbol)
            embed.set_thumbnail(url=f"https://cryptoicons.org/api/icon/{crypto_symbol.lower()}/200")

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Data from Coinbase",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except ValueError:
            await ctx.send("❌ Error parsing price data. The cryptocurrency might not be available.")
        except KeyError:
            await ctx.send(f"❌ Cryptocurrency `{crypto_name}` not found. Try: BTC, ETH, DOGE, LTC")
        except Exception as e:
            await ctx.send(f"❌ Error fetching crypto price: {e}")

    def _get_crypto_emoji(self, symbol):
        """Get emoji for crypto symbol"""
        emoji_map = {
            'BTC': '₿',
            'ETH': 'Ξ',
            'DOGE': '🐕',
            'LTC': 'Ł',
            'ADA': '🎴',
            'SOL': '☀️',
            'LINK': '🔗',
            'MATIC': '🔷'
        }
        return emoji_map.get(symbol, '💰')


async def setup(bot):
    await bot.add_cog(Crypto(bot))