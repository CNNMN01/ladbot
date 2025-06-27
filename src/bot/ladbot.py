"""
Enhanced Ladbot Class - Compatible with existing cogs
"""
import discord
from discord.ext import commands
import logging
from pathlib import Path
import sys
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
            'weather': {'default': True, 'type': 'bool', 'descr': 'Weather command'},
            'crypto': {'default': True, 'type': 'bool', 'descr': 'Crypto command'},
            'reddit': {'default': True, 'type': 'bool', 'descr': 'Reddit command'},
            'bible': {'default': True, 'type': 'bool', 'descr': 'Bible command'},
            'roll': {'default': True, 'type': 'bool', 'descr': 'Dice roll command'},
            'minesweeper': {'default': True, 'type': 'bool', 'descr': 'Minesweeper game'},
            'autoresponses': {'default': False, 'type': 'bool', 'descr': 'Auto-responses feature'},
            'games': {'default': True, 'type': 'bool', 'descr': 'Games commands'},
            'dino': {'default': True, 'type': 'bool', 'descr': 'Dinosaur facts'},
            'knockknock': {'default': True, 'type': 'bool', 'descr': 'Knock-knock jokes'},
            'laugh': {'default': True, 'type': 'bool', 'descr': 'Laugh responses'},
        }

class LadBot(commands.Bot):
    """Enhanced Ladbot with backward compatibility and web dashboard"""

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

        # 🆕 ADD UPTIME TRACKING
        self.start_time = datetime.now()

        # 🆕 ADD COMMAND USAGE TRACKING
        self.commands_used_today = 0

        # 🆕 ADD ERROR TRACKING
        self.error_count = 0

        # 🆕 WEB SERVER THREAD REFERENCE
        self.web_thread = None

    def get_setting(self, guild_id, setting_name):
        """Get a setting value (compatibility method)"""
        # Check cache first
        if guild_id in self.settings_cache and setting_name in self.settings_cache[guild_id]:
            return self.settings_cache[guild_id][setting_name]

        # Return default values for common settings
        defaults = {
            'autoresponses': False,
            'minesweeper': True,
            'cmd_8ball': True,
            'jokes': True,
            'weather': True,
            'crypto': True,
            'reddit': True,
            'bible': True,
            'ping': True,
            'help': True,
            'roll': True,
            'say': True,
            'feedback': True,
            'ascii': True,
            'games': True,
            'dino': True,
            'knockknock': True,
            'laugh': True,
        }
        return defaults.get(setting_name, True)

    async def update_setting(self, guild_id, setting_name, value):
        """Update a setting (compatibility method)"""
        # Store in memory cache
        if guild_id not in self.settings_cache:
            self.settings_cache[guild_id] = {}
        self.settings_cache[guild_id][setting_name] = value
        logger.info(f"Updated setting {setting_name} = {value} for guild {guild_id}")

    def start_web_server(self):
        """Start the web dashboard in a separate thread"""
        try:
            from web.app import run_web_server

            # Get web settings from config
            host = getattr(self.settings, 'WEB_HOST', '0.0.0.0')
            port = int(getattr(self.settings, 'WEB_PORT', 8080))

            # Check if port is available
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex((host if host != '0.0.0.0' else 'localhost', port))
                if result == 0:
                    logger.warning(f"⚠️ Port {port} is already in use. Web server may not start.")

            # Start web server in background thread
            self.web_thread = threading.Thread(
                target=run_web_server,
                args=(self, host, port),
                daemon=True,
                name="WebServer"
            )
            self.web_thread.start()
            logger.info(f"🌐 Web dashboard started at http://{host}:{port}")

            # Add web dashboard info to bot status
            if hasattr(self, 'web_url'):
                self.web_url = f"http://{host}:{port}"
            else:
                self.web_url = f"http://{host}:{port}"

        except ImportError:
            logger.warning("🌐 Web dashboard dependencies not found. Install with: pip install flask flask-cors")
        except Exception as e:
            logger.error(f"❌ Failed to start web server: {e}")
            logger.debug(f"Web server error details: {e.__class__.__name__}: {str(e)}")

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

        # Set bot status
        activity = discord.Game(name=f"{self.settings.BOT_PREFIX}help | v1.0 | {len(self.guilds)} servers")
        await self.change_presence(activity=activity)

        # 🌐 START WEB DASHBOARD
        self.start_web_server()

        # Log startup stats
        total_users = len(self.users)
        total_commands = len(self.commands)
        logger.info(f"📈 Serving {total_users} users with {total_commands} commands")

        # 🆕 ADD STARTUP SUMMARY
        stats = self.get_stats()
        logger.info("🎯 Bot Status Summary:")
        logger.info(f"   • Cogs: {stats['cogs']} loaded")
        logger.info(f"   • Commands: {stats['commands']} available")
        logger.info(f"   • Latency: {stats['latency']}ms")
        logger.info(f"   • Web Dashboard: {getattr(self, 'web_url', 'Not available')}")
        logger.info("🚀 Ladbot is fully operational!")

    async def on_command_completion(self, ctx):
        """Called when a command completes successfully"""
        self.commands_used_today += 1
        logger.debug(f"Command {ctx.command.name} used by {ctx.author} in {ctx.guild}")

    async def on_command_error(self, ctx, error):
        """Basic error handling (enhanced error handler cog provides more)"""
        self.error_count += 1

        # Let the ErrorHandler cog handle most errors
        if hasattr(self, 'get_cog') and self.get_cog('ErrorHandler'):
            return

        # Fallback error handling if ErrorHandler cog isn't loaded
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions.")
        else:
            logger.error(f"Unhandled error in {ctx.command}: {error}")
            await ctx.send("❌ An unexpected error occurred.")

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"📥 Joined new guild: {guild.name} (ID: {guild.id}) with {guild.member_count} members")

        # Set default settings for new guild
        self.settings_cache[guild.id] = {}

        # Try to send a welcome message to the first available channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="👋 Hello! I'm Ladbot",
                    description=f"Thanks for adding me to **{guild.name}**!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="🚀 Getting Started",
                    value=f"Use `{self.command_prefix}help` to see all available commands",
                    inline=False
                )
                embed.add_field(
                    name="⚙️ Settings",
                    value=f"Admins can use `{self.command_prefix}settings` to customize bot behavior",
                    inline=False
                )
                embed.add_field(
                    name="🌐 Web Dashboard",
                    value=f"Visit {getattr(self, 'web_url', 'the web dashboard')} for advanced management",
                    inline=False
                )
                embed.add_field(
                    name="🎮 Features",
                    value="Entertainment, utilities, games, information commands and more!",
                    inline=False
                )
                try:
                    await channel.send(embed=embed)
                    break
                except discord.Forbidden:
                    continue

    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild"""
        logger.info(f"📤 Left guild: {guild.name} (ID: {guild.id})")

        # Clean up settings cache
        if guild.id in self.settings_cache:
            del self.settings_cache[guild.id]

    async def on_message(self, message):
        """Process messages and commands"""
        # Don't respond to bots
        if message.author.bot:
            return

        # Process commands
        await self.process_commands(message)

    def get_uptime(self):
        """Get bot uptime as a formatted string"""
        if hasattr(self, 'start_time'):
            uptime = datetime.now() - self.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m {seconds}s"
        return "Unknown"

    def get_stats(self):
        """Get bot statistics"""
        return {
            'guilds': len(self.guilds),
            'users': len(self.users),
            'commands': len(self.commands),
            'cogs': len(self.cogs),
            'uptime': self.get_uptime(),
            'commands_used': getattr(self, 'commands_used_today', 0),
            'errors': getattr(self, 'error_count', 0),
            'latency': round(self.latency * 1000),
            'web_url': getattr(self, 'web_url', None),
            'status': 'Online' if self.is_ready() else 'Offline',
            'start_time': self.start_time.isoformat() if hasattr(self, 'start_time') else None
        }

    async def close(self):
        """Clean shutdown of bot and web server"""
        logger.info("🛑 Shutting down Ladbot...")

        # Log final stats
        if hasattr(self, 'start_time'):
            uptime = datetime.now() - self.start_time
            logger.info(f"📊 Final uptime: {self.get_uptime()}")
            logger.info(f"📈 Commands processed: {getattr(self, 'commands_used_today', 0)}")
            logger.info(f"❌ Errors encountered: {getattr(self, 'error_count', 0)}")

        # Close Discord connection
        await super().close()

        # Web server thread will automatically close since it's daemonic
        if hasattr(self, 'web_thread') and self.web_thread and self.web_thread.is_alive():
            logger.info("🌐 Web server will shut down automatically")

        logger.info("👋 Ladbot shutdown complete")

    def get_web_dashboard_url(self):
        """Get the web dashboard URL"""
        return getattr(self, 'web_url', 'Not available')

    def is_web_server_running(self):
        """Check if web server is running"""
        return hasattr(self, 'web_thread') and self.web_thread and self.web_thread.is_alive()