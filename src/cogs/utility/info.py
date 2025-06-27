"""
Bot information and statistics commands
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Info(commands.Cog):
    """Information and statistics commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def botstats(self, ctx):
        """Show bot statistics and uptime"""
        try:
            import psutil

            # Calculate uptime
            if hasattr(self.bot, 'start_time'):
                uptime = datetime.now() - self.bot.start_time
                uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            else:
                uptime_str = "Unknown"

            # Get system stats
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()

            embed = discord.Embed(
                title="📊 Bot Statistics",
                color=0x00ff00
            )

            # Bot stats
            embed.add_field(
                name="🤖 Bot Info",
                value=f"**Guilds:** {len(self.bot.guilds)}\n**Users:** {len(self.bot.users)}\n**Commands:** {len(self.bot.commands)}",
                inline=True
            )

            # System stats
            embed.add_field(
                name="💻 System",
                value=f"**CPU:** {cpu_percent}%\n**RAM:** {memory.percent}%\n**Uptime:** {uptime_str}",
                inline=True
            )

            # Version info
            embed.add_field(
                name="📚 Version",
                value=f"**Discord.py:** {discord.__version__}\n**Python:** {sys.version.split()[0]}",
                inline=True
            )

            # Add cog count
            embed.add_field(
                name="🧩 Loaded Cogs",
                value=f"**Total:** {len(self.bot.cogs)}\n**Admin:** {len([c for c in self.bot.cogs if 'admin' in c.lower()])}\n**Utility:** {len([c for c in self.bot.cogs if 'utility' in c.lower()])}",
                inline=True
            )

            # Performance info
            embed.add_field(
                name="⚡ Performance",
                value=f"**Latency:** {round(self.bot.latency * 1000)}ms\n**Commands Today:** {getattr(self.bot, 'commands_used_today', 'N/A')}",
                inline=True
            )

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except ImportError:
            # Fallback if psutil not available
            embed = discord.Embed(
                title="📊 Bot Statistics",
                color=0x00ff00
            )

            embed.add_field(
                name="🤖 Bot Info",
                value=f"**Guilds:** {len(self.bot.guilds)}\n**Users:** {len(self.bot.users)}\n**Commands:** {len(self.bot.commands)}",
                inline=True
            )

            embed.add_field(
                name="📚 Version",
                value=f"**Discord.py:** {discord.__version__}\n**Python:** {sys.version.split()[0]}",
                inline=True
            )

            embed.add_field(
                name="⚡ Performance",
                value=f"**Latency:** {round(self.bot.latency * 1000)}ms\n**Cogs Loaded:** {len(self.bot.cogs)}",
                inline=True
            )

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))