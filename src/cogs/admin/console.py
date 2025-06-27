"""
Console/logging management commands - SECURED VERSION
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from discord.ext import commands
from utils.decorators import admin_required


class Console(commands.Cog):
    """Console and logging management - SECURED"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @admin_required()
    async def logs(self, ctx, lines: int = 20):
        """Show recent log entries (Admin Only)"""
        try:
            # Validate input
            if lines > 100:
                await ctx.send("❌ Maximum 100 lines allowed for security reasons.")
                return
            elif lines < 1:
                lines = 20

            # Read last N lines from log file
            log_file = self.bot.config.logs_dir / "bot.log"

            if not log_file.exists():
                await ctx.send("❌ No log file found.")
                return

            with open(log_file, 'r') as f:
                log_lines = f.readlines()

            # Get last N lines
            recent_logs = log_lines[-lines:] if len(log_lines) >= lines else log_lines

            # Format for Discord and filter sensitive info
            log_text = ""
            for line in recent_logs:
                # Remove potentially sensitive information
                filtered_line = line
                # Remove bot tokens, API keys, etc.
                if any(sensitive in line.lower() for sensitive in ['token', 'password', 'secret', 'key']):
                    filtered_line = line.split(':')[0] + ': [SENSITIVE DATA FILTERED]'
                log_text += filtered_line

            # Split if too long
            if len(log_text) > 1900:
                log_text = log_text[-1900:]
                log_text = "...\n" + log_text

            embed = discord.Embed(
                title=f"📋 Recent Logs ({len(recent_logs)} lines)",
                description=f"```\n{log_text}\n```",
                color=0x00ff00
            )

            embed.add_field(
                name="🔒 Security Note",
                value="Sensitive information has been filtered from logs",
                inline=False
            )

            embed.set_footer(text=f"Requested by Admin: {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error reading logs: {e}")

    @commands.command()
    @admin_required()
    async def clearlogs(self, ctx):
        """Clear the bot log file (Admin Only)"""
        try:
            log_file = self.bot.config.logs_dir / "bot.log"

            if not log_file.exists():
                await ctx.send("❌ No log file found to clear.")
                return

            # Confirmation
            embed = discord.Embed(
                title="⚠️ Clear Log File",
                description="This will permanently delete all log entries.\n\nType `CONFIRM CLEAR` to proceed:",
                color=0xffaa00
            )
            await ctx.send(embed=embed)

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                response = await self.bot.wait_for('message', timeout=30.0, check=check)
                if response.content == "CONFIRM CLEAR":
                    # Clear the log file
                    with open(log_file, 'w') as f:
                        f.write("")

                    embed = discord.Embed(
                        title="✅ Logs Cleared",
                        description="Log file has been cleared successfully.",
                        color=0x00ff00
                    )
                    await ctx.send(embed=embed)

                    # Log this action
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Admin {ctx.author} cleared the log file")
                else:
                    await ctx.send("❌ Log clear cancelled.")
            except:
                await ctx.send("❌ Timed out - log clear cancelled.")

        except Exception as e:
            await ctx.send(f"❌ Error clearing logs: {e}")


async def setup(bot):
    await bot.add_cog(Console(bot))