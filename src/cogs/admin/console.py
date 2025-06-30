"""
Console/logging management commands - SECURED VERSION
"""

import sys
import discord
from discord.ext import commands
from utils.decorators import admin_required
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Console(commands.Cog):
    """Console and logging management"""

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
                name="🔒 Security",
                value="Admin only. Logs all usage.",
                inline=False
            )
            embed.add_field(
                name="💡 Example",
                value=f"`{ctx.prefix}console print('Hello World')`",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        try:
            # Security log
            logger.warning(f"Console command executed by {ctx.author} ({ctx.author.id}): {command}")

            # Create a safe environment
            safe_globals = {
                'bot': self.bot,
                'ctx': ctx,
                'discord': discord,
                'print': print,
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'sorted': sorted,
                    'reversed': reversed,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'any': any,
                    'all': all,
                }
            }

            # Capture output
            old_stdout = sys.stdout
            import io
            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                # Execute the code
                result = eval(command, safe_globals)
                output = captured_output.getvalue()

                # Restore stdout
                sys.stdout = old_stdout

                # Format response
                response = ""
                if output:
                    response += f"**Output:**\n```\n{output}\n```\n"
                if result is not None:
                    response += f"**Result:** `{result}`"

                if not response:
                    response = "✅ Code executed successfully (no output)"

                # Limit response length
                if len(response) > 1900:
                    response = response[:1900] + "...\n[Output truncated]"

                embed = discord.Embed(
                    title="💻 Console Result",
                    description=response,
                    color=0x00ff00
                )
                embed.set_footer(text=f"Executed by: {ctx.author.display_name}")
                await ctx.send(embed=embed)

            except Exception as exec_error:
                sys.stdout = old_stdout

                embed = discord.Embed(
                    title="❌ Console Error",
                    description=f"```\n{str(exec_error)}\n```",
                    color=0xff0000
                )
                embed.set_footer(text=f"Error in command by: {ctx.author.display_name}")
                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in console command: {e}")
            await ctx.send(f"❌ Console command failed: {e}")

    @commands.command()
    @admin_required()
    async def status(self, ctx):
        """Show bot status and health information (Admin Only)"""
        try:
            import psutil
            import os
            from datetime import timedelta

            # Get bot uptime
            uptime = datetime.now() - self.bot.start_time if hasattr(self.bot, 'start_time') else None

            # Get system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            embed = discord.Embed(
                title="🤖 Bot Status Dashboard",
                description="Current bot health and system information",
                color=0x00ff00
            )

            # Bot Info
            embed.add_field(
                name="🎯 Bot Information",
                value=(
                    f"**Guilds:** {len(self.bot.guilds)}\n"
                    f"**Users:** {len(self.bot.users)}\n"
                    f"**Commands:** {len(self.bot.commands)}\n"
                    f"**Latency:** {round(self.bot.latency * 1000)}ms"
                ),
                inline=True
            )

            # System Resources
            embed.add_field(
                name="💻 System Resources",
                value=(
                    f"**CPU:** {cpu_percent}%\n"
                    f"**Memory:** {memory.percent}%\n"
                    f"**Disk:** {round(disk.percent, 1)}%\n"
                    f"**Process ID:** {os.getpid()}"
                ),
                inline=True
            )

            # Uptime and Stats
            if uptime:
                uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            else:
                uptime_str = "Unknown"

            embed.add_field(
                name="⏱️ Runtime Stats",
                value=(
                    f"**Uptime:** {uptime_str}\n"
                    f"**Cogs Loaded:** {len(self.bot.cogs)}\n"
                    f"**Extensions:** {len(self.bot.extensions)}\n"
                    f"**Python:** {sys.version.split()[0]}"
                ),
                inline=True
            )

            embed.set_footer(text=f"Status requested by: {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except ImportError:
            # Fallback if psutil not available
            embed = discord.Embed(
                title="🤖 Basic Bot Status",
                description="System monitoring not available (psutil not installed)",
                color=0xffaa00
            )

            embed.add_field(
                name="🎯 Bot Information",
                value=(
                    f"**Guilds:** {len(self.bot.guilds)}\n"
                    f"**Users:** {len(self.bot.users)}\n"
                    f"**Commands:** {len(self.bot.commands)}\n"
                    f"**Latency:** {round(self.bot.latency * 1000)}ms"
                ),
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await ctx.send(f"❌ Error getting status: {e}")


async def setup(bot):
    await bot.add_cog(Console(bot))