"""
Enhanced error handling for the bot
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from discord.ext import commands
import logging
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler(commands.Cog):
    """Enhanced error handling system"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for all commands"""

        # Ignore command not found errors (reduces spam)
        if isinstance(error, commands.CommandNotFound):
            return

        # Handle different types of errors
        if isinstance(error, commands.CheckFailure):
            # Admin permission errors are handled by decorators
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Argument",
                description=f"Missing required argument: `{error.param.name}`",
                color=0xff0000
            )
            embed.add_field(
                name="Usage",
                value=f"`{ctx.prefix}help {ctx.command.name}` for more info",
                inline=False
            )
            await ctx.send(embed=embed)

        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Argument",
                description=str(error),
                color=0xff0000
            )
            embed.add_field(
                name="Usage",
                value=f"`{ctx.prefix}help {ctx.command.name}` for more info",
                inline=False
            )
            await ctx.send(embed=embed)

        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown",
                description=f"Please wait **{error.retry_after:.1f}** seconds before using this command again.",
                color=0xff9900
            )
            await ctx.send(embed=embed)

        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="🔒 Missing Permissions",
                description="You don't have the required Discord permissions for this command.",
                color=0xff0000
            )
            missing_perms = ", ".join(error.missing_permissions)
            embed.add_field(name="Required Permissions", value=missing_perms, inline=False)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="🤖 Bot Missing Permissions",
                description="I don't have the required permissions to execute this command.",
                color=0xff0000
            )
            missing_perms = ", ".join(error.missing_permissions)
            embed.add_field(name="Missing Permissions", value=missing_perms, inline=False)
            await ctx.send(embed=embed)

        elif isinstance(error, discord.Forbidden):
            embed = discord.Embed(
                title="🚫 Access Forbidden",
                description="I don't have permission to perform that action.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

        else:
            # Log unexpected errors
            logger.error(f"Unhandled error in {ctx.command}: {error}")
            logger.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))

            embed = discord.Embed(
                title="💥 Unexpected Error",
                description="An unexpected error occurred. The error has been logged.",
                color=0xff0000
            )
            embed.add_field(
                name="Error Type",
                value=type(error).__name__,
                inline=True
            )
            if len(str(error)) < 1000:
                embed.add_field(
                    name="Error Details",
                    value=f"```{str(error)}```",
                    inline=False
                )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """Handle non-command errors"""
        logger.error(f"Error in event {event}: {args}, {kwargs}")
        # Don't crash the bot on errors

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testerror(self, ctx, error_type: str = "generic"):
        """Test error handling (Admin Only)"""
        embed = discord.Embed(
            title="🧪 Testing Error Handler",
            description=f"Testing error type: `{error_type}`",
            color=0xff9900
        )
        await ctx.send(embed=embed)

        # Generate different test errors
        if error_type == "missing_arg":
            raise commands.MissingRequiredArgument(ctx.command.params['error_type'])
        elif error_type == "bad_arg":
            raise commands.BadArgument("This is a test bad argument error")
        elif error_type == "forbidden":
            raise discord.Forbidden(discord.HTTPException(), "Test forbidden error")
        elif error_type == "generic":
            raise Exception("This is a test generic error")
        else:
            await ctx.send(f"❌ Unknown error type: `{error_type}`\nTry: missing_arg, bad_arg, forbidden, generic")


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))