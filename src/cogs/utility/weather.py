"""
Weather information command with multiple fallbacks
"""

import sys


import discord
from discord.ext import commands
import aiohttp
import json
import asyncio
import logging
from utils.decorators import guild_setting_enabled, typing_context

logger = logging.getLogger(__name__)


class Weather(commands.Cog):
    """Weather information commands with fallback support"""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = self._get_api_key()
        self.timeout = 10  # Request timeout in seconds

        # Cache for rate limiting
        self._cache = {}
        self._cache_duration = 300  # 5 minutes

    def _get_api_key(self):
        """Get OpenWeatherMap API key with fallback"""
        import os
        key = os.getenv("OPENWEATHER_API_KEY", "").strip()

        # Check if key is set and not the placeholder
        if key and key != "your_openweather_key_here":
            logger.info("Weather: Using OpenWeatherMap API")
            return key
        else:
            logger.info("Weather: No API key configured, using fallback services")
            return None

    @commands.command(aliases=["w"])
    @guild_setting_enabled("weather")
    @typing_context()
    async def weather(self, ctx, *, location: str = None):
        """Get weather information for a location

        Usage: l.weather <city name>
        Examples: l.weather London, l.weather New York, l.weather Tokyo
        """
        if not location:
            embed = discord.Embed(
                title="🌤️ Weather Command",
                description=f"Get current weather information!\n\nUsage: `{self.bot.command_prefix}weather <city name>`",
                color=0x4169E1
            )

            embed.add_field(
                name="Examples",
                value=f"`{self.bot.command_prefix}weather London`\n`{self.bot.command_prefix}weather New York`\n`{self.bot.command_prefix}weather Tokyo`",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        # Clean location input
        location = location.strip()
        if len(location) > 50:
            await ctx.send("❌ Location name too long! Please use a shorter name.")
            return

        # Check cache first
        cache_key = location.lower()
        if cache_key in self._cache:
            cached_time, cached_embed = self._cache[cache_key]
            if (asyncio.get_event_loop().time() - cached_time) < self._cache_duration:
                cached_embed.set_footer(
                    text=f"{cached_embed.footer.text} • Cached data",
                    icon_url=cached_embed.footer.icon_url
                )
                await ctx.send(embed=cached_embed)
                return

        # Try different weather sources in order of preference
        weather_embed = None

        # 1. Try OpenWeatherMap (if API key available)
        if self.api_key:
            weather_embed = await self._get_weather_openweather(location)

        # 2. Fallback to wttr.in (no API key needed)
        if not weather_embed:
            weather_embed = await self._get_weather_wttr(location)

        # 3. Final fallback - helpful links and alternatives
        if not weather_embed:
            weather_embed = await self._create_weather_fallback(location)

        # Cache the result
        if weather_embed:
            self._cache[cache_key] = (asyncio.get_event_loop().time(), weather_embed)

        await ctx.send(embed=weather_embed)

    async def _get_weather_openweather(self, location: str) -> discord.Embed:
        """Get weather from OpenWeatherMap API"""
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric"
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 404:
                        logger.warning(f"OpenWeatherMap: Location '{location}' not found")
                        return None
                    elif response.status == 401:
                        logger.error("OpenWeatherMap: Invalid API key")
                        return None
                    elif response.status != 200:
                        logger.error(f"OpenWeatherMap: HTTP {response.status}")
                        return None

                    data = await response.json()

            # Parse weather data
            city_name = data["name"]
            country = data["sys"]["country"]
            temp_c = round(data["main"]["temp"])
            temp_f = round(temp_c * 9 / 5 + 32)
            feels_like_c = round(data["main"]["feels_like"])
            feels_like_f = round(feels_like_c * 9 / 5 + 32)
            humidity = data["main"]["humidity"]
            pressure = data["main"]["pressure"]
            description = data["weather"][0]["description"].title()
            icon = data["weather"][0]["icon"]
            wind_speed = data["wind"]["speed"]

            # Create embed
            embed = discord.Embed(
                title=f"🌤️ Weather in {city_name}, {country}",
                description=description,
                color=self._get_weather_color(icon)
            )

            embed.add_field(
                name="🌡️ Temperature",
                value=f"**{temp_c}°C** ({temp_f}°F)\nFeels like {feels_like_c}°C ({feels_like_f}°F)",
                inline=True
            )

            embed.add_field(
                name="💧 Humidity",
                value=f"{humidity}%",
                inline=True
            )

            embed.add_field(
                name="🌬️ Wind Speed",
                value=f"{wind_speed} m/s",
                inline=True
            )

            embed.add_field(
                name="📊 Pressure",
                value=f"{pressure} hPa",
                inline=True
            )

            # Add weather icon
            embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon}@2x.png")

            embed.set_footer(
                text="Data from OpenWeatherMap",
                icon_url="https://openweathermap.org/themes/openweathermap/assets/img/logo_white_cropped.png"
            )

            logger.info(f"OpenWeatherMap: Successfully got weather for {city_name}")
            return embed

        except asyncio.TimeoutError:
            logger.error("OpenWeatherMap: Request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"OpenWeatherMap: Network error - {e}")
            return None
        except KeyError as e:
            logger.error(f"OpenWeatherMap: Invalid response format - {e}")
            return None
        except Exception as e:
            logger.error(f"OpenWeatherMap: Unexpected error - {e}")
            return None

    async def _get_weather_wttr(self, location: str) -> discord.Embed:
        """Get weather from wttr.in (no API key required)"""
        try:
            # wttr.in provides free weather data without API key
            url = f"http://wttr.in/{location}?format=j1"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"wttr.in: HTTP {response.status}")
                        return None

                    data = await response.json()

            # Parse wttr.in data
            if not data.get('current_condition'):
                logger.error("wttr.in: Invalid response format")
                return None

            current = data['current_condition'][0]
            nearest_area = data.get('nearest_area', [{}])[0]

            # Extract data
            weather_desc = current['weatherDesc'][0]['value']
            temp_c = int(current['temp_C'])
            temp_f = int(current['temp_F'])
            humidity = current['humidity']
            pressure = current['pressure']
            wind_speed = current['windspeedKmph']
            feels_like_c = int(current['FeelsLikeC'])
            feels_like_f = int(current['FeelsLikeF'])

            # Get location name
            city_name = nearest_area.get('areaName', [{}])[0].get('value', location.title())
            country = nearest_area.get('country', [{}])[0].get('value', '')

            embed = discord.Embed(
                title=f"🌤️ Weather in {city_name}" + (f", {country}" if country else ""),
                description=weather_desc,
                color=0x4169E1
            )

            embed.add_field(
                name="🌡️ Temperature",
                value=f"**{temp_c}°C** ({temp_f}°F)\nFeels like {feels_like_c}°C ({feels_like_f}°F)",
                inline=True
            )

            embed.add_field(
                name="💧 Humidity",
                value=f"{humidity}%",
                inline=True
            )

            embed.add_field(
                name="🌬️ Wind Speed",
                value=f"{wind_speed} km/h",
                inline=True
            )

            embed.add_field(
                name="📊 Pressure",
                value=f"{pressure} mb",
                inline=True
            )

            embed.set_footer(text="Data from wttr.in • Free weather service")

            logger.info(f"wttr.in: Successfully got weather for {city_name}")
            return embed

        except asyncio.TimeoutError:
            logger.error("wttr.in: Request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"wttr.in: Network error - {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"wttr.in: Data parsing error - {e}")
            return None
        except Exception as e:
            logger.error(f"wttr.in: Unexpected error - {e}")
            return None

    async def _create_weather_fallback(self, location: str) -> discord.Embed:
        """Create helpful fallback when all weather services fail"""
        embed = discord.Embed(
            title="🌤️ Weather Information",
            description="Weather services are currently unavailable, but here are some alternatives:",
            color=0xffaa00
        )

        # URL-encode the location for links
        import urllib.parse
        encoded_location = urllib.parse.quote(location)

        embed.add_field(
            name="🔗 Quick Weather Links",
            value=(
                f"• [Weather.com](https://weather.com/weather/today/l/{encoded_location})\n"
                f"• [AccuWeather](https://www.accuweather.com/en/search-locations?query={encoded_location})\n"
                f"• [Weather.gov](https://www.weather.gov/) (US locations)\n"
                f"• [BBC Weather](https://www.bbc.com/weather/search?query={encoded_location})\n"
                f"• [Google Weather](https://www.google.com/search?q=weather+{encoded_location})"
            ),
            inline=False
        )

        embed.add_field(
            name="📱 Quick Tips",
            value=(
                "• Ask Siri/Google: *'What's the weather in [city]?'*\n"
                "• Use your phone's built-in weather app\n"
                "• Try voice assistants on smart speakers\n"
                "• Check local news websites"
            ),
            inline=False
        )

        embed.add_field(
            name="🎯 You searched for",
            value=f"`{location}`",
            inline=True
        )

        if not self.api_key:
            embed.add_field(
                name="🔧 For Bot Owners",
                value=(
                    "**To enable full weather features:**\n"
                    "1. Get free API key: [openweathermap.org/api](https://openweathermap.org/api)\n"
                    "2. Add to .env: `OPENWEATHER_API_KEY=your_key`\n"
                    "3. Restart bot\n"
                    "*Free tier: 1000 calls/day*"
                ),
                inline=False
            )

        embed.set_footer(text="💡 Weather data will be back soon!")
        return embed

    def _get_weather_color(self, icon: str) -> int:
        """Get embed color based on weather icon"""
        if icon.startswith('01'):  # Clear sky
            return 0xFFD700  # Gold
        elif icon.startswith('02'):  # Few clouds
            return 0x87CEEB  # Sky blue
        elif icon.startswith(('03', '04')):  # Clouds
            return 0x708090  # Slate gray
        elif icon.startswith(('09', '10')):  # Rain
            return 0x4169E1  # Royal blue
        elif icon.startswith('11'):  # Thunderstorm
            return 0x4B0082  # Indigo
        elif icon.startswith('13'):  # Snow
            return 0xF0F8FF  # Alice blue
        elif icon.startswith('50'):  # Mist
            return 0xA9A9A9  # Dark gray
        else:
            return 0x4169E1  # Default blue

    @commands.command()
    @guild_setting_enabled("weather")
    async def forecast(self, ctx, *, location: str = None):
        """Get weather forecast (premium feature hint)"""
        if not location:
            await ctx.send(f"❌ Please provide a location! Usage: `{self.bot.command_prefix}forecast <city>`")
            return

        embed = discord.Embed(
            title="🔮 Weather Forecast",
            description="Extended forecasts coming soon!",
            color=0x00ff00
        )

        embed.add_field(
            name="🚧 Under Development",
            value="Multi-day forecasts will be available in a future update.",
            inline=False
        )

        embed.add_field(
            name="🔗 For now, try these:",
            value=(
                f"• [Weather.com 10-day forecast](https://weather.com/weather/tenday/l/{location})\n"
                f"• [AccuWeather forecast](https://www.accuweather.com/en/search-locations?query={location})\n"
                f"• Use `{self.bot.command_prefix}weather {location}` for current conditions"
            ),
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Weather(bot))