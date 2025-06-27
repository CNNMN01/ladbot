"""
Guild settings management commands
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from discord.ext import commands
from utils.decorators import admin_required
from utils.pagination import PaginatedEmbed


class Settings(commands.Cog):
    """Guild settings management"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @admin_required()
    async def settings(self, ctx, option: str = None, *, value: str = None):
        """Manage guild settings

        Usage:
        l.settings - Show all settings
        l.settings <option> - Show specific setting
        l.settings <option> <value> - Change setting
        """
        if option is None:
            await self._show_all_settings(ctx)
        elif value is None:
            await self._show_setting(ctx, option)
        else:
            await self._update_setting(ctx, option, value)

    async def _show_all_settings(self, ctx):
        """Show all available settings in a clean format"""
        try:
            # Create a simple settings display since we don't have full data_manager
            embed = discord.Embed(
                title=f"⚙️ Bot Settings for {ctx.guild.name}",
                description="Configure bot behavior for your server",
                color=0x00ff00
            )

            # Get basic settings from the bot's simple system
            settings_info = {
                'ping': 'Ping Command',
                'help': 'Help Command',
                'feedback': 'Feedback Command',
                'say': 'Say Command',
                'ascii': 'ASCII Art Command',
                'cmd_8ball': '8-Ball Command',
                'jokes': 'Jokes Command',
                'weather': 'Weather Command',
                'crypto': 'Crypto Command',
                'reddit': 'Reddit Command',
                'bible': 'Bible Command',
                'roll': 'Dice Roll Command',
                'minesweeper': 'Minesweeper Game',
                'autoresponses': 'Auto-Responses Feature'
            }

            # Show settings in a clean format
            settings_text = ""
            for setting_key, setting_name in settings_info.items():
                current_value = self.bot.get_setting(ctx.guild.id, setting_key)
                status = "✅ Enabled" if current_value else "❌ Disabled"
                settings_text += f"**{setting_name}:** {status}\n"

            embed.add_field(
                name="📋 Command & Feature Settings",
                value=settings_text,
                inline=False
            )

            embed.add_field(
                name="💡 How to Change Settings",
                value=f"Use `{ctx.prefix}settings <option> on/off`\n"
                      f"Example: `{ctx.prefix}settings ping off`",
                inline=False
            )

            embed.add_field(
                name="📖 Available Options",
                value="ping, help, feedback, say, ascii, cmd_8ball, jokes, weather, crypto, reddit, bible, roll, minesweeper, autoresponses",
                inline=False
            )

            embed.set_footer(text=f"Use {ctx.prefix}settings <option> to view a specific setting")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error loading settings: {e}")

    async def _show_setting(self, ctx, option: str):
        """Show a specific setting"""
        try:
            # Clean the option name
            option = option.lower().strip()

            # Define available options with descriptions
            available_options = {
                'ping': {'name': 'Ping Command', 'desc': 'Allow users to check bot latency'},
                'help': {'name': 'Help Command', 'desc': 'Show available commands and usage'},
                'feedback': {'name': 'Feedback Command', 'desc': 'Allow users to send feedback'},
                'say': {'name': 'Say Command', 'desc': 'Make the bot repeat text'},
                'ascii': {'name': 'ASCII Art', 'desc': 'Generate ASCII art from text'},
                'cmd_8ball': {'name': '8-Ball Command', 'desc': 'Magic 8-ball responses'},
                'jokes': {'name': 'Jokes Command', 'desc': 'Random jokes and dad jokes'},
                'weather': {'name': 'Weather Command', 'desc': 'Weather information lookup'},
                'crypto': {'name': 'Crypto Command', 'desc': 'Cryptocurrency price checking'},
                'reddit': {'name': 'Reddit Command', 'desc': 'Browse Reddit posts'},
                'bible': {'name': 'Bible Command', 'desc': 'Look up Bible verses'},
                'roll': {'name': 'Dice Roll', 'desc': 'Roll dice with D&D notation'},
                'minesweeper': {'name': 'Minesweeper Game', 'desc': 'Interactive minesweeper game'},
                'autoresponses': {'name': 'Auto-Responses', 'desc': 'Automatic keyword responses'}
            }

            if option not in available_options:
                # Suggest similar options
                similar = [opt for opt in available_options.keys() if option in opt or opt in option]

                embed = discord.Embed(
                    title="❌ Setting Not Found",
                    description=f"Setting `{option}` not found.",
                    color=0xff0000
                )

                if similar:
                    embed.add_field(
                        name="💡 Did you mean?",
                        value="\n".join(f"• `{suggestion}`" for suggestion in similar[:5]),
                        inline=False
                    )

                embed.add_field(
                    name="📖 Available Settings",
                    value=", ".join(f"`{opt}`" for opt in available_options.keys()),
                    inline=False
                )

                embed.set_footer(text=f"Use {ctx.prefix}settings to see all settings")
                await ctx.send(embed=embed)
                return

            # Get current setting value
            current_value = self.bot.get_setting(ctx.guild.id, option)
            option_info = available_options[option]

            # Create status embed
            status_emoji = "✅" if current_value else "❌"

            embed = discord.Embed(
                title=f"{status_emoji} {option_info['name']}",
                description=option_info['desc'],
                color=0x00ff00 if current_value else 0xff0000
            )

            embed.add_field(
                name="Current Status",
                value=f"**{'Enabled' if current_value else 'Disabled'}**",
                inline=True
            )

            embed.add_field(
                name="Default",
                value="Enabled",  # Most commands default to enabled
                inline=True
            )

            embed.add_field(
                name="Type",
                value="Boolean (on/off)",
                inline=True
            )

            embed.add_field(
                name="💡 How to Change",
                value=f"`{ctx.prefix}settings {option} on` - Enable\n`{ctx.prefix}settings {option} off` - Disable",
                inline=False
            )

            embed.set_footer(text=f"Setting: {option}")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    async def _update_setting(self, ctx, option: str, value: str):
        """Update a setting"""
        try:
            # Clean inputs
            option = option.lower().strip()
            value = value.lower().strip()

            # Define available options
            available_options = {
                'ping', 'help', 'feedback', 'say', 'ascii', 'cmd_8ball',
                'jokes', 'weather', 'crypto', 'reddit', 'bible', 'roll',
                'minesweeper', 'autoresponses'
            }

            if option not in available_options:
                embed = discord.Embed(
                    title="❌ Invalid Setting",
                    description=f"Setting `{option}` not found.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Available Settings",
                    value=", ".join(f"`{opt}`" for opt in sorted(available_options)),
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            # Convert value to boolean
            true_values = ["yes", "y", "true", "t", "1", "enable", "on", "enabled"]
            false_values = ["no", "n", "false", "f", "0", "disable", "off", "disabled"]

            if value in true_values:
                new_value = True
                status = "enabled"
                emoji = "✅"
            elif value in false_values:
                new_value = False
                status = "disabled"
                emoji = "❌"
            else:
                embed = discord.Embed(
                    title="❌ Invalid Value",
                    description=f"Invalid value for `{option}`. Use `on` or `off`.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Valid Values",
                    value="**Enable:** on, yes, true, enable, 1\n**Disable:** off, no, false, disable, 0",
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            # Update the setting
            await self.bot.update_setting(ctx.guild.id, option, new_value)

            # Create success embed
            embed = discord.Embed(
                title=f"{emoji} Setting Updated",
                description=f"**{option.replace('_', ' ').title()}** has been **{status}**.",
                color=0x00ff00 if new_value else 0xff9900
            )

            embed.add_field(
                name="Setting",
                value=option,
                inline=True
            )

            embed.add_field(
                name="New Value",
                value=status.title(),
                inline=True
            )

            embed.add_field(
                name="Updated By",
                value=ctx.author.mention,
                inline=True
            )

            embed.set_footer(text=f"Use {ctx.prefix}settings to view all settings")
            await ctx.send(embed=embed)

            # Log the change
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Admin {ctx.author} changed setting {option} to {new_value} in guild {ctx.guild.id}")

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Updating Setting",
                description=f"Failed to update setting: {e}",
                color=0xff0000
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Settings(bot))