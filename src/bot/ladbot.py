"""
Enhanced Ladbot Class - Compatible with existing cogs
"""
import discord
from discord.ext import commands
import logging
from pathlib import Path
import sys
import os
from datetime import datetime
import threading

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

class SimpleCogLoader:
    """Simple cog loader for compatibility"""
    def __init__(self, bot):
        self.bot = bot
        self.loaded_cogs = set()

    async def reload_all_cogs(self):
        """Reload all cogs"""
        reloaded = 0
        failed = 0
        for ext_name in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext_name)
                reloaded += 1
                logger.info(f"✅ Reloaded: {ext_name}")
            except Exception as e:
                failed += 1
                logger.error(f"❌ Failed to reload {ext_name}: {e}")

        logger.info(f"🔄 Reload complete: {reloaded} reloaded, {failed} failed")
        return reloaded, failed

class SimpleDataManager:
    """Simple data manager for compatibility"""
    def __init__(self):
        self.embed_color = 0x00ff00
        self.options = self._get_default_options()

    def _get_default_options(self):
        """Return default options for backward compatibility"""
        return {
            'ping': {'default': True, 'type': 'bool', 'descr': 'Ping command'},
            'help': {'default': True, 'type': 'bool', 'descr': 'Help command'},
            'feedback': {'default': True, 'type': 'bool', 'descr': 'Feedback command'},
            'say': {'default': True, 'type': 'bool', 'descr': 'Say command'},
            'ascii': {'default': True, 'type': 'bool', 'descr': 'ASCII art command'},
            'cmd_8ball': {'default': True, 'type': 'bool', 'descr': '8-ball command'},
            'jokes': {'default': True, 'type': 'bool', 'descr': 'Jokes command'},
            'minesweeper': {'default': True, 'type': 'bool', 'descr': 'Minesweeper game'},
            'autoresponses': {'default': False, 'type': 'bool', 'descr': 'Auto responses'},
        }

