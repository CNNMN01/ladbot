"""
Enhanced Ladbot Discord Bot Class with Real Command Tracking
"""
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime, date
import json
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class LadBot(commands.Bot):
    """Enhanced Ladbot with real command tracking and web dashboard integration"""

    def __init__(self):
        """Initialize the bot with enhanced tracking"""
        # Get settings
        from config.settings import settings
        self.settings = settings

        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # Initialize bot
        super().__init__(
            command_prefix=settings.BOT_PREFIX,
            intents=intents,
            help_command=None
        )

        # Web server configuration
        self.web_port = 8080
        self.web_host = '0.0.0.0'
        self.web_url = None
        self.web_thread = None

        # Real command tracking initialization
        self.command_usage = {}  # {command_name: usage_count}
        self.commands_used_today = 0
        self.total_commands_used = 0
        self.session_commands = 0
        self.error_count = 0
        self.last_reset_date = date.today().isoformat()

        # Performance tracking
        self.start_time = None  # Will be set in on_ready
        self.last_latency_check = datetime.now()
        self.latency_history = []

        logger.info("🔧 Setting up bot components...")

    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            await self.load_cogs()
            logger.info("🎮 All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")

    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = Path("src/cogs")
        if not cogs_dir.exists():
            cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            logger.warning("No cogs directory found")
            return

        loaded = 0
        failed = 0

        # Discover and load cogs
        for category_dir in cogs_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("_"):
                for cog_file in category_dir.glob("*.py"):
                    if cog_file.name != "__init__.py":
                        cog_name = f"cogs.{category_dir.name}.{cog_file.stem}"
                        try:
                            await self.load_extension(cog_name)
                            logger.info(f"✅ Loaded: {cog_name}")
                            loaded += 1
                        except Exception as e:
                            logger.error(f"❌ Failed to load {cog_name}: {e}")
                            failed += 1

        logger.info(f"🎮 Cog loading complete: {loaded} loaded, {failed} failed")

    async def on_ready(self):
        """Called when the bot is ready - Enhanced with real command tracking"""
        # Set start time for uptime calculation
        self.start_time = datetime.now()

        # Load command statistics from persistent storage
        await self.load_command_stats()

        # Initialize latency tracking
        self.latency_history = [round(self.latency * 1000)]

        # Log comprehensive startup info
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"👥 Serving {len(self.users)} users")
        logger.info(f"🎮 Loaded {len(self.cogs)} cogs")
        logger.info(f"🔧 {len(self.commands)} commands available")
        logger.info(f"📈 Command stats: {self.total_commands_used} total, {self.commands_used_today} today")
        logger.info(f"📊 Unique commands used: {len(self.command_usage)}")
        logger.info(f"🕐 Start time recorded: {self.start_time}")
        logger.info(f"📡 Initial latency: {round(self.latency * 1000)}ms")

        # Set activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def load_command_stats(self):
        """Load command statistics from persistent storage"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            stats_file = data_dir / "command_stats.json"

            if not stats_file.exists():
                # Initialize empty stats
                self.command_usage = {}
                self.commands_used_today = 0
                self.total_commands_used = 0
                self.session_commands = 0
                self.error_count = 0
                self.last_reset_date = date.today().isoformat()
                logger.info("📊 No existing command stats found, starting fresh")
                await self.save_command_stats()  # Create initial file
                return

            # Load existing stats
            with open(stats_file, 'r') as f:
                stats_data = json.load(f)

            self.command_usage = stats_data.get('command_usage', {})
            self.total_commands_used = stats_data.get('total_commands_used', 0)
            self.error_count = stats_data.get('error_count', 0)
            self.session_commands = 0  # Always start session at 0

            # Check if we need to reset daily stats
            last_reset = stats_data.get('last_reset_date', date.today().isoformat())
            today = date.today().isoformat()

            if last_reset != today:
                # New day - reset daily counter
                self.commands_used_today = 0
                self.last_reset_date = today
                logger.info("🗓️ New day detected, reset daily command counter")
                await self.save_command_stats()  # Save the reset
            else:
                self.commands_used_today = stats_data.get('commands_used_today', 0)
                self.last_reset_date = last_reset

            logger.info(f"📊 Loaded command stats: {len(self.command_usage)} unique commands, {self.total_commands_used} total uses")

        except Exception as e:
            logger.error(f"❌ Error loading command stats: {e}")
            # Initialize empty stats on error
            self.command_usage = {}
            self.commands_used_today = 0
            self.total_commands_used = 0
            self.session_commands = 0
            self.error_count = 0
            self.last_reset_date = date.today().isoformat()

    async def save_command_stats(self):
        """Save command statistics to persistent storage"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            stats_file = data_dir / "command_stats.json"

            # Prepare data to save
            stats_data = {
                'command_usage': self.command_usage,
                'commands_used_today': self.commands_used_today,
                'total_commands_used': self.total_commands_used,
                'error_count': self.error_count,
                'last_updated': datetime.now().isoformat(),
                'last_reset_date': self.last_reset_date,
                'session_start': self.start_time.isoformat() if self.start_time else None
            }

            # Save to file
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)

            logger.debug(f"💾 Saved command stats: {len(self.command_usage)} commands tracked")

        except Exception as e:
            logger.error(f"❌ Error saving command stats: {e}")

    async def on_command_completion(self, ctx):
        """Track completed commands for real analytics"""
        try:
            # Get command name
            command_name = ctx.command.name if ctx.command else 'unknown'

            # Track the specific command
            self.command_usage[command_name] = self.command_usage.get(command_name, 0) + 1

            # Update counters
            self.commands_used_today += 1
            self.total_commands_used += 1
            self.session_commands += 1

            # Update latency history (keep last 10 readings)
            current_latency = round(self.latency * 1000)
            self.latency_history.append(current_latency)
            if len(self.latency_history) > 10:
                self.latency_history.pop(0)

            # Save to persistent storage (every 5 commands to reduce I/O)
            if self.session_commands % 5 == 0:
                await self.save_command_stats()

            logger.info(f"📈 Command '{command_name}' executed. Session: {self.session_commands}, Today: {self.commands_used_today}, Total: {self.total_commands_used}")

        except Exception as e:
            logger.error(f"❌ Error tracking command completion: {e}")

    async def on_command_error(self, ctx, error):
        """Track command errors for dashboard monitoring"""
        try:
            self.error_count += 1

            # Log different error types appropriately
            if isinstance(error, commands.CommandNotFound):
                logger.debug(f"Command not found: {ctx.message.content}")
            elif isinstance(error, commands.MissingPermissions):
                logger.warning(f"Permission error in {ctx.command.name if ctx.command else 'unknown'}: {error}")
            elif isinstance(error, commands.CommandOnCooldown):
                logger.debug(f"Cooldown error in {ctx.command.name if ctx.command else 'unknown'}: {error}")
            elif isinstance(error, commands.BadArgument):
                logger.debug(f"Bad argument in {ctx.command.name if ctx.command else 'unknown'}: {error}")
            else:
                logger.error(f"Command error in {ctx.command.name if ctx.command else 'unknown'}: {error}")

        except Exception as e:
            logger.error(f"❌ Error tracking command error: {e}")

    async def on_guild_join(self, guild):
        """Log when bot joins a new guild"""
        logger.info(f"📈 Joined new guild: {guild.name} (ID: {guild.id}) - {guild.member_count} members")

        # Update activity status with new guild count
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def on_guild_remove(self, guild):
        """Log when bot leaves a guild"""
        logger.info(f"📉 Left guild: {guild.name} (ID: {guild.id})")

        # Update activity status with new guild count
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def on_message(self, message):
        """Process messages and track stats"""
        # Don't respond to bots
        if message.author.bot:
            return

        # Process commands
        await self.process_commands(message)

    def get_uptime(self):
        """Get formatted uptime string"""
        if not hasattr(self, 'start_time') or not self.start_time:
            return "Unknown"

        try:
            uptime_delta = datetime.now() - self.start_time
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            else:
                return f"{minutes}m {seconds}s"
        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            return "Error"

    def get_average_latency(self):
        """Get average latency from recent readings"""
        try:
            if not hasattr(self, 'latency_history') or not self.latency_history:
                return round(self.latency * 1000)
            return round(sum(self.latency_history) / len(self.latency_history))
        except Exception:
            return round(self.latency * 1000) if hasattr(self, 'latency') else 0

    def get_command_stats_summary(self):
        """Get a summary of command usage statistics"""
        try:
            if not self.command_usage:
                return "No commands used yet"

            total_uses = sum(self.command_usage.values())
            top_command = max(self.command_usage.items(), key=lambda x: x[1])

            return f"{len(self.command_usage)} unique commands, {total_uses} total uses, top: {top_command[0]} ({top_command[1]} uses)"
        except Exception as e:
            logger.error(f"Error getting command stats summary: {e}")
            return "Error getting stats"

    async def reset_daily_stats(self):
        """Reset daily statistics (called at midnight)"""
        try:
            logger.info("🔄 Resetting daily statistics...")
            self.commands_used_today = 0
            self.last_reset_date = date.today().isoformat()
            await self.save_command_stats()
            logger.info("✅ Daily statistics reset complete")
        except Exception as e:
            logger.error(f"❌ Error resetting daily stats: {e}")

    async def close(self):
        """Clean shutdown with stats saving"""
        logger.info("🔄 Bot shutting down...")

        # Save final stats
        try:
            await self.save_command_stats()
            logger.info("💾 Final command stats saved")
        except Exception as e:
            logger.error(f"❌ Error saving final stats: {e}")

        # Stop web server if running
        if hasattr(self, 'web_thread') and self.web_thread:
            logger.info("🌐 Stopping web server...")

        await super().close()
        logger.info("👋 Bot shutdown complete")