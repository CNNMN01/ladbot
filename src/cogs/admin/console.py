"""
Console/logging management commands - SECURED VERSION
"""

import sys

import discord
from discord.ext import commands
from utils.decorators import admin_required
import logging

logger = logging.getLogger(__name__)


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

            # Try multiple ways to get the logs directory
            log_file = None

            # Method 1: Try bot.config.LOGS_DIR (uppercase)
            if hasattr(self.bot.config, 'LOGS_DIR'):
                log_file = self.bot.config.LOGS_DIR / "bot.log"
            # Method 2: Try bot.config.logs_dir (lowercase)
            elif hasattr(self.bot.config, 'logs_dir'):
                log_file = self.bot.config.logs_dir / "bot.log"
            # Method 3: Try bot.data_manager.logs_dir
            elif hasattr(self.bot, 'data_manager') and hasattr(self.bot.data_manager, 'logs_dir'):
                log_file = self.bot.data_manager.logs_dir / "bot.log"
            # Method 4: Default path
            else:
                from pathlib import Path
                log_file = Path("logs/bot.log")

            logger.info(f"Looking for log file at: {log_file}")

            if not log_file.exists():
                embed = discord.Embed(
                    description="❌ No log file found. Logs might be output to console only in production.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🔍 Debug Info",
                    value=f"Checked path: `{log_file}`",
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            # Read last N lines from log file
            with open(log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()

            if not log_lines:
                await ctx.send("❌ Log file is empty.")
                return

            # Get last N lines
            recent_logs = log_lines[-lines:] if len(log_lines) >= lines else log_lines

            # Format for Discord and filter sensitive info
            log_text = ""
            for line in recent_logs:
                # Remove potentially sensitive information
                filtered_line = line.strip()

                # Filter out sensitive data
                sensitive_keywords = ['token', 'password', 'secret', 'key', 'api_key']
                if any(keyword in filtered_line.lower() for keyword in sensitive_keywords):
                    # Keep timestamp and level, filter the message
                    parts = filtered_line.split(' - ')
                    if len(parts) >= 3:
                        filtered_line = f"{parts[0]} - {parts[1]} - [SENSITIVE DATA FILTERED]"
                    else:
                        filtered_line = "[SENSITIVE DATA FILTERED]"

                log_text += filtered_line + "\n"

            # Truncate if too long for Discord
            if len(log_text) > 1900:
                log_text = "...\n" + log_text[-1900:]

            embed = discord.Embed(
                title=f"📋 Recent Logs ({len(recent_logs)} lines)",
                description=f"```\n{log_text}\n```",
                color=0x00ff00
            )

            embed.add_field(
                name="📁 Log File",
                value=f"`{log_file}`",
                inline=True
            )

            embed.add_field(
                name="📊 Total Lines",
                value=f"{len(log_lines):,}",
                inline=True
            )

            embed.add_field(
                name="🔒 Security",
                value="Sensitive data filtered",
                inline=True
            )

            embed.set_footer(text=f"Requested by Admin: {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except FileNotFoundError:
            await ctx.send("❌ Log file not found. Logs might be output to console only.")
        except PermissionError:
            await ctx.send("❌ Permission denied reading log file.")
        except Exception as e:
            logger.error(f"Error in logs command: {e}")
            await ctx.send(f"❌ Error reading logs: {e}")

    @commands.command()
    @admin_required()
    async def clearlogs(self, ctx):
        """Clear the bot log file (Admin Only)"""
        try:
            # Get log file path
            log_file = None

            if hasattr(self.bot.config, 'LOGS_DIR'):
                log_file = self.bot.config.LOGS_DIR / "bot.log"
            elif hasattr(self.bot.config, 'logs_dir'):
                log_file = self.bot.config.logs_dir / "bot.log"
            elif hasattr(self.bot, 'data_manager') and hasattr(self.bot.data_manager, 'logs_dir'):
                log_file = self.bot.data_manager.logs_dir / "bot.log"
            else:
                from pathlib import Path
                log_file = Path("logs/bot.log")

            if not log_file.exists():
                await ctx.send("❌ No log file found to clear.")
                return

            # Backup current logs before clearing
            backup_content = ""
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                backup_content = f"Log cleared by {ctx.author} at {datetime.now()}\n"
                backup_content += f"Previous log had {len(lines)} lines\n"
                backup_content += "=" * 50 + "\n"

            # Clear the log file but add a clear message
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(backup_content)

            embed = discord.Embed(
                title="🗑️ Logs Cleared",
                description=f"Successfully cleared log file.\nPrevious log had {len(lines):,} lines.",
                color=0x00ff00
            )

            embed.add_field(
                name="📁 File",
                value=f"`{log_file}`",
                inline=True
            )

            embed.add_field(
                name="👤 Cleared by",
                value=ctx.author.mention,
                inline=True
            )

            embed.set_footer(text="New logs will continue to be written to this file")
            await ctx.send(embed=embed)

            logger.info(f"Log file cleared by admin {ctx.author} ({ctx.author.id})")

        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            await ctx.send(f"❌ Error clearing logs: {e}")

    @commands.command()
    @admin_required()
    async def console(self, ctx, *, command: str = None):
        """Execute Python code for debugging (Admin Only)"""
        if not command:
            embed = discord.Embed(
                title="💻 Console Command",
                description="Execute Python code for debugging.\n\n**⚠️ WARNING: This is dangerous in production!**",
                color=0xffaa00
            )

            embed.add_field(
                name="📝 Usage",
                value=f"`{ctx.prefix}console <python_code>`",
                inline=False
            )

            embed.add_field(
                name="🔍 Examples",
                value=f"`{ctx.prefix}console len(bot.guilds)`\n`{ctx.prefix}console bot.user.name`\n`{ctx.prefix}console print('Hello')`",
                inline=False
            )

            embed.add_field(
                name="🔒 Security",
                value="Only bot admins can use this command",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        try:
            # Create safe execution environment
            env = {
                'bot': self.bot,
                'ctx': ctx,
                'discord': discord,
                'commands': commands,
                'logger': logger,
                '__builtins__': __builtins__
            }

            # Execute the command
            result = eval(command, env)

            # Handle async results
            if hasattr(result, '__await__'):
                result = await result

            # Format result
            if result is None:
                result_str = "None"
            else:
                result_str = str(result)

            # Truncate if too long
            if len(result_str) > 1900:
                result_str = result_str[:1900] + "..."

            embed = discord.Embed(
                title="💻 Console Output",
                color=0x00ff00
            )

            embed.add_field(
                name="📝 Command",
                value=f"```python\n{command}\n```",
                inline=False
            )

            embed.add_field(
                name="📤 Result",
                value=f"```python\n{result_str}\n```",
                inline=False
            )

            embed.set_footer(text=f"Executed by {ctx.author.display_name}")
            await ctx.send(embed=embed)

            # Log the console usage
            logger.warning(f"Console command executed by {ctx.author} ({ctx.author.id}): {command}")

        except Exception as e:
            embed = discord.Embed(
                title="❌ Console Error",
                color=0xff0000
            )

            embed.add_field(
                name="📝 Command",
                value=f"```python\n{command}\n```",
                inline=False
            )

            embed.add_field(
                name="💥 Error",
                value=f"```python\n{str(e)}\n```",
                inline=False
            )

            await ctx.send(embed=embed)
            logger.error(f"Console command error for {ctx.author}: {e}")


async def setup(bot):
    await bot.add_cog(Console(bot))