"""
Guild Settings Management Commands - Fixed with ONLY Real Commands
Handles all setting operations with comprehensive error handling
"""

import discord
from discord.ext import commands
from utils.decorators import admin_required
from utils.embeds import EmbedBuilder
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Settings(commands.Cog):
    """Guild settings management with comprehensive compatibility"""

    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = EmbedBuilder()

        # Define ONLY real Discord commands that actually exist
        self.available_settings = {
            # Core Commands - VERIFIED REAL COMMANDS
            'ping': 'Ping command - Check bot latency',
            'help': 'Help command - Show command list',
            'feedback': 'Feedback command - Send feedback to developers',
            'say': 'Say command - Make bot repeat text',

            # Entertainment Commands - VERIFIED REAL COMMANDS
            '8ball': '8-Ball command - Magic 8-ball responses',
            'jokes': 'Jokes command - Random jokes',
            'laugh': 'Laugh command - Bot laugh reactions',
            'ascii': 'ASCII command - Generate ASCII art',
            'minesweeper': 'Minesweeper command - Play minesweeper game',
            'knockknock': 'Knock-knock command - Knock-knock jokes',

            # Utility Commands - VERIFIED REAL COMMANDS
            'weather': 'Weather command - Get weather information',
            'convert': 'Convert command - Unit conversion',
            'roll': 'Roll command - Dice rolling',

            # Information Commands - VERIFIED REAL COMMANDS
            'crypto': 'Crypto command - Cryptocurrency prices',
            'reddit': 'Reddit command - Browse Reddit content',
            'bible': 'Bible command - Bible verse lookup',
            'dino': 'Dino command - Dinosaur facts',

            # Admin Features - VERIFIED REAL COMMANDS
            'autoresponse': 'Autoresponse command - Manage auto-responses'
        }

    @commands.command(name="settings", aliases=["config", "cfg"])
    @admin_required()
    async def settings(self, ctx, option: str = None, *, value: str = None):
        """Manage guild settings with comprehensive options

        Usage:
        l.settings - Show all settings
        l.settings <option> - Show specific setting
        l.settings <option> <value> - Change setting
        l.settings list - List available options
        l.settings reset - Reset all to defaults
        """
        try:
            # Handle special commands
            if option and option.lower() in ['list', 'available', 'options']:
                await self._show_available_settings(ctx)
                return
            elif option and option.lower() in ['reset', 'defaults']:
                await self._reset_settings(ctx)
                return
            elif option is None:
                await self._show_all_settings(ctx)
            elif value is None:
                await self._show_setting(ctx, option)
            else:
                await self._update_setting(ctx, option, value)

        except Exception as e:
            logger.error(f"Error in settings command: {e}")
            embed = discord.Embed(
                title="❌ Settings Error",
                description="An error occurred while processing your settings request.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    async def _show_all_settings(self, ctx):
        """Show all available settings with their current status"""
        try:
            embed = discord.Embed(
                title=f"⚙️ Bot Settings for {ctx.guild.name}",
                description="Current configuration for all bot features",
                color=0x4e73df
            )

            # Organize settings by category - ONLY REAL COMMANDS
            categories = {
                '🎮 Entertainment': ['8ball', 'jokes', 'laugh', 'ascii', 'minesweeper', 'knockknock'],
                '🔧 Utility': ['ping', 'help', 'feedback', 'say', 'weather', 'convert', 'roll'],
                '📊 Information': ['crypto', 'reddit', 'bible', 'dino'],
                '👑 Admin': ['autoresponse']
            }

            for category, settings in categories.items():
                setting_status = []
                for setting in settings:
                    if setting in self.available_settings:
                        # Get current setting value
                        current_value = self._get_setting_safe(ctx.guild.id, setting)
                        status_emoji = "✅" if current_value else "❌"
                        setting_status.append(f"{status_emoji} `{setting}`")

                if setting_status:
                    # Split into chunks if too many settings
                    chunks = [setting_status[i:i+6] for i in range(0, len(setting_status), 6)]
                    for i, chunk in enumerate(chunks):
                        field_name = category if i == 0 else f"{category} (cont.)"
                        embed.add_field(
                            name=field_name,
                            value="\n".join(chunk),
                            inline=True
                        )

            embed.add_field(
                name="📖 Usage Examples",
                value=(
                    f"`{ctx.prefix}settings ping off` - Disable ping command\n"
                    f"`{ctx.prefix}settings 8ball on` - Enable 8ball command\n"
                    f"`{ctx.prefix}settings list` - Show all available options\n"
                    f"`{ctx.prefix}settings reset` - Reset all to defaults"
                ),
                inline=False
            )

            embed.add_field(
                name="🔧 Special Commands",
                value=(
                    f"`{ctx.prefix}settings list` - View all configurable options\n"
                    f"`{ctx.prefix}settings reset` - Reset everything to defaults\n"
                    f"`{ctx.prefix}settings <command>` - Check status of specific command"
                ),
                inline=False
            )

            embed.set_footer(text=f"Use {ctx.prefix}settings <option> <on/off> to change settings")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing all settings: {e}")
            await ctx.send("❌ Error displaying settings. Please try again.")

    async def _show_setting(self, ctx, option):
        """Show details for a specific setting"""
        try:
            option = option.lower()

            if option not in self.available_settings:
                await self._show_invalid_option(ctx, option)
                return

            current_value = self._get_setting_safe(ctx.guild.id, option)
            status = "Enabled" if current_value else "Disabled"
            color = 0x00ff00 if current_value else 0xff9900
            emoji = "✅" if current_value else "❌"

            embed = discord.Embed(
                title=f"{emoji} {option.replace('_', ' ').title()}",
                description=self.available_settings[option],
                color=color
            )

            embed.add_field(
                name="Current Status",
                value=status,
                inline=True
            )

            embed.add_field(
                name="Setting Key",
                value=f"`{option}`",
                inline=True
            )

            embed.add_field(
                name="Change Setting",
                value=f"`{ctx.prefix}settings {option} {'off' if current_value else 'on'}`",
                inline=True
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing setting {option}: {e}")
            await ctx.send(f"❌ Error retrieving setting information for `{option}`")

    async def _update_setting(self, ctx, option, value):
        """Update a specific setting with comprehensive validation"""
        try:
            option = option.lower()
            value = value.lower()

            # Validate option exists
            if option not in self.available_settings:
                await self._show_invalid_option(ctx, option)
                return

            # Parse value
            true_values = ["yes", "y", "true", "t", "1", "enable", "on", "enabled", "allow"]
            false_values = ["no", "n", "false", "f", "0", "disable", "off", "disabled", "deny"]

            if value in true_values:
                new_value = True
                status = "enabled"
                emoji = "✅"
                color = 0x00ff00
            elif value in false_values:
                new_value = False
                status = "disabled"
                emoji = "❌"
                color = 0xff9900
            else:
                embed = discord.Embed(
                    title="❌ Invalid Value",
                    description=f"Invalid value `{value}` for setting `{option}`",
                    color=0xff0000
                )
                embed.add_field(
                    name="✅ Valid Enable Values",
                    value="on, yes, true, enable, 1, allow",
                    inline=True
                )
                embed.add_field(
                    name="❌ Valid Disable Values",
                    value="off, no, false, disable, 0, deny",
                    inline=True
                )
                embed.add_field(
                    name="Example",
                    value=f"`{ctx.prefix}settings {option} on`",
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            # Update the setting using multiple fallback methods
            success = self._set_setting_safe(ctx.guild.id, option, new_value)

            if not success:
                embed = discord.Embed(
                    title="❌ Error Updating Setting",
                    description="Failed to save the setting. Please try again or contact an administrator.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            # Verify the setting was actually changed
            updated_value = self._get_setting_safe(ctx.guild.id, option)
            if updated_value != new_value:
                logger.warning(f"Setting {option} not properly updated for guild {ctx.guild.id}")

            # Create success embed
            embed = discord.Embed(
                title=f"{emoji} Setting Updated Successfully",
                description=f"**{option.replace('_', ' ').title()}** has been **{status}** for this server.",
                color=color
            )

            embed.add_field(
                name="Setting",
                value=f"`{option}`",
                inline=True
            )

            embed.add_field(
                name="New Status",
                value=status.title(),
                inline=True
            )

            embed.add_field(
                name="Changed By",
                value=ctx.author.mention,
                inline=True
            )

            embed.add_field(
                name="Description",
                value=self.available_settings[option],
                inline=False
            )

            embed.set_footer(text=f"Use {ctx.prefix}settings to view all settings")
            embed.timestamp = datetime.utcnow()

            await ctx.send(embed=embed)

            # Log the change
            logger.info(f"Admin {ctx.author} ({ctx.author.id}) changed setting '{option}' to {new_value} in guild {ctx.guild.name} ({ctx.guild.id})")

        except Exception as e:
            logger.error(f"Error updating setting {option}: {e}")
            embed = discord.Embed(
                title="❌ Error Updating Setting",
                description=f"An unexpected error occurred: {str(e)[:100]}...",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    async def _show_available_settings(self, ctx):
        """Show all available settings in organized categories"""
        try:
            embed = discord.Embed(
                title="📋 Available Settings",
                description="All configurable bot features for this server",
                color=0x4e73df
            )

            # Organize by category - ONLY REAL COMMANDS
            categories = {
                '🎮 Entertainment Commands': {
                    '8ball': '8-Ball magic responses',
                    'jokes': 'Random jokes and puns',
                    'ascii': 'ASCII art generator',
                    'minesweeper': 'Minesweeper game',
                    'knockknock': 'Knock-knock jokes',
                    'laugh': 'Laugh reactions'
                },
                '🔧 Utility Commands': {
                    'ping': 'Bot latency check',
                    'help': 'Command help system',
                    'weather': 'Weather information',
                    'convert': 'Unit conversion',
                    'roll': 'Dice rolling',
                    'feedback': 'Send feedback',
                    'say': 'Text repeating'
                },
                '📊 Information Commands': {
                    'crypto': 'Cryptocurrency data',
                    'reddit': 'Reddit content',
                    'bible': 'Bible verse lookup',
                    'dino': 'Dinosaur facts'
                },
                '👑 Admin Features': {
                    'autoresponse': 'Auto-response system'
                }
            }

            for category, settings in categories.items():
                setting_list = []
                for key, desc in settings.items():
                    current_value = self._get_setting_safe(ctx.guild.id, key)
                    status = "✅" if current_value else "❌"
                    setting_list.append(f"{status} **{key}** - {desc}")

                if setting_list:
                    embed.add_field(
                        name=category,
                        value="\n".join(setting_list),
                        inline=False
                    )

            embed.add_field(
                name="💡 Usage Tips",
                value=(
                    f"• `{ctx.prefix}settings <option> on` - Enable a feature\n"
                    f"• `{ctx.prefix}settings <option> off` - Disable a feature\n"
                    f"• `{ctx.prefix}settings list` - Show all available options\n"
                    f"• `{ctx.prefix}settings reset` - Reset all to defaults"
                ),
                inline=False
            )

            embed.add_field(
                name="🔧 Advanced Options",
                value=(
                    f"• `{ctx.prefix}settings reset` - Resets ALL settings to enabled\n"
                    f"• Requires ✅ confirmation before executing\n"
                    f"• Cannot be undone - use with caution!"
                ),
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing available settings: {e}")
            await ctx.send("❌ Error displaying available settings.")

    async def _show_invalid_option(self, ctx, option):
        """Show error message for invalid setting option"""
        embed = discord.Embed(
            title="❌ Invalid Setting",
            description=f"Setting `{option}` is not recognized.",
            color=0xff0000
        )

        # Suggest similar settings
        similar_settings = [key for key in self.available_settings.keys()
                          if option in key or key in option]

        if similar_settings:
            embed.add_field(
                name="💡 Did you mean?",
                value=", ".join(f"`{s}`" for s in similar_settings[:5]),
                inline=False
            )

        embed.add_field(
            name="📋 View All Options",
            value=f"`{ctx.prefix}settings list`",
            inline=True
        )

        embed.add_field(
            name="🏠 View All Settings",
            value=f"`{ctx.prefix}settings`",
            inline=True
        )

        embed.add_field(
            name="🔧 Reset to Defaults",
            value=f"`{ctx.prefix}settings reset`",
            inline=True
        )

        await ctx.send(embed=embed)

    async def _reset_settings(self, ctx):
        """Reset all settings to default values"""
        try:
            # Confirmation prompt
            embed = discord.Embed(
                title="⚠️ Reset All Settings",
                description="This will reset ALL bot settings to their default values. This action cannot be undone.",
                color=0xff9900
            )
            embed.add_field(
                name="⚠️ Warning",
                value="This will enable ALL 19 commands and features for this server.",
                inline=False
            )
            embed.add_field(
                name="Confirm Reset",
                value="React with ✅ to confirm or ❌ to cancel\n*You have 30 seconds to respond*",
                inline=False
            )

            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            def check(reaction, user):
                return (user == ctx.author and
                       str(reaction.emoji) in ["✅", "❌"] and
                       reaction.message.id == message.id)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)

                if str(reaction.emoji) == "✅":
                    # Reset all settings to True (default enabled)
                    reset_count = 0
                    for setting in self.available_settings.keys():
                        if self._set_setting_safe(ctx.guild.id, setting, True):
                            reset_count += 1

                    embed = discord.Embed(
                        title="✅ Settings Reset Complete",
                        description=f"Successfully reset {reset_count} settings to their default values.",
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="Default State",
                        value="All commands and features are now **enabled**",
                        inline=False
                    )
                    embed.add_field(
                        name="What's Enabled",
                        value="Entertainment, Utility, Information, and Admin commands are all active.",
                        inline=False
                    )
                    await message.edit(embed=embed)

                    logger.info(f"Admin {ctx.author} reset all settings for guild {ctx.guild.id}")
                else:
                    embed = discord.Embed(
                        title="❌ Reset Cancelled",
                        description="Settings reset has been cancelled. No changes were made.",
                        color=0xff9900
                    )
                    await message.edit(embed=embed)

            except Exception as e:
                embed = discord.Embed(
                    title="⏰ Reset Timeout",
                    description="Settings reset timed out. No changes were made.",
                    color=0xff9900
                )
                await message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Error in reset settings: {e}")
            await ctx.send("❌ Error during settings reset.")

    def _get_setting_safe(self, guild_id, setting_name, default=True):
        """Safely get a setting with multiple fallback methods"""
        try:
            # Method 1: Use bot's get_setting method if available
            if hasattr(self.bot, 'get_setting'):
                return self.bot.get_setting(guild_id, setting_name, default)

            # Method 2: Use data_manager if available
            if hasattr(self.bot, 'data_manager') and hasattr(self.bot.data_manager, 'get_guild_setting'):
                return self.bot.data_manager.get_guild_setting(guild_id, setting_name, default)

            # Method 3: Check settings cache
            if hasattr(self.bot, 'settings_cache') and guild_id in self.bot.settings_cache:
                return self.bot.settings_cache[guild_id].get(setting_name, default)

            # Method 4: Return default
            return default

        except Exception as e:
            logger.debug(f"Error getting setting {setting_name}: {e}")
            return default

    def _set_setting_safe(self, guild_id, setting_name, value):
        """Safely set a setting with multiple fallback methods"""
        try:
            success = False

            # Method 1: Use bot's set_setting method if available
            if hasattr(self.bot, 'set_setting'):
                try:
                    result = self.bot.set_setting(guild_id, setting_name, value)
                    success = success or result
                except Exception as e:
                    logger.debug(f"Method 1 failed: {e}")

            # Method 2: Use data_manager if available
            if hasattr(self.bot, 'data_manager') and hasattr(self.bot.data_manager, 'set_guild_setting'):
                try:
                    result = self.bot.data_manager.set_guild_setting(guild_id, setting_name, value)
                    success = success or result
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")

            # Method 3: Update settings cache directly
            if hasattr(self.bot, 'settings_cache'):
                try:
                    if guild_id not in self.bot.settings_cache:
                        self.bot.settings_cache[guild_id] = {}
                    self.bot.settings_cache[guild_id][setting_name] = value
                    success = True
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")

            return success

        except Exception as e:
            logger.error(f"Error setting {setting_name} to {value}: {e}")
            return False


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Settings(bot))