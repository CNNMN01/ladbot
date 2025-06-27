"""
Cog reloading commands for administrators - SECURED VERSION
"""

import sys

import discord
from discord.ext import commands
from utils.decorators import admin_required, owner_only, dangerous_command
from utils.embeds import EmbedBuilder
import time
import importlib
import sys
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Reload(commands.Cog):
    """Cog management commands - SECURED"""

    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = EmbedBuilder()

    @commands.command()
    @admin_required()
    async def reload(self, ctx, cog_name: str = None):
        """Reload cogs with proper cache clearing (Admin Only)

        Usage:
        l.reload - Reload all cogs
        l.reload <cog_name> - Reload specific cog
        """
        if cog_name:
            await self._reload_single_cog(ctx, cog_name)
        else:
            await self._reload_all_cogs(ctx)

    async def _reload_single_cog(self, ctx, cog_name: str):
        """Reload a single cog with cache clearing"""
        # Try to find the cog in loaded cogs
        full_cog_name = None
        for loaded_cog in self.bot.cog_loader.loaded_cogs:
            if cog_name.lower() in loaded_cog.lower():
                full_cog_name = loaded_cog
                break

        if not full_cog_name:
            await ctx.send(embed=self.embed_builder.create_error_embed(
                f"Cog `{cog_name}` not found in loaded cogs."
            ))
            return

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

            await ctx.send(embed=self.embed_builder.create_success_embed(
                f"Successfully reloaded `{full_cog_name}` with cache clearing"
            ))

        except Exception as e:
            logger.error(f"Failed to reload {full_cog_name}: {e}")
            await ctx.send(embed=self.embed_builder.create_error_embed(
                f"Failed to reload `{full_cog_name}`: {str(e)[:100]}..."
            ))

    async def _reload_all_cogs(self, ctx):
        """Reload all cogs with progress updates and cache clearing"""
        embed = discord.Embed(
            title="🔄 Reloading All Cogs",
            description="Clearing Python cache and reloading extensions...",
            color=self.bot.data_manager.embed_color
        )
        message = await ctx.send(embed=embed)

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
            # Update progress every 3 cogs or on completion
            if i % 3 == 0 or i == total_cogs:
                embed.description = f"Reloading extensions... ({i}/{total_cogs})\n`{cog_name}`"
                try:
                    await message.edit(embed=embed)
                except discord.NotFound:
                    break

            try:
                # Reload the extension
                await self.bot.reload_extension(cog_name)
                reloaded_count += 1
                logger.info(f"Reloaded: {cog_name}")
            except Exception as e:
                failed_cogs.append(cog_name)
                logger.error(f"Failed to reload {cog_name}: {e}")

        # Final status
        embed.title = "✅ Cog Reload Complete"
        embed.description = (
            f"**Cache cleared:** {cleared_modules} modules\n"
            f"**Successfully reloaded:** {reloaded_count}/{total_cogs}\n"
            f"**Failed:** {len(failed_cogs)}"
        )

        if failed_cogs:
            embed.add_field(
                name="Failed Cogs",
                value="\n".join(f"• {cog}" for cog in failed_cogs[:10]),
                inline=False
            )

        embed.color = 0x00ff00 if not failed_cogs else 0xffaa00

        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            await ctx.send(embed=embed)

    @commands.command()
    @owner_only()
    async def forcereload(self, ctx, cog_name: str = None):
        """Force reload with aggressive cache clearing (Bot Owner Only)"""

        if cog_name:
            # Single cog force reload
            try:
                # Find the full cog name
                full_cog_name = None
                for loaded_cog in self.bot.cog_loader.loaded_cogs:
                    if cog_name.lower() in loaded_cog.lower():
                        full_cog_name = loaded_cog
                        break

                if not full_cog_name:
                    await ctx.send(f"❌ Cog `{cog_name}` not found.")
                    return

                embed = discord.Embed(
                    title="🔄 Force Reloading Cog",
                    description=f"Aggressively reloading `{full_cog_name}`...",
                    color=0xffaa00
                )
                message = await ctx.send(embed=embed)

                # Step 1: Unload extension
                if full_cog_name in self.bot.extensions:
                    await self.bot.unload_extension(full_cog_name)

                # Step 2: Clear from sys.modules and all related modules
                modules_to_clear = [name for name in sys.modules.keys()
                                    if name.startswith(full_cog_name) or name == full_cog_name]

                for module in modules_to_clear:
                    if module in sys.modules:
                        try:
                            importlib.reload(sys.modules[module])
                        except:
                            # If reload fails, remove from cache entirely
                            del sys.modules[module]

                # Step 3: Load again
                await self.bot.load_extension(full_cog_name)

                embed.title = "✅ Force Reload Complete"
                embed.description = f"Successfully force reloaded `{full_cog_name}`\nCleared {len(modules_to_clear)} modules from cache"
                embed.color = 0x00ff00

                await message.edit(embed=embed)
                logger.warning(f"Bot Owner {ctx.author} force reloaded {full_cog_name}")

            except Exception as e:
                embed = discord.Embed(
                    title="❌ Force Reload Failed",
                    description=f"Error: {str(e)[:200]}...",
                    color=0xff0000
                )
                await ctx.send(embed=embed)

        else:
            # Force reload all
            embed = discord.Embed(
                title="🔄 Force Reloading All Cogs",
                description="⚠️ **DANGEROUS OPERATION** ⚠️\nAggressively clearing cache and reloading...",
                color=0xffaa00
            )
            message = await ctx.send(embed=embed)

            # Clear ALL cog-related modules from cache
            cog_modules = [name for name in list(sys.modules.keys()) if name.startswith('cogs.')]
            utils_modules = [name for name in list(sys.modules.keys()) if name.startswith('utils.')]

            cleared_count = 0
            for module_name in cog_modules + utils_modules:
                if module_name in sys.modules:
                    try:
                        importlib.reload(sys.modules[module_name])
                        cleared_count += 1
                    except:
                        try:
                            del sys.modules[module_name]
                            cleared_count += 1
                        except:
                            pass

            # Reload all cogs
            cogs_to_reload = list(self.bot.cog_loader.loaded_cogs)
            reloaded = 0
            failed = 0
            failed_list = []

            for cog_name in cogs_to_reload:
                try:
                    await self.bot.reload_extension(cog_name)
                    reloaded += 1
                except Exception as e:
                    failed += 1
                    failed_list.append(cog_name)
                    logger.error(f"Failed to force reload {cog_name}: {e}")

            embed.title = "✅ Force Reload Complete"
            embed.description = f"**Cache cleared:** {cleared_count} modules\n**Reloaded:** {reloaded}\n**Failed:** {failed}"
            embed.color = 0x00ff00 if failed == 0 else 0xffaa00

            if failed_list:
                embed.add_field(
                    name="Failed Cogs",
                    value="\n".join(f"• {cog}" for cog in failed_list[:5]),
                    inline=False
                )

            await message.edit(embed=embed)
            logger.warning(f"Bot Owner {ctx.author} performed FORCE RELOAD ALL")

    @commands.command()
    @admin_required()
    async def status(self, ctx):
        """Show bot status and statistics (Admin Only)"""

        # Basic stats
        cog_count = len(ctx.bot.cogs)
        command_count = len(list(ctx.bot.walk_commands()))
        guild_count = len(ctx.bot.guilds)

        # Calculate total users
        user_count = 0
        for guild in ctx.bot.guilds:
            if guild.member_count:
                user_count += guild.member_count

        # Active games count
        active_games = 0
        for cog in ctx.bot.cogs.values():
            if hasattr(cog, 'active_games'):
                active_games += len(cog.active_games)

        # Simple memory check (fallback if psutil not available)
        try:
            import psutil
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            cpu_percent = psutil.Process().cpu_percent()

            # Uptime calculation
            uptime_seconds = time.time() - psutil.Process().create_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)

            system_info = f"**Memory:** {memory_usage:.1f} MB\n**CPU:** {cpu_percent}%\n**Uptime:** {uptime_hours}h {uptime_minutes}m"
        except ImportError:
            system_info = "**System Info:** Not available\n*(Install psutil for detailed stats)*"
        except Exception as e:
            system_info = f"**System Info:** Error loading\n*(Error: {str(e)[:30]}...)*"

        embed = discord.Embed(
            title="🤖 Ladbot Status Dashboard",
            description="Bot status and statistics",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📊 Bot Statistics",
            value=f"**Servers:** {guild_count:,}\n**Users:** {user_count:,}\n**Cogs:** {cog_count}\n**Commands:** {command_count}",
            inline=True
        )

        embed.add_field(
            name="🎮 Active Sessions",
            value=f"**Minesweeper Games:** {active_games}\n**Latency:** {round(ctx.bot.latency * 1000)}ms\n**Status:** Online ✅",
            inline=True
        )

        embed.add_field(
            name="⚡ System Performance",
            value=system_info,
            inline=True
        )

        # Admin info
        embed.add_field(
            name="🛡️ Admin Info",
            value=f"**Admin Count:** {len(ctx.bot.settings.admin_ids)}\n**Requested by:** {ctx.author.mention}",
            inline=True
        )

        embed.set_footer(text="🔒 Admin-only information")
        await ctx.send(embed=embed)

    @commands.command()
    @admin_required()
    async def botinfo(self, ctx):
        """Show detailed bot information (Admin Only)"""

        embed = discord.Embed(
            title="🤖 Ladbot Information",
            description="Detailed information about this bot instance",
            color=0x00ff00
        )

        # Bot details
        embed.add_field(
            name="📋 Bot Details",
            value=f"**Name:** {ctx.bot.user.name}\n**ID:** {ctx.bot.user.id}\n**Version:** 2.0.0\n**Prefix:** {ctx.bot.settings.prefix}",
            inline=False
        )

        # Loaded cogs
        cogs_list = []
        for cog_name, cog in ctx.bot.cogs.items():
            command_count = len([cmd for cmd in ctx.bot.walk_commands() if cmd.cog == cog])
            cogs_list.append(f"• **{cog_name}** ({command_count} commands)")

        # Split into chunks if too many cogs
        if len(cogs_list) > 10:
            cogs_display = "\n".join(cogs_list[:10]) + f"\n... and {len(cogs_list) - 10} more"
        else:
            cogs_display = "\n".join(cogs_list)

        embed.add_field(
            name=f"🔧 Loaded Cogs ({len(ctx.bot.cogs)})",
            value=cogs_display or "No cogs loaded",
            inline=False
        )

        # Configuration info (ADMIN ONLY)
        embed.add_field(
            name="⚙️ Configuration",
            value=f"**Debug Mode:** {'Yes' if ctx.bot.settings.debug else 'No'}\n**Database:** {'PostgreSQL' if 'postgresql' in ctx.bot.settings.database_url else 'SQLite'}\n**Admin Count:** {len(ctx.bot.settings.admin_ids)}",
            inline=True
        )

        # Security info (ADMIN ONLY)
        embed.add_field(
            name="🔒 Security Info",
            value=f"**Admin IDs:** {len(ctx.bot.settings.admin_ids)} configured\n**Intents:** Message Content, Members\n**Permissions:** Bot Admin",
            inline=True
        )

        embed.set_footer(text="🔒 Admin-only information")
        await ctx.send(embed=embed)

    @commands.command()
    @dangerous_command()
    async def clearmodules(self, ctx):
        """Clear all cached Python modules (NUCLEAR OPTION - Bot Owner Only)"""

        embed = discord.Embed(
            title="⚠️ DANGER: Clear Module Cache",
            description="**THIS IS A DANGEROUS OPERATION**\n\nThis will clear ALL cached Python modules and could completely break the bot.\n\n**Type `CONFIRM NUCLEAR` to proceed:**",
            color=0xff0000
        )

        embed.add_field(
            name="⚠️ WARNING",
            value="• This can break the bot completely\n• Only use if reload is completely broken\n• You may need to restart the bot manually\n• Bot Owner permission required",
            inline=False
        )

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            if response.content == "CONFIRM NUCLEAR":
                # Clear ALL modules except core Python ones
                to_clear = []
                core_modules = ['__builtin__', '__main__', 'sys', 'os', 'discord', 'asyncio']

                for name in list(sys.modules.keys()):
                    if not any(name.startswith(core) for core in core_modules):
                        to_clear.append(name)

                cleared = 0
                for module in to_clear:
                    try:
                        del sys.modules[module]
                        cleared += 1
                    except:
                        pass

                embed = discord.Embed(
                    title="💥 NUCLEAR MODULE CLEAR COMPLETE",
                    description=f"Cleared {cleared} modules from cache.\n\n**CRITICAL:** Run `l.forcereload` immediately!",
                    color=0xff4500
                )

                embed.add_field(
                    name="🚨 Next Steps",
                    value="1. Run `l.forcereload` immediately\n2. If bot becomes unresponsive, restart manually\n3. Monitor for any issues",
                    inline=False
                )

                await ctx.send(embed=embed)
                logger.critical(f"Bot Owner {ctx.author} performed NUCLEAR MODULE CLEAR - {cleared} modules cleared")
            else:
                await ctx.send("❌ Nuclear operation cancelled - module cache NOT cleared.")
        except:
            await ctx.send("❌ Timed out - nuclear operation cancelled.")


async def setup(bot):
    await bot.add_cog(Reload(bot))