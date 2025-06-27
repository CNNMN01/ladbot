"""
Simple, reliable help command with proper admin filtering
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from discord.ext import commands
from utils.pagination import PaginatedEmbed


class Help(commands.Cog):
    """Simple help command system with admin filtering"""

    def __init__(self, bot):
        self.bot = bot
        # Remove the default help command
        bot.remove_command('help')

        # Define admin-only commands that should be hidden from public help
        self.admin_only_commands = {
            'amiadmin', 'autoresponse', 'clearmodules', 'forcereload',
            'logs', 'reload', 'settings', 'status', 'botinfo', 'console',
            'clearlogs', 'kick', 'ban', 'unban', 'purge'  # Added moderation commands
        }

        # Define admin-only cogs
        self.admin_only_cogs = {'Admin'}

    def _is_admin(self, ctx) -> bool:
        """Check if user is admin"""
        # Handle different config attribute names safely
        admin_ids = []
        try:
            # Try lowercase first
            if hasattr(ctx.bot.config, 'admin_ids'):
                admin_ids = ctx.bot.config.admin_ids
            # Try uppercase if lowercase doesn't exist
            elif hasattr(ctx.bot.config, 'ADMIN_IDS'):
                admin_ids = ctx.bot.config.ADMIN_IDS
            # Fallback to empty list
            else:
                admin_ids = []
        except Exception:
            admin_ids = []

        return (
            ctx.author.guild_permissions.administrator or
            ctx.author.id in admin_ids
        )

    def _should_show_command(self, command, ctx) -> bool:
        """Determine if a command should be shown to this user"""
        # Always hide hidden commands
        if command.hidden:
            return False

        # Check if command is admin-only
        if command.name in self.admin_only_commands:
            return self._is_admin(ctx)

        # Check if command's cog is admin-only
        if command.cog and command.cog.qualified_name in self.admin_only_cogs:
            return self._is_admin(ctx)

        # Show all other commands
        return True

    @commands.command(name="help", aliases=["h"])
    async def help_command(self, ctx, *, command_name: str = None):
        """Show help information

        Usage:
        l.help - Show all commands
        l.help <command> - Show help for specific command
        """
        if command_name:
            await self._show_command_help(ctx, command_name)
        else:
            await self._show_all_commands(ctx)

    async def _show_all_commands(self, ctx):
        """Show all available commands organized by category"""

        is_admin = self._is_admin(ctx)

        # Get all cogs and their commands
        cog_commands = {}

        for cog_name, cog in self.bot.cogs.items():
            # Skip certain cogs from help
            if cog_name in ['Events', 'Help']:
                continue

            # Skip admin-only cogs for non-admins
            if cog_name in self.admin_only_cogs and not is_admin:
                continue

            commands_list = []
            for command in cog.get_commands():
                if self._should_show_command(command, ctx):
                    # Get command description
                    desc = command.help or command.brief or "No description"
                    if len(desc) > 50:
                        desc = desc[:47] + "..."
                    commands_list.append((command.name, desc))

            if commands_list:
                cog_commands[cog_name] = commands_list

        # Create embeds for each category
        embeds = []

        # Main help embed
        main_embed = discord.Embed(
            title="🤖 Ladbot Help",
            description="Here are all available commands organized by category!",
            color=0x00ff00
        )

        main_embed.add_field(
            name="📋 How to Use",
            value=f"`{ctx.prefix}help <command>` - Get detailed help for a command\n`{ctx.prefix}help <category>` - See commands in a category",
            inline=False
        )

        # Add category overview
        category_list = []
        for cog_name in cog_commands.keys():
            emoji = self._get_category_emoji(cog_name)
            category_list.append(f"{emoji} **{cog_name}** ({len(cog_commands[cog_name])} commands)")

        if category_list:
            main_embed.add_field(
                name="📚 Command Categories",
                value="\n".join(category_list),
                inline=False
            )

        main_embed.add_field(
            name="💡 Examples",
            value=f"`{ctx.prefix}help ping`\n`{ctx.prefix}help minesweeper`\n`{ctx.prefix}help Entertainment`",
            inline=False
        )

        # Add admin notice if user is admin
        if is_admin:
            main_embed.add_field(
                name="🛡️ Admin Status",
                value="You have admin permissions - seeing all commands including admin-only ones.",
                inline=False
            )

        total_commands = sum(len(cmds) for cmds in cog_commands.values())
        footer_text = f"Total Commands: {total_commands}"
        if not is_admin:
            footer_text += " • Admin commands hidden"

        main_embed.set_footer(text=footer_text)
        embeds.append(main_embed)

        # Create embeds for each category
        for cog_name, commands_list in cog_commands.items():
            emoji = self._get_category_emoji(cog_name)

            # Add admin indicator for admin cogs
            title = f"{emoji} {cog_name} Commands"
            if cog_name in self.admin_only_cogs:
                title += " 🛡️"

            embed = discord.Embed(
                title=title,
                description=f"Commands in the {cog_name} category:",
                color=0x00ff00
            )

            # Add admin warning for admin categories
            if cog_name in self.admin_only_cogs:
                embed.description += "\n⚠️ **Admin-only commands**"

            # Add commands in batches to avoid hitting field limits
            for i in range(0, len(commands_list), 10):
                batch = commands_list[i:i+10]

                cmd_text = ""
                for cmd_name, cmd_desc in batch:
                    # Add admin indicator for admin commands
                    if cmd_name in self.admin_only_commands:
                        cmd_text += f"`{ctx.prefix}{cmd_name}` 🛡️ - {cmd_desc}\n"
                    else:
                        cmd_text += f"`{ctx.prefix}{cmd_name}` - {cmd_desc}\n"

                field_name = f"Commands" if i == 0 else f"Commands (continued)"
                embed.add_field(
                    name=field_name,
                    value=cmd_text,
                    inline=False
                )

            embed.set_footer(text=f"Use {ctx.prefix}help <command> for detailed information")
            embeds.append(embed)

        # Send paginated embeds
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            paginator = PaginatedEmbed(ctx, embeds, timeout=120)
            await paginator.start()

    async def _show_command_help(self, ctx, command_name: str):
        """Show help for a specific command or category"""

        # First, try to find it as a command
        command = self.bot.get_command(command_name.lower())

        if command:
            # Check if user can see this command
            if not self._should_show_command(command, ctx):
                embed = discord.Embed(
                    title="🔒 Access Denied",
                    description=f"The command `{command_name}` requires administrator permissions.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

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

        # Try to find it as a cog/category
        cog = self.bot.get_cog(command_name.title())
        if cog:
            # Check if user can see this cog
            if cog.qualified_name in self.admin_only_cogs and not self._is_admin(ctx):
                embed = discord.Embed(
                    title="🔒 Access Denied",
                    description=f"The `{command_name}` category requires administrator permissions.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            await self._show_category_help(ctx, cog)
            return

        # Command not found
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"No command or category named `{command_name}` was found.",
            color=0xff0000
        )

        # Suggest similar commands (only ones they can access)
        all_commands = [cmd.name for cmd in self.bot.commands if self._should_show_command(cmd, ctx)]
        all_cogs = [name for name in self.bot.cogs.keys()
                   if name not in self.admin_only_cogs or self._is_admin(ctx)]

        suggestions = []
        search_term = command_name.lower()

        # Simple similarity check
        for cmd_name in all_commands + all_cogs:
            if search_term in cmd_name.lower() or cmd_name.lower().startswith(search_term):
                suggestions.append(cmd_name)

        if suggestions:
            embed.add_field(
                name="💡 Did you mean?",
                value="\n".join(f"• `{suggestion}`" for suggestion in suggestions[:5]),
                inline=False
            )

        embed.add_field(
            name="🔍 How to get help",
            value=f"`{ctx.prefix}help` - Show all commands\n`{ctx.prefix}help <command>` - Get help for a command",
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
            'Moderation': '🔨'
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