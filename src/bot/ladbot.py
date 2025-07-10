"""
ENHANCED LADBOT DISCORD BOT CLASS
Production-ready Discord bot with comprehensive web dashboard integration,
real-time analytics, PostgreSQL database storage, and advanced error handling
"""

import asyncio
import logging
import threading
import json
import psutil
import os
import discord
from pathlib import Path
from utils.database import db_manager
from datetime import datetime, date, timedelta
from collections import defaultdict, deque
from typing import Dict, Any, Optional, List, Union

from discord.ext import commands, tasks

logger = logging.getLogger(__name__)


class LadBot(commands.Bot):
    """Enhanced Ladbot with comprehensive web integration and database storage"""

    def __init__(self):
        """Initialize the bot with enhanced tracking and web integration"""
        # Get settings
        from config.settings import settings
        self.settings = settings

        # Compatibility aliases for existing cogs
        self.config = settings

        # Set up Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.reactions = True
        intents.voice_states = True

        # Initialize bot with settings
        super().__init__(
            command_prefix=settings.BOT_PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True
        )

        # ===== WEB INTEGRATION =====
        self.web_port = 8080
        self.web_host = '0.0.0.0'
        self.web_url = None
        self.web_thread = None

        # ===== ANALYTICS & TRACKING =====
        self.start_time = None
        self.startup_time = datetime.now()

        # Command tracking
        self.command_usage = defaultdict(int)
        self.commands_used_today = 0
        self.total_commands_used = 0
        self.session_commands = 0
        self.unique_commands_used = 0
        self.last_reset_date = date.today().isoformat()
        self.error_count = 0

        # Performance tracking
        self.latency_history = deque(maxlen=60)  # Last 60 measurements
        self.average_latency = 0
        self.last_latency_check = datetime.now()

        # Memory and system tracking
        self.memory_usage = 0
        self.cpu_usage = 0
        self.memory_percent = 0

        # Additional compatibility attributes for web dashboard
        self.loaded_cogs = 0
        self.total_tracked_commands = 0

        # ===== DATABASE INTEGRATION =====
        self.db_manager = None
        self.database_ready = False

        # ===== DATA MANAGEMENT =====
        self.data_manager = self._create_data_manager()  # Keep for analytics/backups
        self.cog_loader = self._create_cog_loader()

        # Settings cache for performance (now database-backed)
        self.settings_cache = {}
        self.guild_settings = {}  # Compatibility alias

        # Recent activity tracking
        self.recent_activity = deque(maxlen=100)

        # Background tasks
        self.update_stats_task = self.update_stats_loop
        self.cleanup_task = self.cleanup_loop

        logger.info("🔧 Enhanced Ladbot initialized with database integration")

    async def setup_hook(self):
        """Called when the bot is starting up - Initialize database and load cogs"""
        try:
            # Initialize database connection
            from utils.database import db_manager
            self.db_manager = db_manager

            logger.info("🗄️ Initializing database connection...")
            db_success = await self.db_manager.initialize()
            if not db_success:
                logger.error("❌ Database initialization failed - bot may not function properly")
            else:
                self.database_ready = True
                logger.info("✅ Database connection established")

            # Load all cogs
            logger.info("🎮 Loading cogs...")
            await self.load_all_cogs()

            # Start background tasks
            self.start_background_tasks()

            logger.info("🎮 Bot setup completed successfully")
        except Exception as e:
            logger.error(f"❌ Error in setup_hook: {e}")

    # ===== GLOBAL COMMAND CHECKING =====

    async def on_command(self, ctx):
        """Global command interceptor - checks database settings for ALL commands"""
        if not ctx.guild:
            return  # Allow DM commands

        if not self.database_ready:
            return  # Allow commands if database not ready

        try:
            # Get the command name
            command_name = ctx.command.name

            # Special commands that should always work (admin/core commands)
            always_allowed = {'help', 'ping', 'settings', 'reload', 'logs', 'console', 'feedback'}

            if command_name in always_allowed:
                return  # Allow these commands always

            # Check if command is enabled in database
            setting_enabled = await self.get_setting(ctx.guild.id, command_name, True)

            if not setting_enabled:
                # Command is disabled - show message and raise an exception to stop execution
                embed = discord.Embed(
                    title="🚫 Command Disabled",
                    description=f"The `{command_name}` command has been disabled for this server.",
                    color=0xff9900
                )
                embed.add_field(
                    name="Re-enable Command",
                    value="Use the web dashboard to enable this command",
                    inline=False
                )
                await ctx.send(embed=embed)

                # ✅ FIXED: Raise an exception instead of disabling the command globally
                from discord.ext.commands import CheckFailure
                raise CheckFailure(f"Command {command_name} is disabled for this server")

            logger.debug(f"✅ Allowed command: {command_name} in guild {ctx.guild.id}")

        except CheckFailure:
            # Re-raise CheckFailure exceptions
            raise
        except Exception as e:
            logger.error(f"Error in global command check: {e}")
            # On error, allow command (fail-safe)

    # ===== SETTINGS METHODS - DATABASE INTEGRATION =====

    async def get_setting(self, guild_id: int, setting_name: str, default=True):
        """Get a guild setting from database - FIXED VERSION"""
        if not self.database_ready or not self.db_manager:
            logger.warning(f"Database not ready, returning default for {setting_name}")
            return default

        try:
            # Force database lookup every time for web dashboard changes
            value = await self.db_manager.get_guild_setting(guild_id, setting_name, default)
            logger.debug(f"🔍 BOT: Got {setting_name}={value} for guild {guild_id} from database")
            return value
        except Exception as e:
            logger.error(f"❌ BOT: Error getting setting {setting_name}: {e}")
            return default

    async def set_setting(self, guild_id: int, setting_name: str, value):
        """Set a guild setting in database - FIXED VERSION"""
        if not self.database_ready or not self.db_manager:
            logger.warning(f"Database not ready, cannot set {setting_name}")
            return False

        try:
            success = await self.db_manager.set_guild_setting(guild_id, setting_name, value)
            if success:
                # Clear any local cache
                cache_key = f"{guild_id}_{setting_name}"
                self.settings_cache.pop(cache_key, None)
                logger.info(f"✅ BOT: Set {setting_name}={value} for guild {guild_id} in database")
            return success
        except Exception as e:
            logger.error(f"❌ BOT: Error setting {setting_name}: {e}")
            return False

    async def get_all_guild_settings(self, guild_id: int):
        """Get all settings for a guild from database"""
        if not self.database_ready or not self.db_manager:
            return {}

        try:
            return await self.db_manager.get_all_guild_settings(guild_id)
        except Exception as e:
            logger.error(f"Error getting all settings for guild {guild_id}: {e}")
            return {}

    def reload_guild_settings(self, guild_id: int):
        """Clear settings cache for a guild (database is always current)"""
        try:
            # Clear cache for this guild
            keys_to_remove = [k for k in self.settings_cache.keys() if k.startswith(f"{guild_id}_")]
            for key in keys_to_remove:
                del self.settings_cache[key]

            logger.info(f"🔄 Cleared settings cache for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache for guild {guild_id}: {e}")
            return False

    # ===== COMPATIBILITY METHODS =====

    def get_guild_setting(self, guild_id: int, setting_name: str, default=True):
        """Sync wrapper for get_setting (for compatibility with sync code)"""
        if not self.database_ready:
            return default
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.get_setting(guild_id, setting_name, default))
        except Exception as e:
            logger.error(f"Error in sync get_guild_setting: {e}")
            return default

    def set_guild_setting(self, guild_id: int, setting_name: str, value):
        """Sync wrapper for set_setting (for compatibility with sync code)"""
        if not self.database_ready:
            return False
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.set_setting(guild_id, setting_name, value))
        except Exception as e:
            logger.error(f"Error in sync set_guild_setting: {e}")
            return False

    @property
    def prefix(self):
        """Bot prefix for compatibility"""
        return self.command_prefix

    # ===== DATA MANAGEMENT =====

    def _create_data_manager(self):
        """Create a data manager for analytics and backups (non-settings data)"""

        class EnhancedDataManager:
            def __init__(self, settings, bot_instance):
                self.settings = settings
                self.bot = bot_instance

                # Force absolute path for Railway/production
                if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RENDER'):
                    self.data_dir = Path("/app/data")
                else:
                    self.data_dir = Path("data")

                self.data_dir.mkdir(exist_ok=True)

                # Create subdirectories
                (self.data_dir / "analytics").mkdir(exist_ok=True)
                (self.data_dir / "backups").mkdir(exist_ok=True)

                self.last_cache_clear = datetime.now()

                logger.info(f"📊 Data manager initialized with path: {self.data_dir}")

            def save_analytics_data(self, data):
                """Save analytics data to file"""
                try:
                    analytics_file = self.data_dir / "analytics" / "bot_analytics.json"
                    with open(analytics_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    return True
                except Exception as e:
                    logger.error(f"Error saving analytics data: {e}")
                    return False

            def get_analytics_data(self):
                """Load analytics data from file"""
                try:
                    analytics_file = self.data_dir / "analytics" / "bot_analytics.json"

                    if analytics_file.exists():
                        with open(analytics_file, 'r') as f:
                            return json.load(f)

                    return {}

                except Exception as e:
                    logger.error(f"Error loading analytics data: {e}")
                    return {}

            def backup_settings(self):
                """Create a backup of all settings"""
                try:
                    backup_dir = self.data_dir / "backups"
                    backup_file = backup_dir / f"settings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

                    backup_data = {
                        'timestamp': datetime.now().isoformat(),
                        'analytics': self.get_analytics_data(),
                        'command_usage': dict(self.bot.command_usage)
                    }

                    with open(backup_file, 'w') as f:
                        json.dump(backup_data, f, indent=2)

                    logger.info(f"📦 Settings backup created: {backup_file}")
                    return backup_file

                except Exception as e:
                    logger.error(f"Error creating settings backup: {e}")
                    return None

            def clear_cache(self):
                """Clear settings cache"""
                self.bot.settings_cache.clear()
                self.last_cache_clear = datetime.now()
                logger.debug("🧹 Settings cache cleared")

        return EnhancedDataManager(self.settings, self)

    def _create_cog_loader(self):
        """Create a cog loader for reload command compatibility"""

        class CogLoader:
            def __init__(self, bot):
                self.bot = bot
                self._loaded_cogs_cache = set()

            @property
            def loaded_cogs(self):
                """Get loaded cog names as a set"""
                return set(self.bot.extensions.keys())

            @loaded_cogs.setter
            def loaded_cogs(self, value):
                """Setter for compatibility"""
                self._loaded_cogs_cache = set(value) if value else set()

            def get_loaded_cogs(self):
                """Get list of loaded cog names"""
                return list(self.bot.extensions.keys())

            def get_failed_cogs(self):
                """Get list of failed cog names"""
                return []  # Placeholder

            async def reload_cog(self, cog_name):
                """Reload a specific cog"""
                try:
                    await self.bot.reload_extension(cog_name)
                    logger.info(f"✅ Reloaded cog: {cog_name}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Error reloading cog {cog_name}: {e}")
                    return False

            async def reload_all_cogs(self):
                """Reload all loaded cogs"""
                cogs_to_reload = list(self.loaded_cogs)
                reloaded_count = 0
                failed_count = 0

                for cog_name in cogs_to_reload:
                    success = await self.reload_cog(cog_name)
                    if success:
                        reloaded_count += 1
                    else:
                        failed_count += 1

                logger.info(f"🔄 Cog reload complete: {reloaded_count} reloaded, {failed_count} failed")
                return reloaded_count, failed_count

            def get_cog_status(self):
                """Get overall cog status"""
                return {
                    'loaded': len(self.bot.extensions),
                    'failed': 0,
                    'total': len(self.bot.extensions)
                }

        return CogLoader(self)

    # ===== COG LOADING - ENHANCED =====

    async def load_all_cogs(self):
        """Load all cogs with comprehensive error handling and multiple directory support"""
        # Try multiple possible cog directory locations
        possible_dirs = [
            Path("src/cogs"),  # New structure in src
            Path("cogs"),  # Standard structure
            Path("Cogs")  # Legacy structure
        ]

        cogs_dir = None
        for dir_path in possible_dirs:
            if dir_path.exists():
                cogs_dir = dir_path
                logger.info(f"📁 Found cogs directory: {cogs_dir}")
                break

        if not cogs_dir:
            logger.error(f"❌ No cogs directory found! Searched: {[str(p) for p in possible_dirs]}")
            return

        loaded = 0
        failed = 0
        failed_cogs = []

        # Check for new structure (subdirectories)
        if any(item.is_dir() and not item.name.startswith("_") for item in cogs_dir.iterdir()):
            # New structure: cogs organized in subdirectories
            logger.info("📂 Using new cog structure (subdirectories)")
            for category_dir in cogs_dir.iterdir():
                if category_dir.is_dir() and not category_dir.name.startswith("_"):
                    for cog_file in category_dir.glob("*.py"):
                        if cog_file.name.startswith("_"):
                            continue

                        # Determine import path based on directory structure
                        if cogs_dir.name == "cogs" and cogs_dir.parent.name == "src":
                            cog_name = f"src.cogs.{category_dir.name}.{cog_file.stem}"
                        else:
                            cog_name = f"cogs.{category_dir.name}.{cog_file.stem}"

                        try:
                            await self.load_extension(cog_name)
                            logger.info(f"✅ Loaded: {cog_name}")
                            loaded += 1
                        except Exception as e:
                            logger.error(f"❌ Failed to load {cog_name}: {e}")
                            failed += 1
                            failed_cogs.append((cog_name, str(e)))

        else:
            # Old structure: all cogs in one directory
            logger.info("📂 Using legacy cog structure (flat directory)")
            for cog_file in cogs_dir.glob("*.py"):
                if cog_file.name.startswith("_"):
                    continue

                # Determine import path
                if cogs_dir.name == "Cogs":
                    cog_name = f"Cogs.{cog_file.stem}"
                elif cogs_dir.name == "cogs" and cogs_dir.parent.name == "src":
                    cog_name = f"src.cogs.{cog_file.stem}"
                else:
                    cog_name = f"cogs.{cog_file.stem}"

                try:
                    await self.load_extension(cog_name)
                    logger.info(f"✅ Loaded: {cog_name}")
                    loaded += 1
                except Exception as e:
                    logger.error(f"❌ Failed to load {cog_name}: {e}")
                    failed += 1
                    failed_cogs.append((cog_name, str(e)))

        self.loaded_cogs = loaded
        logger.info(f"🎮 Cog loading complete: {loaded} loaded, {failed} failed")

        if failed_cogs:
            logger.warning(f"Failed cogs: {', '.join([name for name, _ in failed_cogs])}")

        # Log available commands after loading
        command_count = len([cmd for cmd in self.commands])
        logger.info(f"🎯 {command_count} commands now available")

    def start_background_tasks(self):
        """Start background tasks"""
        try:
            if not self.update_stats_task.is_running():
                self.update_stats_task.start()

            if not self.cleanup_task.is_running():
                self.cleanup_task.start()

            logger.info("📊 Background tasks started")

        except Exception as e:
            logger.error(f"Error starting background tasks: {e}")

    # ===== ACTIVITY TRACKING =====

    def add_activity(self, activity_type: str, description: str):
        """Add an activity to recent activity tracking"""
        self.recent_activity.append({
            'type': activity_type,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'guild_count': len(self.guilds),
            'user_count': len(self.users)
        })

    async def update_system_stats(self):
        """Update system performance statistics"""
        try:
            # Memory usage
            process = psutil.Process()
            self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            self.memory_percent = process.memory_percent()

            # CPU usage
            self.cpu_usage = process.cpu_percent()

            # Latency tracking
            current_latency = round(self.latency * 1000, 2)
            self.latency_history.append(current_latency)
            if self.latency_history:
                self.average_latency = sum(self.latency_history) / len(self.latency_history)

        except Exception as e:
            logger.debug(f"Error updating system stats: {e}")

    # ===== BOT EVENTS =====

    async def on_ready(self):
        """Enhanced on_ready event with comprehensive startup and cog loading"""
        # Set start time for uptime calculation
        self.start_time = datetime.now()

        # Load command statistics from persistent storage
        await self.load_command_stats()

        # Initialize latency tracking
        current_latency = round(self.latency * 1000)
        self.latency_history.append(current_latency)
        self.average_latency = current_latency

        # Update tracking variables
        self.unique_commands_used = len(self.command_usage)
        self.total_tracked_commands = self.total_commands_used

        # Log comprehensive startup info
        logger.info("🎮 ========== LADBOT READY ==========")
        logger.info(f"🤖 Bot: {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"📈 Serving {sum(guild.member_count for guild in self.guilds)} users")
        logger.info(f"🎮 {len(self.commands)} commands available")
        logger.info(f"🔧 {len(self.extensions)} cogs loaded")
        logger.info(f"🗄️ Database ready: {self.database_ready}")
        logger.info(f"⚡ Current latency: {current_latency}ms")

        # Add to recent activity
        self.add_activity("Bot started", f"Connected to {len(self.guilds)} servers with {len(self.commands)} commands")

    async def load_command_stats(self):
        """Load command statistics from file"""
        try:
            stats_file = self.data_manager.data_dir / "analytics" / "command_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                    self.command_usage.update(data.get('command_usage', {}))
                    self.total_commands_used = data.get('total_commands_used', 0)
                    self.commands_used_today = data.get('commands_used_today', 0)
                    self.last_reset_date = data.get('last_reset_date', date.today().isoformat())

                logger.info(f"📊 Loaded command stats: {self.total_commands_used} total commands")

        except Exception as e:
            logger.error(f"Error loading command stats: {e}")

    async def save_command_stats(self):
        """Save command statistics to file"""
        try:
            stats_file = self.data_manager.data_dir / "analytics" / "command_stats.json"
            data = {
                'command_usage': dict(self.command_usage),
                'total_commands_used': self.total_commands_used,
                'commands_used_today': self.commands_used_today,
                'last_reset_date': self.last_reset_date,
                'session_commands': self.session_commands,
                'last_updated': datetime.now().isoformat()
            }

            with open(stats_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving command stats: {e}")

    # ===== EVENT HANDLERS =====

    async def on_command_completion(self, ctx):
        """Track command usage"""
        command_name = ctx.command.name

        # Update command usage
        self.command_usage[command_name] += 1
        self.total_commands_used += 1
        self.commands_used_today += 1
        self.session_commands += 1

        # Check if we need to reset daily stats
        today = date.today().isoformat()
        if self.last_reset_date != today:
            self.commands_used_today = 1
            self.last_reset_date = today
            logger.info("📅 Daily stats reset")

        # Update unique commands count
        self.unique_commands_used = len(self.command_usage)

        # Add to recent activity
        self.add_activity("Command used", f"{ctx.author} used {command_name}")

        logger.debug(f"📈 Command {command_name} used by {ctx.author} in {ctx.guild}")

    async def on_command_error(self, ctx, error):
        """Enhanced error handling with tracking"""
        # Don't show error for disabled commands (we already showed a message)
        if hasattr(ctx.command, 'enabled') and not ctx.command.enabled:
            # Re-enable for next time
            ctx.command.enabled = True
            return

        self.error_count += 1

        # Log the error
        logger.error(f"❌ Command error in {ctx.guild}: {error}")

        # Add to recent activity
        self.add_activity("Command error", f"Error in {ctx.command}: {str(error)[:50]}")

        # Don't send error messages for common errors
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            return

        # Send user-friendly error message
        try:
            embed = discord.Embed(
                title="❌ Command Error",
                description=f"Something went wrong with the `{ctx.command}` command.",
                color=0xff0000
            )
            embed.add_field(
                name="Error Details",
                value=f"```{str(error)[:200]}```",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=10)
        except:
            pass  # Ignore if we can't send error message

    async def on_guild_join(self, guild):
        """Handle bot joining a new guild"""
        logger.info(f"🆕 Joined guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
        self.add_activity("Guild joined", f"Joined {guild.name} ({guild.member_count} members)")

    async def on_guild_remove(self, guild):
        """Handle bot leaving a guild"""
        logger.info(f"👋 Left guild: {guild.name} (ID: {guild.id})")
        self.add_activity("Guild left", f"Left {guild.name}")

    # ===== BACKGROUND TASKS =====

    @tasks.loop(minutes=5)
    async def update_stats_loop(self):
        """Update statistics every 5 minutes"""
        try:
            await self.update_system_stats()
            await self.save_command_stats()

            # Save analytics data
            analytics_data = {
                'timestamp': datetime.now().isoformat(),
                'guilds': len(self.guilds),
                'users': len(self.users),
                'commands_today': self.commands_used_today,
                'total_commands': self.total_commands_used,
                'memory_usage': self.memory_usage,
                'cpu_usage': self.cpu_usage,
                'latency': round(self.latency * 1000, 2),
                'uptime_seconds': (datetime.now() - self.startup_time).total_seconds(),
                'database_ready': self.database_ready
            }

            self.data_manager.save_analytics_data(analytics_data)

        except Exception as e:
            logger.error(f"Error in stats update loop: {e}")

    @update_stats_loop.before_loop
    async def before_update_stats_loop(self):
        """Wait for bot to be ready before starting stats loop"""
        await self.wait_until_ready()

    @tasks.loop(hours=1)
    async def cleanup_loop(self):
        """Cleanup task that runs every hour"""
        try:
            # Clear old cache entries
            self.data_manager.clear_cache()

            # Create backup every 6 hours
            current_hour = datetime.now().hour
            if current_hour % 6 == 0:
                self.data_manager.backup_settings()

        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")

    @cleanup_loop.before_loop
    async def before_cleanup_loop(self):
        """Wait for bot to be ready before starting cleanup loop"""
        await self.wait_until_ready()

    # ===== WEB DASHBOARD INTEGRATION =====

    def get_comprehensive_stats(self):
        """Get comprehensive stats for web dashboard"""
        try:
            uptime = datetime.now() - self.startup_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds

            return {
                'guilds': len(self.guilds),
                'users': len(self.users),
                'commands': len(self.commands),
                'latency': round(self.latency * 1000, 2),
                'uptime': uptime_str,
                'memory_usage': self.memory_usage,
                'cpu_usage': self.cpu_usage,
                'memory_percent': self.memory_percent,
                'commands_used_today': self.commands_used_today,
                'total_commands_used': self.total_commands_used,
                'session_commands': self.session_commands,
                'unique_commands_used': self.unique_commands_used,
                'error_count': self.error_count,
                'bot_status': 'online' if self.is_ready() else 'starting',
                'loaded_cogs': len(self.extensions),
                'average_latency': self.average_latency,
                'database_ready': self.database_ready,
                'recent_activity': list(self.recent_activity)[-10:],  # Last 10 activities
                'last_updated': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting comprehensive stats: {e}")
            return {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': '0:00:00', 'bot_status': 'error',
                'database_ready': False,
                'error_message': str(e)
            }

    async def close(self):
        """Clean shutdown"""
        try:
            logger.info("🛑 Bot shutdown initiated")

            # Stop background tasks
            if hasattr(self, 'update_stats_task'):
                self.update_stats_task.cancel()

            if hasattr(self, 'cleanup_task'):
                self.cleanup_task.cancel()

            # Save final stats
            await self.save_command_stats()

            # Create final backup
            self.data_manager.backup_settings()

            # Close database connections
            if self.db_manager:
                await self.db_manager.close()

            # Add shutdown activity
            self.add_activity("Bot shutdown", "Clean shutdown initiated")

            logger.info("✅ Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")



        finally:

            await super().close()

        # ===== HELPER FUNCTIONS =====

        def setup_bot() -> LadBot:

            """Create and setup the bot instance"""

            try:

                bot = LadBot()

                logger.info("✅ Bot instance created successfully")

                return bot

            except Exception as e:

                logger.error(f"❌ Failed to create bot instance: {e}")

                raise

        if __name__ == "__main__":

            # For testing purposes

            import asyncio

            from config.settings import settings

            async def main():

                bot = setup_bot()

                try:

                    await bot.start(settings.BOT_TOKEN)

                except KeyboardInterrupt:

                    logger.info("Bot stopped by user")

                finally:

                    await bot.close()

            asyncio.run(main())