class LadBot(commands.Bot):
    """Enhanced Discord bot with compatibility layers"""

    def __init__(self):
        from config.settings import settings

        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        super().__init__(
            command_prefix=settings.BOT_PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

        self.settings = settings

        # Backward compatibility - add the attributes your cogs expect
        self.config = settings  # Many cogs use self.bot.config

        # Create a simple data manager for compatibility
        self.data_manager = SimpleDataManager()

        # Add cog loader for reload commands
        self.cog_loader = SimpleCogLoader(self)

        # Add settings cache for compatibility
        self.settings_cache = {}

        # Add uptime tracking
        self.start_time = datetime.now()

        # Add command usage tracking
        self.commands_used_today = 0

        # Add error tracking
        self.error_count = 0

        # Web server configuration for Render
        self.web_host = '0.0.0.0'
        self.web_port = int(os.environ.get('PORT', 8080))
        self.web_thread = None
        self.web_url = f"https://ladbot-dashboard.onrender.com"

    def get_setting(self, guild_id, setting_name):
        """Get a setting value (compatibility method)"""
        # Check cache first
        if guild_id in self.settings_cache and setting_name in self.settings_cache[guild_id]:
            return self.settings_cache[guild_id][setting_name]

        # Return default values for common settings
        defaults = {
            'autoresponses': False,
            'minesweeper': True,
            'ping': True,
            'help': True,
            'feedback': True,
            'say': True,
            'ascii': True,
            'cmd_8ball': True,
            'jokes': True,
            'weather': True,
            'crypto': True,
            'reddit': True,
            'bible': True,
            'roll': True,
            'games': True,
        }

        return defaults.get(setting_name, True)

    def update_setting(self, guild_id, setting_name, value):
        """Update a setting value (compatibility method)"""
        if guild_id not in self.settings_cache:
            self.settings_cache[guild_id] = {}

        self.settings_cache[guild_id][setting_name] = value
        logger.info(f"Updated setting {setting_name}={value} for guild {guild_id}")

    def get_stats(self):
        """Get bot statistics"""
        # Calculate uptime properly
        uptime_str = "0s"
        if hasattr(self, 'start_time'):
            uptime_delta = datetime.now() - self.start_time
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                uptime_str = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                uptime_str = f"{hours}h {minutes}m"
            elif minutes > 0:
                uptime_str = f"{minutes}m {seconds}s"
            else:
                uptime_str = f"{seconds}s"

        return {
            'cogs': len(self.cogs),
            'commands': len(self.commands),
            'latency': f"{round(self.latency * 1000)}",
            'uptime': uptime_str,
            'guilds': len(self.guilds),
            'users': len(self.users),
            'status': 'online' if self.is_ready() else 'offline'
        }

    def start_web_server(self):
        """Start web dashboard in a separate thread"""
        try:
            logger.info("🌐 Starting web dashboard...")

            # Import Flask components
            from web.app import create_app

            # Create Flask app with bot instance
            app = create_app(self)

            # Start web server in separate thread
            def run_server():
                try:
                    app.run(
                        host=self.web_host,
                        port=self.web_port,
                        debug=False,
                        use_reloader=False,
                        threaded=True
                    )
                except Exception as e:
                    logger.error(f"❌ Web server error: {e}")

            # Start in background thread
            self.web_thread = threading.Thread(target=run_server, daemon=True)
            self.web_thread.start()

            logger.info(f"🌐 Web dashboard started at: {self.web_url}")

        except ImportError as e:
            logger.warning("🌐 Web dashboard disabled - missing dependencies")
            logger.info("Install with: pip install flask flask-cors")
        except Exception as e:
            logger.error(f"❌ Failed to start web server: {e}")

    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("🔧 Setting up bot components...")

        try:
            await self.load_cogs()
            logger.info("✅ Bot setup completed")
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise

    async def load_cogs(self):
        """Load all available cogs"""
        cog_dirs = ["admin", "entertainment", "information", "utility"]
        loaded_count = 0
        failed_count = 0

        for cog_dir in cog_dirs:
            cog_path = Path("src/cogs") / cog_dir

            if cog_path.exists():
                for file_path in cog_path.glob("*.py"):
                    if file_path.name.startswith("_"):
                        continue

                    cog_name = f"cogs.{cog_dir}.{file_path.stem}"
                    try:
                        await self.load_extension(cog_name)
                        self.cog_loader.loaded_cogs.add(cog_name)
                        logger.info(f"✅ Loaded: {cog_name}")
                        loaded_count += 1
                    except Exception as e:
                        logger.error(f"❌ Failed to load {cog_name}: {e}")
                        failed_count += 1

        logger.info(f"🎮 Cog loading: {loaded_count} loaded, {failed_count} failed")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")

        # Set bot status - Updated with new friendly message
        activity = discord.Game(name="🎪 Your entertainment companion")
        await self.change_presence(activity=activity)

        # Start web dashboard
        self.start_web_server()

        # Log startup stats
        total_users = len(self.users)
        total_commands = len(self.commands)
        logger.info(f"📈 Serving {total_users} users with {total_commands} commands")

        # Add startup summary
        stats = self.get_stats()
        logger.info("🎯 Bot Status Summary:")
        logger.info(f"   • Cogs: {stats['cogs']} loaded")
        logger.info(f"   • Commands: {stats['commands']} available")
        logger.info(f"   • Latency: {stats['latency']}ms")
        logger.info(f"   • Web Dashboard: {self.web_url}")
        logger.info("🚀 Ladbot is fully operational!")

    async def on_command(self, ctx):
        """Called when a command is invoked"""
        self.commands_used_today += 1
        logger.info(f"Command '{ctx.command}' used by {ctx.author} in {ctx.guild}")

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        self.error_count += 1

        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        else:
            logger.error(f"Unhandled error in {ctx.command}: {error}")
            await ctx.send("❌ An error occurred while processing that command.")

    async def close(self):
        """Called when bot is shutting down"""
        logger.info("🔄 Bot is shutting down...")

        # Stop web server if running
        if self.web_thread and self.web_thread.is_alive():
            logger.info("🌐 Stopping web dashboard...")

        await super().close()
        logger.info("👋 Bot shutdown complete")