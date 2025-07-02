"""
ENHANCED LADBOT DISCORD BOT CLASS
Production-ready Discord bot with comprehensive web dashboard integration,
real-time analytics, and advanced error handling
"""

import asyncio
import logging
import threading
import json
import psutil
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict, deque
from typing import Dict, Any, Optional, List, Union

import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)


class LadBot(commands.Bot):
    """Enhanced Ladbot with comprehensive web integration and analytics"""

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

        # ===== DATA MANAGEMENT =====
        self.data_manager = self._create_data_manager()
        self.cog_loader = self._create_cog_loader()

        # Settings cache for performance
        self.settings_cache = {}
        self.guild_settings = {}  # Compatibility alias

        # Recent activity tracking
        self.recent_activity = deque(maxlen=100)

        logger.info("🔧 Enhanced Ladbot initialized with web integration")

    def _create_data_manager(self):
        """Create a comprehensive data manager for web integration"""

        class EnhancedDataManager:
            def __init__(self, settings, bot_instance):
                self.settings = settings
                self.bot = bot_instance
                self.data_dir = Path("data")
                self.data_dir.mkdir(exist_ok=True)

                # Create subdirectories
                (self.data_dir / "analytics").mkdir(exist_ok=True)
                (self.data_dir / "guild_settings").mkdir(exist_ok=True)
                (self.data_dir / "backups").mkdir(exist_ok=True)

                self.last_cache_clear = datetime.now()

                logger.info("📊 Data manager initialized")

            def get_guild_setting(self, guild_id: int, setting_name: str, default=True):
                """Get a guild-specific setting"""
                try:
                    settings_file = self.data_dir / "guild_settings" / f"{guild_id}.json"

                    if settings_file.exists():
                        with open(settings_file, 'r') as f:
                            guild_settings = json.load(f)
                            return guild_settings.get(setting_name, default)

                    return default

                except Exception as e:
                    logger.error(f"Error getting guild setting {setting_name} for {guild_id}: {e}")
                    return default

            def set_guild_setting(self, guild_id: int, setting_name: str, value):
                """Set a guild-specific setting"""
                try:
                    settings_file = self.data_dir / "guild_settings" / f"{guild_id}.json"

                    # Load existing settings
                    guild_settings = {}
                    if settings_file.exists():
                        with open(settings_file, 'r') as f:
                            guild_settings = json.load(f)

                    # Update setting
                    guild_settings[setting_name] = value
                    guild_settings['last_updated'] = datetime.now().isoformat()

                    # Save settings
                    with open(settings_file, 'w') as f:
                        json.dump(guild_settings, f, indent=2)

                    # Update cache
                    cache_key = f"{guild_id}_{setting_name}"
                    self.bot.settings_cache[cache_key] = value

                    logger.debug(f"Updated guild setting {setting_name} for {guild_id}")
                    return True

                except Exception as e:
                    logger.error(f"Error setting guild setting {setting_name} for {guild_id}: {e}")
                    return False

            def get_all_guild_settings(self, guild_id: int):
                """Get all settings for a guild"""
                try:
                    settings_file = self.data_dir / "guild_settings" / f"{guild_id}.json"

                    if settings_file.exists():
                        with open(settings_file, 'r') as f:
                            return json.load(f)

                    return {}

                except Exception as e:
                    logger.error(f"Error getting all guild settings for {guild_id}: {e}")
                    return {}

            def save_analytics_data(self, data: Dict[str, Any]):
                """Save analytics data to file"""
                try:
                    analytics_file = self.data_dir / "analytics" / "bot_analytics.json"
                    data['last_updated'] = datetime.now().isoformat()

                    with open(analytics_file, 'w') as f:
                        json.dump(data, f, indent=2)

                    return True

                except Exception as e:
                    logger.error(f"Error saving analytics data: {e}")
                    return False

            def get_analytics_data(self):
                """Get analytics data from file"""
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
                        'guild_settings': {},
                        'analytics': self.get_analytics_data(),
                        'command_usage': dict(self.bot.command_usage)
                    }

                    # Backup all guild settings
                    guild_settings_dir = self.data_dir / "guild_settings"
                    if guild_settings_dir.exists():
                        for settings_file in guild_settings_dir.glob("*.json"):
                            guild_id = settings_file.stem
                            with open(settings_file, 'r') as f:
                                backup_data['guild_settings'][guild_id] = json.load(f)

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

    # ===== COMPATIBILITY METHODS =====

    def get_setting(self, guild_id: int, setting_name: str, default=True):
        """Get a guild-specific setting (compatibility method)"""
        return self.data_manager.get_guild_setting(guild_id, setting_name, default)

    def set_setting(self, guild_id: int, setting_name: str, value):
        """Set a guild-specific setting (compatibility method)"""
        success = self.data_manager.set_guild_setting(guild_id, setting_name, value)
        if success:
            self.dispatch('setting_updated', guild_id, setting_name, value)
        return success

    def get_guild_setting(self, guild_id: int, setting_name: str, default=True):
        """Alternative method name for compatibility"""
        return self.get_setting(guild_id, setting_name, default)

    def set_guild_setting(self, guild_id: int, setting_name: str, value):
        """Alternative method name for compatibility"""
        return self.set_setting(guild_id, setting_name, value)

    @property
    def prefix(self):
        """Bot prefix for compatibility"""
        return self.command_prefix

    def _get_setting_safe(self, guild_id: int, setting_name: str, default=True):
        """Helper method for decorators to safely get settings"""
        try:
            return self.get_setting(guild_id, setting_name, default)
        except Exception as e:
            logger.debug(f"Error in _get_setting_safe for {setting_name}: {e}")
            return default

    # ===== BOT LIFECYCLE =====

    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            await self.load_cogs()
            self.start_background_tasks()
            logger.info("🎮 Bot setup completed successfully")
        except Exception as e:
            logger.error(f"❌ Error in setup_hook: {e}")

    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = Path("src/cogs")
        if not cogs_dir.exists():
            cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            logger.warning("⚠️  No cogs directory found")
            return

        loaded = 0
        failed = 0
        failed_cogs = []

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
                            failed_cogs.append((cog_name, str(e)))

        self.loaded_cogs = loaded
        logger.info(f"🎮 Cog loading complete: {loaded} loaded, {failed} failed")

        if failed_cogs:
            logger.warning(f"Failed cogs: {', '.join([name for name, _ in failed_cogs])}")

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

    async def on_ready(self):
        """Called when the bot is ready"""
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
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"📈 Serving {sum(guild.member_count for guild in self.guilds)} users")
        logger.info(f"🎮 {len(self.commands)} commands available")
        logger.info(f"⚡ Current latency: {current_latency}ms")

        # Add to recent activity
        self.add_activity("Bot started", f"Connected to {len(self.guilds)} servers")

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
        self.total_tracked_commands = self.total_commands_used

        # Add to recent activity
        self.add_activity("Command used", f"{ctx.author.name} used {command_name}")

        # Save stats periodically
        if self.session_commands % 10 == 0:
            await self.save_command_stats()

        logger.debug(f"📝 Command tracked: {command_name} by {ctx.author} in {ctx.guild}")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        self.error_count += 1

        # Log the error
        logger.error(f"Command error in {ctx.command}: {error}")

        # Add to recent activity
        self.add_activity("Command error", f"Error in {ctx.command.name}: {type(error).__name__}")

        # Send user-friendly error message
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions for this command")
        else:
            await ctx.send("❌ An unexpected error occurred")
            logger.exception(f"Unhandled command error: {error}")

    async def on_guild_join(self, guild):
        """Handle bot joining a guild"""
        logger.info(f"📥 Joined guild: {guild.name} (ID: {guild.id}) with {guild.member_count} members")
        self.add_activity("Guild joined", f"Joined {guild.name} ({guild.member_count} members)")

    async def on_guild_remove(self, guild):
        """Handle bot leaving a guild"""
        logger.info(f"📤 Left guild: {guild.name} (ID: {guild.id})")
        self.add_activity("Guild left", f"Left {guild.name}")

    # ===== BACKGROUND TASKS =====

    @tasks.loop(seconds=30)
    async def update_stats_task(self):
        """Update bot statistics periodically"""
        try:
            # Update latency history
            current_latency = round(self.latency * 1000)
            self.latency_history.append(current_latency)

            # Calculate average latency
            if self.latency_history:
                self.average_latency = sum(self.latency_history) // len(self.latency_history)

            # Update system stats
            process = psutil.Process()
            memory_info = process.memory_info()
            self.memory_usage = round(memory_info.rss / 1024 / 1024, 2)  # MB
            self.memory_percent = round(process.memory_percent(), 2)
            self.cpu_usage = round(process.cpu_percent(), 2)

            # Update other stats
            self.unique_commands_used = len(self.command_usage)
            self.total_tracked_commands = self.total_commands_used

            # Save analytics data
            analytics_data = {
                'total_guilds': len(self.guilds),
                'total_users': sum(guild.member_count for guild in self.guilds),
                'total_commands': self.total_commands_used,
                'commands_today': self.commands_used_today,
                'session_commands': self.session_commands,
                'unique_commands': self.unique_commands_used,
                'error_count': self.error_count,
                'average_latency': self.average_latency,
                'memory_usage_mb': self.memory_usage,
                'memory_percent': self.memory_percent,
                'cpu_usage': self.cpu_usage,
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'last_updated': datetime.now().isoformat()
            }

            self.data_manager.save_analytics_data(analytics_data)

        except Exception as e:
            logger.error(f"Error in stats update task: {e}")

    @tasks.loop(hours=1)
    async def cleanup_task(self):
        """Periodic cleanup task"""
        try:
            # Clear cache every hour
            if (datetime.now() - self.data_manager.last_cache_clear).seconds > 3600:
                self.data_manager.clear_cache()

            # Create backup every 6 hours
            if self.session_commands > 0 and self.session_commands % 100 == 0:
                self.data_manager.backup_settings()

            # Save command stats
            await self.save_command_stats()

            logger.debug("🧹 Cleanup task completed")

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

    @update_stats_task.before_loop
    async def before_update_stats_task(self):
        """Wait until bot is ready before starting stats task"""
        await self.wait_until_ready()

    @cleanup_task.before_loop
    async def before_cleanup_task(self):
        """Wait until bot is ready before starting cleanup task"""
        await self.wait_until_ready()

    # ===== UTILITY METHODS =====

    def add_activity(self, action: str, details: str):
        """Add an activity to recent activity log"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        self.recent_activity.append(activity)

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics for web dashboard"""
        try:
            uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds

            return {
                'guilds': len(self.guilds),
                'users': sum(guild.member_count for guild in self.guilds),
                'commands': len(self.commands),
                'latency': round(self.latency * 1000),
                'uptime': uptime_str,
                'memory_usage': self.memory_usage,
                'memory_percent': self.memory_percent,
                'cpu_usage': self.cpu_usage,
                'bot_status': 'online' if self.is_ready() else 'offline',
                'loaded_cogs': len(self.cogs),
                'command_usage': dict(self.command_usage),
                'commands_today': self.commands_used_today,
                'total_commands': self.total_commands_used,
                'session_commands': self.session_commands,
                'unique_commands_used': self.unique_commands_used,
                'total_tracked_commands': self.total_tracked_commands,
                'error_count': self.error_count,
                'average_latency': self.average_latency,
                'recent_activity': list(self.recent_activity)[-10:],  # Last 10 activities
                'last_updated': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting comprehensive stats: {e}")
            return {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': '0:00:00', 'bot_status': 'error',
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