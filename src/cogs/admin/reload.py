"""
Cog reloading commands for administrators - BULLETPROOF VERSION
"""

import discord
from discord.ext import commands
from utils.decorators import admin_required, owner_only
from utils.embeds import EmbedBuilder
import importlib
import sys
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class Reload(commands.Cog):
    """Cog management commands - BULLETPROOF"""

    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = EmbedBuilder()

    @commands.command()
    @admin_required()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def reload(self, ctx, cog_name: str = None):
        """Reload cogs with proper cache clearing (Admin Only)

        Usage:
        l.reload - Reload all cogs
        l.reload <cog_name> - Reload specific cog
        """
        # CRITICAL: Single execution protection
        if hasattr(ctx.bot, '_reload_in_progress') and ctx.bot._reload_in_progress:
            return await ctx.send("🔄 Reload already in progress, please wait...")

        ctx.bot._reload_in_progress = True

        try:
            if cog_name:
                await self._reload_single_cog(ctx, cog_name)
            else:
                await self._reload_all_cogs(ctx)
        except Exception as e:
            logger.error(f"Unexpected error in reload command: {e}")
            try:
                embed = discord.Embed(
                    title="❌ Reload Error",
                    description=f"An error occurred: {str(e)[:100]}...",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            except:
                await ctx.send("❌ Reload failed with an error.")
        finally:
            ctx.bot._reload_in_progress = False

    async def _reload_single_cog(self, ctx, cog_name: str):
        """Reload a single cog with cache clearing"""
        # Try to find the cog in loaded cogs
        full_cog_name = None
        for loaded_cog in self.bot.cog_loader.loaded_cogs:
            if cog_name.lower() in loaded_cog.lower():
                full_cog_name = loaded_cog
                break

        if not full_cog_name:
            return await ctx.send(f"❌ Cog `{cog_name}` not found in loaded cogs.")

        try:
            # Step 1: Unload the extension
            if full_cog_name in self.bot.extensions:
                await self.bot.unload_extension(full_cog_name)

            # Step 2: Clear and reload Python module
            if full_cog_name in sys.modules:
                importlib.reload(sys.modules[full_cog_name])
                logger.info(f"Cleared cache for module: {full_cog_name}")

            # Step 3: Load the extension again
            await self.bot.load_extension(full_cog_name)

            embed = discord.Embed(
                title="✅ Single Cog Reloaded",
                description=f"Successfully reloaded `{full_cog_name}` with cache clearing",
                color=0x00ff00
            )
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to reload {full_cog_name}: {e}")
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Failed to reload `{full_cog_name}`: {str(e)[:100]}...",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    async def _reload_all_cogs(self, ctx):
        """Reload all cogs with progress updates and cache clearing"""
        embed = discord.Embed(
            title="🔄 Reloading All Cogs",
            description="Clearing Python cache and reloading extensions...",
            color=0x00ff00
        )

        message = None
        try:
            message = await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send initial reload message: {e}")
            # Fallback to simple message
            await ctx.send("🔄 Reloading all cogs...")

        # Step 1: Clear all cog modules from Python cache
        cog_modules = [name for name in sys.modules.keys() if name.startswith('cogs.')]
        cleared_modules = 0

        for module_name in cog_modules:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    cleared_modules += 1
            except Exception as e:
                logger.warning(f"Could not clear cache for {module_name}: {e}")

        logger.info(f"Admin {ctx.author} cleared cache for {cleared_modules} cog modules")

        # Step 2: Reload all extensions
        cogs_to_reload = list(self.bot.cog_loader.loaded_cogs)
        total_cogs = len(cogs_to_reload)
        reloaded_count = 0
        failed_cogs = []

        for i, cog_name in enumerate(cogs_to_reload, 1):
            # Update progress every 5 cogs to reduce rate limits
            if i % 5 == 0 or i == total_cogs:
                if message:  # Only update if we have a message
                    embed.description = f"Reloading extensions... ({i}/{total_cogs})\n`{cog_name}`"
                    try:
                        await message.edit(embed=embed)
                        # Small delay to prevent rate limits
                        await asyncio.sleep(0.3)
                    except (discord.NotFound, discord.HTTPException, discord.Forbidden) as e:
                        logger.warning(f"Could not update progress message: {e}")
                        # Don't break, just continue without updates
                        message = None

            try:
                # Reload the extension
                await self.bot.reload_extension(cog_name)
                reloaded_count += 1
                logger.info(f"Reloaded: {cog_name}")
            except Exception as e:
                failed_cogs.append(cog_name)
                logger.error(f"Failed to reload {cog_name}: {e}")

        # Final status
        final_embed = discord.Embed(
            title="✅ Cog Reload Complete",
            description=(
                f"**Cache cleared:** {cleared_modules} modules\n"
                f"**Successfully reloaded:** {reloaded_count}/{total_cogs}\n"
                f"**Failed:** {len(failed_cogs)}"
            ),
            color=0x00ff00 if not failed_cogs else 0xffaa00
        )

        if failed_cogs:
            failed_list = "\n".join(f"• {cog}" for cog in failed_cogs[:10])
            final_embed.add_field(
                name="Failed Cogs",
                value=failed_list,
                inline=False
            )

        # Try to edit the original message, fallback to new message
        try:
            if message:
                await message.edit(embed=final_embed)
            else:
                await ctx.send(embed=final_embed)
        except (discord.NotFound, discord.HTTPException, discord.Forbidden) as e:
            logger.warning(f"Could not send final status: {e}")
            # Fallback to simple text message
            try:
                status_text = f"✅ Reload complete: {reloaded_count}/{total_cogs} cogs reloaded"
                if failed_cogs:
                    status_text += f", {len(failed_cogs)} failed"
                await ctx.send(status_text)
            except Exception as final_e:
                logger.error(f"Complete failure to send reload status: {final_e}")

    @commands.command()
    @admin_required()
    async def status(self, ctx):
        """Show bot status and statistics (Admin Only)"""
        try:
            # Basic stats
            cog_count = len(ctx.bot.cogs)
            command_count = len(list(ctx.bot.walk_commands()))
            guild_count = len(ctx.bot.guilds)

            # Calculate total users
            user_count = sum(guild.member_count or 0 for guild in ctx.bot.guilds)

            embed = discord.Embed(
                title="🤖 Ladbot Status",
                description="Current bot status and statistics",
                color=0x00ff00
            )

            embed.add_field(
                name="📊 Statistics",
                value=f"**Guilds:** {guild_count}\n**Users:** {user_count:,}\n**Commands:** {command_count}\n**Cogs:** {cog_count}",
                inline=True
            )

            embed.add_field(
                name="⚡ Performance",
                value=f"**Latency:** {round(ctx.bot.latency * 1000)}ms\n**Uptime:** {self._get_uptime(ctx.bot)}",
                inline=True
            )

            embed.add_field(
                name="🔧 System",
                value=f"**Admin Count:** {len(ctx.bot.settings.ADMIN_IDS)}\n**Requested by:** {ctx.author.mention}",
                inline=True
            )

            embed.set_footer(text="🔒 Admin-only information")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            # Fallback status
            try:
                await ctx.send(f"🤖 **Bot Status:** Online | **Cogs:** {len(ctx.bot.cogs)} | **Commands:** {len(list(ctx.bot.walk_commands()))}")
            except Exception as final_e:
                logger.error(f"Complete failure in status command: {final_e}")

    def _get_uptime(self, bot):
        """Calculate bot uptime"""
        try:
            if hasattr(bot, 'start_time'):
                uptime = datetime.now() - bot.start_time
                days = uptime.days
                hours, remainder = divmod(uptime.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return f"{days}d {hours}h {minutes}m"
            return "Unknown"
        except Exception as e:
            logger.warning(f"Error calculating uptime: {e}")
            return "Error"


async def setup(bot):
    await bot.add_cog(Reload(bot))