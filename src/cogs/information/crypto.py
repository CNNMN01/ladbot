"""
Cryptocurrency price information with real API data
"""

import sys

import discord
from discord.ext import commands
import aiohttp
import json
from utils.decorators import guild_setting_enabled, typing_context
import logging

logger = logging.getLogger(__name__)


class Crypto(commands.Cog):
    """Cryptocurrency price commands with real-time data"""

    def __init__(self, bot):
        self.bot = bot
        # Use CoinGecko API for more reliable data
        self.api_url = "https://api.coingecko.com/api/v3/simple/price"

        # Popular crypto symbols mapped to CoinGecko IDs
        self.crypto_mapping = {
            'bitcoin': 'bitcoin',
            'btc': 'bitcoin',
            'ethereum': 'ethereum',
            'eth': 'ethereum',
            'dogecoin': 'dogecoin',
            'doge': 'dogecoin',
            'litecoin': 'litecoin',
            'ltc': 'litecoin',
            'cardano': 'cardano',
            'ada': 'cardano',
            'solana': 'solana',
            'sol': 'solana',
            'chainlink': 'chainlink',
            'link': 'chainlink',
            'polygon': 'matic-network',
            'matic': 'matic-network',
            'binancecoin': 'binancecoin',
            'bnb': 'binancecoin',
            'ripple': 'ripple',
            'xrp': 'ripple',
            'polkadot': 'polkadot',
            'dot': 'polkadot',
            'avalanche': 'avalanche-2',
            'avax': 'avalanche-2'
        }

        # Symbol mapping for display
        self.display_symbols = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'dogecoin': 'DOGE',
            'litecoin': 'LTC',
            'cardano': 'ADA',
            'solana': 'SOL',
            'chainlink': 'LINK',
            'matic-network': 'MATIC',
            'binancecoin': 'BNB',
            'ripple': 'XRP',
            'polkadot': 'DOT',
            'avalanche-2': 'AVAX'
        }

    @commands.command(aliases=["price", "coin"])
    @guild_setting_enabled("crypto")
    @typing_context()
    async def crypto(self, ctx, crypto_name: str = None):
        """Get real-time cryptocurrency price in USD

        Usage: l.crypto <cryptocurrency>
        Examples: l.crypto bitcoin, l.crypto ETH, l.crypto doge
        """
        if not crypto_name:
            embed = discord.Embed(
                title="💰 Crypto Price Checker",
                description=f"Get real-time cryptocurrency prices!\n\nUsage: `{self.bot.command_prefix}crypto <coin>`",
                color=0xFFD700
            )

            popular_coins = "BTC, ETH, DOGE, LTC, ADA, SOL, LINK, MATIC, BNB, XRP"
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

            embed.set_footer(text="Real-time data from CoinGecko")
            await ctx.send(embed=embed)
            return

        try:
            # Normalize crypto name and get CoinGecko ID
            crypto_id = self.crypto_mapping.get(crypto_name.lower())

            if not crypto_id:
                # Try direct lookup if not in mapping
                crypto_id = crypto_name.lower()

            logger.info(f"Fetching price for {crypto_id}")

            # Fetch real price data from CoinGecko API
            async with aiohttp.ClientSession() as session:
                params = {
                    "ids": crypto_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true"
                }

                async with session.get(self.api_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"CoinGecko API error: {response.status}")
                        await ctx.send("❌ Crypto service is temporarily unavailable. Please try again later.")
                        return

                    data = await response.json()

            # Check if crypto was found
            if not data or crypto_id not in data:
                embed = discord.Embed(
                    description=f"❌ Cryptocurrency `{crypto_name}` not found.\nTry popular coins like: BTC, ETH, DOGE, LTC, ADA",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            # Extract price data
            crypto_data = data[crypto_id]
            price_usd = float(crypto_data["usd"])

            # Get display symbol
            display_symbol = self.display_symbols.get(crypto_id, crypto_name.upper())

            # Format price appropriately
            if price_usd >= 1:
                formatted_price = f"${price_usd:,.2f}"
            elif price_usd >= 0.01:
                formatted_price = f"${price_usd:.4f}"
            elif price_usd >= 0.0001:
                formatted_price = f"${price_usd:.6f}"
            else:
                formatted_price = f"${price_usd:.8f}"

            # Create embed
            color = 0x00ff00 if crypto_data.get("usd_24h_change", 0) >= 0 else 0xff0000

            embed = discord.Embed(
                title=f"💰 {display_symbol} Price",
                description=f"**Current Price: {formatted_price} USD**",
                color=color
            )

            # Add price breakdown
            embed.add_field(
                name="💵 USD",
                value=formatted_price,
                inline=True
            )

            # Calculate amounts you can buy
            if price_usd > 0:
                amount_100 = 100 / price_usd
                amount_1000 = 1000 / price_usd

                if amount_100 >= 1:
                    embed.add_field(
                        name="🧮 For $100",
                        value=f"{amount_100:,.4f} {display_symbol}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🧮 For $100",
                        value=f"{amount_100:.8f} {display_symbol}",
                        inline=True
                    )

                if amount_1000 >= 1:
                    embed.add_field(
                        name="🧮 For $1000",
                        value=f"{amount_1000:,.4f} {display_symbol}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🧮 For $1000",
                        value=f"{amount_1000:.8f} {display_symbol}",
                        inline=True
                    )

            # Add 24h change if available
            if "usd_24h_change" in crypto_data:
                change_24h = crypto_data["usd_24h_change"]
                change_emoji = "📈" if change_24h >= 0 else "📉"
                change_color = "+" if change_24h >= 0 else ""
                embed.add_field(
                    name=f"{change_emoji} 24h Change",
                    value=f"{change_color}{change_24h:.2f}%",
                    inline=True
                )

            # Add market cap if available
            if "usd_market_cap" in crypto_data:
                market_cap = crypto_data["usd_market_cap"]
                if market_cap:
                    if market_cap >= 1_000_000_000:
                        market_cap_str = f"${market_cap/1_000_000_000:.2f}B"
                    elif market_cap >= 1_000_000:
                        market_cap_str = f"${market_cap/1_000_000:.2f}M"
                    else:
                        market_cap_str = f"${market_cap:,.0f}"

                    embed.add_field(
                        name="📊 Market Cap",
                        value=market_cap_str,
                        inline=True
                    )

            # Add crypto emoji to title
            crypto_emoji = self._get_crypto_emoji(display_symbol)
            if crypto_emoji != '💰':
                embed.title = f"{crypto_emoji} {display_symbol} Price"

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Real-time data from CoinGecko",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except ValueError as e:
            logger.error(f"ValueError in crypto command: {e}")
            await ctx.send("❌ Error parsing price data. Please try again.")
        except KeyError as e:
            logger.error(f"KeyError in crypto command: {e}")
            await ctx.send(f"❌ Cryptocurrency `{crypto_name}` not found. Try: BTC, ETH, DOGE, LTC")
        except Exception as e:
            logger.error(f"Unexpected error in crypto command: {e}")
            await ctx.send(f"❌ Error fetching crypto price. Please try again later.")

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
            'MATIC': '🔷',
            'BNB': '🔶',
            'XRP': '💧',
            'DOT': '🔴',
            'AVAX': '🏔️'
        }
        return emoji_map.get(symbol, '💰')


async def setup(bot):
    await bot.add_cog(Crypto(bot))