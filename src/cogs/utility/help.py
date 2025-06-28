"""
Enhanced Help command with fuzzy matching and case insensitivity
"""

import sys

import discord
from discord.ext import commands
from utils.pagination import PaginatedEmbed
import logging

logger = logging.getLogger(__name__)


class Help(commands.Cog):
    """Enhanced help system with fuzzy matching"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command = None  # Remove default help

        # Define admin-only cogs and commands
        self.admin_only_cogs = ['Settings', 'Console', 'Reload', 'ErrorHandler', 'Moderation']
        self.admin_only_commands = ['settings', 'reload', 'console', 'feedback_debug', 'ban', 'kick', 'purge']

    def _is_admin(self, ctx):
        """Check if user is admin"""
        if not ctx.guild:
            return False

        # Check server admin
        if ctx.author.guild_permissions.administrator:
            return True

        # Check bot admin list
        try:
            admin_ids = getattr(self.bot.config, 'ADMIN_IDS', []) or getattr(self.bot.config, 'admin_ids', [])
            if ctx.author.id in admin_ids:
                return True
        except:
            pass

        return False

    def _should_show_command(self, command, ctx):
        """Determine if a command should be shown to the user"""
        # Hide admin commands from non-admins
        if command.name in self.admin_only_commands and not self._is_admin(ctx):
            return False

        # Check if command cog is admin-only
        if command.cog and command.cog.qualified_name in self.admin_only_cogs and not self._is_admin(ctx):
            return False

        return True

    @commands.command(name="help", aliases=["h", "commands"])
    async def help_command(self, ctx, *, command_name: str = None):
        """Show help information

        Usage:
        l.help - Show all categories
        l.help <command> - Show help for a command
        l.help <category> - Show commands in a category
        """
        if command_name is None:
            await self._show_main_help(ctx)
        else:
            await self._show_command_help(ctx, command_name)

    async def _show_main_help(self, ctx):
        """Show the main help menu with categories"""
        embed = discord.Embed(
            title="🤖 Ladbot Help Menu",
            description="Choose a category or use `help <command>` for specific command info",
            color=0x00ff00
        )

        # Group commands by category
        categories = {}

        for cog_name, cog in self.bot.cogs.items():
            # Skip internal cogs
            if cog_name in ['Events', 'Help']:
                continue

            # Skip admin cogs for non-admins
            if cog_name in self.admin_only_cogs and not self._is_admin(ctx):
                continue

            # Count visible commands in this cog
            visible_commands = []
            for command in cog.get_commands():
                if self._should_show_command(command, ctx):
                    visible_commands.append(command)

            if visible_commands:
                categories[cog_name] = {
                    'cog': cog,
                    'commands': visible_commands,
                    'count': len(visible_commands)
                }

        # Create category fields
        for category_name, category_info in categories.items():
            emoji = self._get_category_emoji(category_name)
            cog = category_info['cog']
            count = category_info['count']

            # Add admin indicator
            display_name = category_name
            if category_name in self.admin_only_cogs:
                display_name += " 🛡️"

            # Get some example commands
            example_commands = [cmd.name for cmd in category_info['commands'][:3]]
            examples = ", ".join([f"`{cmd}`" for cmd in example_commands])

            if count > 3:
                examples += f" (+{count-3} more)"

            description = cog.description or f"Commands in the {category_name} category"

            embed.add_field(
                name=f"{emoji} {display_name} ({count})",
                value=f"{description}\n**Examples:** {examples}",
                inline=False
            )

        embed.add_field(
            name="📋 Quick Commands",
            value=f"`{ctx.prefix}help <category>` - Show category commands\n`{ctx.prefix}help <command>` - Command details\n`{ctx.prefix}cmdlist` - All commands list",
            inline=False
        )

        embed.set_footer(text=f"Use {ctx.prefix}help <command> for detailed information about a command")
        await ctx.send(embed=embed)

    async def _show_command_help(self, ctx, command_name: str):
        """Show help for a specific command or category with improved matching"""

        # First, try exact command match
        command = self.bot.get_command(command_name.lower())
        if command:
            if self._should_show_command(command, ctx):
                embed = discord.Embed(
                    title=f"📖 Command: {ctx.prefix}{command.name}",
                    color=0x00ff00
                )

                # Add admin indicator if it's an admin command
                if command.name in self.admin_only_commands:
                    embed.title += " 🛡️"
                    embed.add_field(
                        name="🔒 Permissions",
                        value="**Administrator Only**",
                        inline=True
                    )

                # Command description
                description = command.help or command.brief or "No description available."
                embed.description = description

                # Usage/signature
                if command.signature:
                    embed.add_field(
                        name="📝 Usage",
                        value=f"`{ctx.prefix}{command.name} {command.signature}`",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📝 Usage",
                        value=f"`{ctx.prefix}{command.name}`",
                        inline=False
                    )

                # Aliases
                if command.aliases:
                    aliases = ", ".join([f"`{alias}`" for alias in command.aliases])
                    embed.add_field(
                        name="🔄 Aliases",
                        value=aliases,
                        inline=False
                    )

                # Category
                if command.cog:
                    category_name = command.cog.qualified_name
                    if category_name in self.admin_only_cogs:
                        category_name += " 🛡️"
                    embed.add_field(
                        name="📁 Category",
                        value=category_name,
                        inline=True
                    )

                # Cooldown info
                try:
                    if hasattr(command, '_buckets') and command._buckets._cooldown:
                        cooldown = command._buckets._cooldown
                        embed.add_field(
                            name="⏱️ Cooldown",
                            value=f"{cooldown.rate} uses per {cooldown.per} seconds",
                            inline=True
                        )
                except:
                    pass  # Skip cooldown info if not available

                embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                await ctx.send(embed=embed)
                return
            else:
                embed = discord.Embed(
                    title="🔒 Command Restricted",
                    description=f"The command `{command_name}` requires special permissions.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

        # Try to find it as a cog/category with improved case-insensitive matching
        target_cog = None

        # Create variations of the search term
        search_variations = [
            command_name,                    # Original: "AsciiArt"
            command_name.lower(),           # "asciiart"
            command_name.title(),           # "Asciiart"
            command_name.upper(),           # "ASCIIART"
            command_name.replace('_', ''),  # Remove underscores
            command_name.replace('-', ''),  # Remove hyphens
        ]

        # Special handling for common variations
        if 'ascii' in command_name.lower():
            search_variations.extend(['AsciiArt', 'Ascii', 'ascii', 'art', 'Art'])

        # Try direct cog name matches
        for variation in search_variations:
            cog = self.bot.get_cog(variation)
            if cog:
                target_cog = cog
                break

        # If no direct match, try partial/fuzzy matching
        if not target_cog:
            command_name_lower = command_name.lower()
            best_match = None
            best_score = 0

            for cog_name, cog in self.bot.cogs.items():
                if cog_name in ['Events', 'Help']:
                    continue

                cog_name_lower = cog_name.lower()

                # Calculate match score
                score = 0

                # Exact match (highest priority)
                if command_name_lower == cog_name_lower:
                    score = 100
                # One contains the other
                elif command_name_lower in cog_name_lower:
                    score = 80
                elif cog_name_lower in command_name_lower:
                    score = 75
                # Starts with
                elif cog_name_lower.startswith(command_name_lower):
                    score = 70
                elif command_name_lower.startswith(cog_name_lower):
                    score = 65
                # Contains significant portion
                elif len(command_name) >= 4:
                    for i in range(len(command_name) - 3):
                        substr = command_name_lower[i:i+4]
                        if substr in cog_name_lower:
                            score = max(score, 50)

                if score > best_score:
                    best_score = score
                    best_match = cog

            if best_score >= 50:  # Minimum match threshold
                target_cog = best_match

        if target_cog:
            # Check if user can see this cog
            if target_cog.qualified_name in self.admin_only_cogs and not self._is_admin(ctx):
                embed = discord.Embed(
                    title="🔒 Access Denied",
                    description=f"The `{command_name}` category requires administrator permissions.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            await self._show_category_help(ctx, target_cog)
            return

        # If still not found, show suggestions
        suggestions = []
        command_name_lower = command_name.lower()

        # Collect command suggestions
        for cmd in self.bot.commands:
            if self._should_show_command(cmd, ctx):
                # Add command name if it matches
                if command_name_lower in cmd.name.lower() or cmd.name.lower() in command_name_lower:
                    suggestions.append(cmd.name)
                # Add aliases if they match
                for alias in cmd.aliases:
                    if command_name_lower in alias.lower() or alias.lower() in command_name_lower:
                        suggestions.append(alias)

        # Collect cog suggestions
        for cog_name, cog in self.bot.cogs.items():
            if cog_name in ['Events', 'Help']:
                continue
            if cog_name in self.admin_only_cogs and not self._is_admin(ctx):
                continue

            if command_name_lower in cog_name.lower() or cog_name.lower() in command_name_lower:
                suggestions.append(cog_name)

        # Remove duplicates and limit
        suggestions = list(dict.fromkeys(suggestions))[:8]

        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"No command or category named `{command_name}` was found.",
            color=0xff0000
        )

        if suggestions:
            embed.add_field(
                name="💡 Did you mean?",
                value="\n".join(f"• `{suggestion}`" for suggestion in suggestions),
                inline=False
            )

        embed.add_field(
            name="🔍 How to get help",
            value=f"`{ctx.prefix}help` - Show all commands\n`{ctx.prefix}help <command>` - Get help for a command\n`{ctx.prefix}cmdlist` - List all commands",
            inline=False
        )

        await ctx.send(embed=embed)

    async def _show_category_help(self, ctx, cog):
        """Show help for a specific category/cog"""
        emoji = self._get_category_emoji(cog.qualified_name)

        # Add admin indicator for admin cogs
        title = f"{emoji} {cog.qualified_name} Commands"
        if cog.qualified_name in self.admin_only_cogs:
            title += " 🛡️"

        embed = discord.Embed(
            title=title,
            description=cog.description or f"Commands in the {cog.qualified_name} category",
            color=0x00ff00
        )

        # Add admin warning for admin categories
        if cog.qualified_name in self.admin_only_cogs:
            embed.description += "\n⚠️ **Admin-only commands**"

        commands_list = []
        for command in cog.get_commands():
            if self._should_show_command(command, ctx):
                desc = command.help or command.brief or "No description"
                if len(desc) > 60:
                    desc = desc[:57] + "..."

                # Add admin indicator for admin commands
                if command.name in self.admin_only_commands:
                    commands_list.append(f"`{ctx.prefix}{command.name}` 🛡️ - {desc}")
                else:
                    commands_list.append(f"`{ctx.prefix}{command.name}` - {desc}")

        if commands_list:
            # Split into multiple fields if too many commands
            for i in range(0, len(commands_list), 8):
                batch = commands_list[i:i+8]
                field_name = "Commands" if i == 0 else "More Commands"
                embed.add_field(
                    name=field_name,
                    value="\n".join(batch),
                    inline=False
                )
        else:
            embed.add_field(
                name="No Available Commands",
                value="No commands are available for your permission level.",
                inline=False
            )

        embed.set_footer(text=f"Use {ctx.prefix}help <command> for detailed information about a command")
        await ctx.send(embed=embed)

    def _get_category_emoji(self, category_name: str) -> str:
        """Get emoji for category"""
        category_emojis = {
            'Admin': '🛡️',
            'Entertainment': '🎮',
            'Utility': '🔧',
            'Information': '📚',
            'General': '⚙️',
            'Games': '🎯',
            'Content': '📖',
            'Tools': '🛠️',
            'Fun': '🎉',
            'Music': '🎵',
            'Moderation': '🔨',
            'AsciiArt': '🎨',
            'Settings': '⚙️',
            'Console': '💻',
            'Reload': '🔄',
            'ErrorHandler': '⚠️',
            'Feedback': '📝',
            'EightBall': '🎱',
            'Weather': '🌤️',
            'Crypto': '💰',
            'Reddit': '🔗',
            'Bible': '📖',
            'Dinosaurs': '🦕'
        }
        return category_emojis.get(category_name, '📁')

    @commands.command(name="cmdlist", aliases=["commandlist"])
    async def command_list(self, ctx):
        """Show a simple list of all available commands"""
        all_commands = []

        for cog_name, cog in self.bot.cogs.items():
            if cog_name in ['Events', 'Help']:
                continue

            # Skip admin cogs for non-admins
            if cog_name in self.admin_only_cogs and not self._is_admin(ctx):
                continue

            for command in cog.get_commands():
                if self._should_show_command(command, ctx):
                    # Add admin indicator
                    if command.name in self.admin_only_commands:
                        all_commands.append(f"{command.name} 🛡️")
                    else:
                        all_commands.append(command.name)

        # Sort commands alphabetically
        all_commands.sort()

        # Create embed
        embed = discord.Embed(
            title="📋 All Available Commands",
            color=0x00ff00
        )

        # Add admin notice if applicable
        if self._is_admin(ctx):
            embed.description = "🛡️ Admin commands are marked with a shield icon"

        # Split into columns
        commands_per_field = 15
        for i in range(0, len(all_commands), commands_per_field):
            batch = all_commands[i:i+commands_per_field]
            command_text = "\n".join([f"`{ctx.prefix}{cmd}`" for cmd in batch])

            field_name = f"Commands ({i+1}-{min(i+commands_per_field, len(all_commands))})"
            embed.add_field(
                name=field_name,
                value=command_text,
                inline=True
            )

        footer_text = f"Total: {len(all_commands)} commands • Use {ctx.prefix}help <command> for details"
        if not self._is_admin(ctx):
            footer_text += " • Admin commands hidden"

        embed.set_footer(text=footer_text)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))