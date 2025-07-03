"""
Enhanced security decorators with comprehensive admin checking and web dashboard integration
"""

import functools
from discord.ext import commands
from typing import Callable
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


def admin_required():
    """Decorator to check if user is admin with detailed logging"""

    async def predicate(ctx):
        # Check Discord server admin permission
        has_server_admin = ctx.author.guild_permissions.administrator if ctx.guild else False

        # Handle different config attribute names safely
        admin_ids = []
        try:
            # Try multiple paths to find admin IDs
            if hasattr(ctx.bot.config, 'admin_ids'):
                admin_ids = ctx.bot.config.admin_ids or []
            elif hasattr(ctx.bot.config, 'ADMIN_IDS'):
                admin_ids = ctx.bot.config.ADMIN_IDS or []
            elif hasattr(ctx.bot, 'settings') and hasattr(ctx.bot.settings, 'ADMIN_IDS'):
                admin_ids = ctx.bot.settings.ADMIN_IDS or []
            elif hasattr(ctx.bot, 'settings') and hasattr(ctx.bot.settings, 'admin_ids'):
                admin_ids = ctx.bot.settings.admin_ids or []
            else:
                logger.warning("Could not find admin_ids in bot configuration")
                admin_ids = []
        except Exception as e:
            logger.warning(f"Error accessing admin_ids: {e}")
            admin_ids = []

        # Check bot admin list
        is_bot_admin = ctx.author.id in admin_ids

        # Bot owner always has access
        is_owner = await ctx.bot.is_owner(ctx.author)

        if not (has_server_admin or is_bot_admin or is_owner):
            logger.warning(f"Admin command access denied for {ctx.author} ({ctx.author.id}) in {ctx.guild}")
            raise commands.CheckFailure("This command requires administrator permissions.")

        # Log admin command usage
        logger.info(f"Admin command {ctx.command} used by {ctx.author} ({ctx.author.id})")
        return True

    return commands.check(predicate)


def owner_only():
    """Decorator for bot owner only commands with logging"""

    async def predicate(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        if not is_owner:
            logger.warning(f"Owner-only command access denied for {ctx.author} ({ctx.author.id})")
            raise commands.CheckFailure("This command requires bot owner permissions.")

        # Log owner command usage
        logger.warning(f"Owner command {ctx.command} used by {ctx.author} ({ctx.author.id})")
        return True

    return commands.check(predicate)


def dangerous_command():
    """Decorator for dangerous commands - requires bot owner with extra logging"""

    async def predicate(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        if not is_owner:
            logger.error(f"DANGEROUS command access denied for {ctx.author} ({ctx.author.id}) - Command: {ctx.command}")
            raise commands.CheckFailure("This is a dangerous command that requires bot owner permissions.")

        # Log dangerous command usage with extra detail
        logger.critical(f"DANGEROUS COMMAND {ctx.command} used by Owner {ctx.author} ({ctx.author.id}) in {ctx.guild}")
        return True

    return commands.check(predicate)


def guild_setting_enabled(setting_name: str):
    """Decorator to check if a guild setting is enabled - SIMPLIFIED VERSION"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            guild_id = ctx.guild.id if ctx.guild else None

            if not guild_id:
                # No guild context, allow command
                return await func(self, ctx, *args, **kwargs)

            try:
                # Import the unified settings service
                from utils.settings_service import settings_service

                # Get setting using the unified service
                setting_enabled = settings_service.get_guild_setting(guild_id, setting_name, True)

                logger.info(
                    f"🔍 COMMAND CHECK: {ctx.command.name} for guild {guild_id} - {setting_name}={setting_enabled}")

                # If disabled, show message and block command
                if not setting_enabled:
                    import discord
                    embed = discord.Embed(
                        title="🚫 Command Disabled",
                        description=f"The `{ctx.command.name}` command has been disabled for this server.",
                        color=0xff9900
                    )
                    embed.add_field(
                        name="Re-enable Command",
                        value=f"`{ctx.prefix}settings {setting_name} on`\nor use the web dashboard",
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    return  # Block the command

                # If enabled, run the command
                return await func(self, ctx, *args, **kwargs)

            except Exception as e:
                logger.error(f"❌ Error checking guild setting {setting_name}: {e}")
                # On error, allow command to run (fail-safe)
                return await func(self, ctx, *args, **kwargs)

        return wrapper

    return decorator


def typing_context():
    """Decorator to show typing indicator during command execution"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            async with ctx.typing():
                return await func(self, ctx, *args, **kwargs)

        return wrapper

    return decorator


def rate_limit(rate: int, per: float):
    """Decorator to add rate limiting to commands"""

    def decorator(func: Callable) -> Callable:
        func.__rate_limit_rate__ = rate
        func.__rate_limit_per__ = per
        return func

    return decorator