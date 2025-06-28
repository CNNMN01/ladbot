"""
Enhanced Ladbot Discord Bot Class with Full Web Dashboard Support
"""
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class LadBot(commands.Bot):
    """Enhanced Ladbot with web dashboard integration"""

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

        # Statistics tracking - Initialize immediately
        self.start_time = None  # Will be set in on_ready
        self.commands_used_today = 0
        self.total_commands_used = 0
        self.error_count = 0
        self.session_commands = 0

        # Performance tracking
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
        """Called when the bot is ready - Enhanced with full tracking"""
        # Set start time for uptime calculation
        self.start_time = datetime.now()

        # Initialize all tracking variables
        if not hasattr(self, 'commands_used_today'):
            self.commands_used_today = 0
        if not hasattr(self, 'total_commands_used'):
            self.total_commands_used = 0
        if not hasattr(self, 'error_count'):
            self.error_count = 0
        if not hasattr(self, 'session_commands'):
            self.session_commands = 0

        # Initialize latency tracking
        self.latency_history = [round(self.latency * 1000)]

        # Log comprehensive startup info
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"👥 Serving {len(self.users)} users")
        logger.info(f"🎮 Loaded {len(self.cogs)} cogs")
        logger.info(f"🔧 {len(self.commands)} commands available")
        logger.info(f"🕐 Start time recorded: {self.start_time}")
        logger.info(f"📡 Initial latency: {round(self.latency * 1000)}ms")

        # Set activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def on_command_completion(self, ctx):
        """Track completed commands for dashboard stats"""
        try:
            self.commands_used_today += 1
            self.total_commands_used += 1
            self.session_commands += 1

            # Update latency history (keep last 10 readings)
            current_latency = round(self.latency * 1000)
            self.latency_history.append(current_latency)
            if len(self.latency_history) > 10:
                self.latency_history.pop(0)

            logger.debug(f"Command {ctx.command.name} completed. Session: {self.session_commands}, Today: {self.commands_used_today}")

        except Exception as e:
            logger.error(f"Error tracking command completion: {e}")

    async def on_command_error(self, ctx, error):
        """Track command errors for dashboard monitoring"""
        try:
            self.error_count += 1

            # Log different error types appropriately
            if isinstance(error, commands.CommandNotFound):
                logger.debug(f"Command not found: {ctx.message.content}")
            elif isinstance(error, commands.MissingPermissions):
                logger.warning(f"Permission error in {ctx.command.name}: {error}")
            elif isinstance(error, commands.CommandOnCooldown):
                logger.debug(f"Cooldown error in {ctx.command.name}: {error}")
            else:
                logger.error(f"Command error in {ctx.command.name}: {error}")

        except Exception as e:
            logger.error(f"Error tracking command error: {e}")

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

    async def close(self):
        """Clean shutdown"""
        logger.info("🔄 Bot shutting down...")

        # Stop web server if running
        if hasattr(self, 'web_thread') and self.web_thread:
            logger.info("🌐 Stopping web server...")

        await super().close()
        logger.info("👋 Bot shutdown complete")