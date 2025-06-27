"""
Enhanced Global Error Handler for Ladbot
"""

import discord
from discord.ext import commands
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorHandler(commands.Cog):
    """Enhanced error handling with detailed logging"""

    def __init__(self, bot):
        self.bot = bot
        self.error_channel_id = None  # Set this to log errors to a specific channel

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for all commands"""

        # Track error
        if hasattr(self.bot, 'error_count'):
            self.bot.error_count += 1

        # Ignore these errors
        if isinstance(error, (commands.CommandNotFound, commands.DisabledCommand)):
            return

        # Handle specific error types
        if isinstance(error, commands.CheckFailure):
            # Permission errors - user friendly message
            embed = discord.Embed(
                title="🚫 Permission Denied",
                description=str(error),
                color=0xff4444
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❓ Missing Argument",
                description=f"Missing required argument: `{error.param.name}`\n\nUse `{ctx.prefix}help {ctx.command}` for usage info.",
                color=0xffaa00
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Argument",
                description=f"Invalid argument provided.\n\nUse `{ctx.prefix}help {ctx.command}` for usage info.",
                color=0xffaa00
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown",
                description=f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                color=0xffaa00
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="🚫 Missing Permissions",
                description="You don't have the required permissions to use this command.",
                color=0xff4444
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        # Handle unexpected errors
        error_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Log the full error
        logger.error(f"Unhandled error (ID: {error_id}) in command {ctx.command}: {error}")
        logger.error(f"Error details: {traceback.format_exc()}")

        # Send user-friendly error message
        embed = discord.Embed(
            title="💥 Unexpected Error",
            description=f"An unexpected error occurred while executing this command.\n\n**Error ID:** `{error_id}`\n\nThis error has been logged for investigation.",
            color=0xff4444
        )
        embed.set_footer(text="If this keeps happening, please contact an administrator.")

        try:
            await ctx.send(embed=embed)
        except:
            # Fallback to plain text if embed fails
            await ctx.send(f"❌ An unexpected error occurred (ID: {error_id}). This has been logged.")

        # Send detailed error to error channel if configured
        if self.error_channel_id:
            try:
                error_channel = self.bot.get_channel(self.error_channel_id)
                if error_channel:
                    error_embed = discord.Embed(
                        title=f"Error Report - {error_id}",
                        color=0xff0000
                    )
                    error_embed.add_field(name="Command", value=str(ctx.command), inline=True)
                    error_embed.add_field(name="User", value=f"{ctx.author} ({ctx.author.id})", inline=True)
                    error_embed.add_field(name="Guild", value=f"{ctx.guild} ({ctx.guild.id})" if ctx.guild else "DM", inline=True)
                    error_embed.add_field(name="Error", value=f"```{str(error)[:1000]}```", inline=False)

                    if len(str(error)) > 1000:
                        error_embed.add_field(name="Full Traceback", value="Check logs for full details", inline=False)

                    await error_channel.send(embed=error_embed)
            except Exception as e:
                logger.error(f"Failed to send error to error channel: {e}")


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))