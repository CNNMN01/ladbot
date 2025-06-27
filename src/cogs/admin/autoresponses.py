"""
Auto-response management system - Admin Only
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import json
import re
from utils.decorators import admin_required
from utils.embeds import EmbedBuilder


class AutoResponses(commands.Cog):
    """Auto-response management - Admin controlled"""

    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = EmbedBuilder()
        # Rate limiting to prevent spam
        self.response_cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and respond automatically"""
        # Don't respond to bots or commands
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return

        # Only work in guilds
        if not message.guild:
            return

        guild_id = message.guild.id

        # Check if auto-responses are enabled for this guild
        if not self.bot.get_setting(guild_id, "autoresponses"):
            return

        # Get auto-response configuration
        autoresponse_config = self.bot.get_setting(guild_id, "autoresponse_file")
        if not autoresponse_config:
            return

        # Rate limiting - prevent spam (max 1 response per 5 seconds per channel)
        channel_key = f"{guild_id}_{message.channel.id}"
        current_time = message.created_at.timestamp()

        if channel_key in self.response_cooldowns:
            if current_time - self.response_cooldowns[channel_key] < 5:
                return

        # Check message against triggers
        message_content = message.content.lower()

        for response_data in autoresponse_config:
            if self._check_trigger(message_content, response_data):
                try:
                    # Update cooldown
                    self.response_cooldowns[channel_key] = current_time

                    # Send response
                    await message.channel.send(response_data["response"])

                    # Log the auto-response (for admin monitoring)
                    print(
                        f"Auto-response triggered in {message.guild.name} by {message.author}: '{response_data['trigger']}' -> '{response_data['response']}'")

                    break  # Only send first matching response
                except Exception as e:
                    print(f"Error sending auto-response: {e}")

    def _check_trigger(self, message_content, response_data):
        """Check if message matches trigger"""
        trigger = response_data["trigger"].lower()
        match_type = response_data.get("match_type", "contains")

        if match_type == "exact":
            return message_content.strip() == trigger
        elif match_type == "starts_with":
            return message_content.startswith(trigger)
        elif match_type == "ends_with":
            return message_content.endswith(trigger)
        elif match_type == "regex":
            try:
                return bool(re.search(trigger, message_content))
            except re.error:
                return False
        else:  # contains (default)
            return trigger in message_content

    @commands.group(name="autoresponse", aliases=["ar"])
    async def autoresponse_group(self, ctx):
        """Auto-response management commands (Admin Only)"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🤖 Auto-Response Management",
                description="**Admin-only commands for managing auto-responses**",
                color=0x00ff00
            )
            embed.add_field(
                name="📋 Available Commands",
                value=(
                    f"`{self.bot.command_prefix}autoresponse add <trigger> <response>` - Add new response\n"
                    f"`{self.bot.command_prefix}autoresponse remove <trigger>` - Remove response\n"
                    f"`{self.bot.command_prefix}autoresponse list` - List all responses\n"
                    f"`{self.bot.command_prefix}autoresponse edit <trigger> <new_response>` - Edit response\n"
                    f"`{self.bot.command_prefix}autoresponse clear` - Clear all responses\n"
                    f"`{self.bot.command_prefix}autoresponse status` - Show system status"
                ),
                inline=False
            )
            embed.add_field(
                name="⚙️ Settings",
                value=f"Enable/disable: `{self.bot.command_prefix}settings autoresponses on/off`",
                inline=False
            )
            embed.set_footer(text="🔒 Admin permissions required for all commands")
            await ctx.send(embed=embed)

    @autoresponse_group.command(name="add")
    @admin_required()
    async def add_response(self, ctx, trigger: str, *, response: str):
        """Add a new auto-response (Admin Only)

        Usage: l.autoresponse add "hello" "Hi there! 👋"
        """
        try:
            # Validation
            if len(trigger) > 100:
                await ctx.send("❌ Trigger must be 100 characters or less.")
                return

            if len(response) > 500:
                await ctx.send("❌ Response must be 500 characters or less.")
                return

            # Check for inappropriate content (basic filter)
            if any(word in trigger.lower() for word in ['@everyone', '@here']):
                await ctx.send("❌ Triggers cannot contain mention tags.")
                return

            guild_id = ctx.guild.id
            current_responses = self.bot.get_setting(guild_id, "autoresponse_file") or []

            # Check if trigger already exists
            for existing in current_responses:
                if existing["trigger"].lower() == trigger.lower():
                    await ctx.send(f"❌ Trigger `{trigger}` already exists. Use `edit` to modify it.")
                    return

            # Limit number of auto-responses per server
            if len(current_responses) >= 50:
                await ctx.send("❌ Maximum 50 auto-responses per server. Remove some first.")
                return

            # Add new response
            new_response = {
                "trigger": trigger,
                "response": response,
                "match_type": "contains",
                "created_by": ctx.author.id,
                "created_by_name": str(ctx.author),
                "created_at": ctx.message.created_at.isoformat()
            }

            current_responses.append(new_response)
            await self.bot.update_setting(guild_id, "autoresponse_file", current_responses)

            embed = discord.Embed(
                title="✅ Auto-Response Added",
                color=0x00ff00
            )
            embed.add_field(name="Trigger", value=f"`{trigger}`", inline=True)
            embed.add_field(name="Response", value=response, inline=False)
            embed.add_field(name="Added by", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"Total responses: {len(current_responses)}")

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error adding auto-response: {e}")

    @autoresponse_group.command(name="remove", aliases=["delete"])
    @admin_required()
    async def remove_response(self, ctx, *, trigger: str):
        """Remove an auto-response (Admin Only)

        Usage: l.autoresponse remove "hello"
        """
        try:
            guild_id = ctx.guild.id
            current_responses = self.bot.get_setting(guild_id, "autoresponse_file") or []

            # Find trigger to remove
            removed_response = None
            original_count = len(current_responses)

            for response in current_responses:
                if response["trigger"].lower() == trigger.lower():
                    removed_response = response
                    break

            if not removed_response:
                await ctx.send(f"❌ Trigger `{trigger}` not found.")
                return

            # Remove it
            current_responses = [r for r in current_responses if r["trigger"].lower() != trigger.lower()]
            await self.bot.update_setting(guild_id, "autoresponse_file", current_responses)

            embed = discord.Embed(
                title="✅ Auto-Response Removed",
                color=0x00ff00
            )
            embed.add_field(name="Removed Trigger", value=f"`{trigger}`", inline=True)
            embed.add_field(name="Response Was", value=removed_response["response"], inline=False)
            embed.add_field(name="Removed by", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"Remaining responses: {len(current_responses)}")

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error removing auto-response: {e}")

    @autoresponse_group.command(name="list")
    @admin_required()
    async def list_responses(self, ctx):
        """List all auto-responses (Admin Only)"""
        try:
            guild_id = ctx.guild.id
            current_responses = self.bot.get_setting(guild_id, "autoresponse_file") or []

            if not current_responses:
                embed = discord.Embed(
                    title="📋 Auto-Responses",
                    description="No auto-responses configured.\nUse `l.autoresponse add` to create one!",
                    color=0xffaa00
                )
                await ctx.send(embed=embed)
                return

            # Create multiple embeds if needed
            embeds = []
            items_per_page = 10

            for i in range(0, len(current_responses), items_per_page):
                chunk = current_responses[i:i + items_per_page]

                embed = discord.Embed(
                    title=f"📋 Auto-Responses for {ctx.guild.name}",
                    description=f"Page {i // items_per_page + 1} • Total: {len(current_responses)} responses",
                    color=0x00ff00
                )

                for j, response_data in enumerate(chunk, i + 1):
                    trigger = response_data["trigger"]
                    response = response_data["response"]
                    creator = response_data.get("created_by_name", "Unknown")

                    # Truncate long responses
                    if len(response) > 100:
                        response = response[:97] + "..."

                    embed.add_field(
                        name=f"{j}. {trigger}",
                        value=f"**Response:** {response}\n**Added by:** {creator}",
                        inline=False
                    )

                embeds.append(embed)

            # Send embeds
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                from utils.pagination import PaginatedEmbed
                paginator = PaginatedEmbed(ctx, embeds)
                await paginator.start()

        except Exception as e:
            await ctx.send(f"❌ Error listing auto-responses: {e}")

    @autoresponse_group.command(name="edit")
    @admin_required()
    async def edit_response(self, ctx, trigger: str, *, new_response: str):
        """Edit an existing auto-response (Admin Only)

        Usage: l.autoresponse edit "hello" "Hey there! 🎉"
        """
        try:
            if len(new_response) > 500:
                await ctx.send("❌ Response must be 500 characters or less.")
                return

            guild_id = ctx.guild.id
            current_responses = self.bot.get_setting(guild_id, "autoresponse_file") or []

            # Find and update trigger
            found = False
            old_response = ""

            for response_data in current_responses:
                if response_data["trigger"].lower() == trigger.lower():
                    old_response = response_data["response"]
                    response_data["response"] = new_response
                    response_data["edited_by"] = ctx.author.id
                    response_data["edited_by_name"] = str(ctx.author)
                    response_data["edited_at"] = ctx.message.created_at.isoformat()
                    found = True
                    break

            if not found:
                await ctx.send(f"❌ Trigger `{trigger}` not found.")
                return

            await self.bot.update_setting(guild_id, "autoresponse_file", current_responses)

            embed = discord.Embed(
                title="✅ Auto-Response Updated",
                color=0x00ff00
            )
            embed.add_field(name="Trigger", value=f"`{trigger}`", inline=False)
            embed.add_field(name="Old Response", value=old_response, inline=False)
            embed.add_field(name="New Response", value=new_response, inline=False)
            embed.add_field(name="Updated by", value=ctx.author.mention, inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error editing auto-response: {e}")

    @autoresponse_group.command(name="status")
    @admin_required()
    async def show_status(self, ctx):
        """Show auto-response system status (Admin Only)"""
        try:
            guild_id = ctx.guild.id
            is_enabled = self.bot.get_setting(guild_id, "autoresponses")
            current_responses = self.bot.get_setting(guild_id, "autoresponse_file") or []

            embed = discord.Embed(
                title="🤖 Auto-Response System Status",
                color=0x00ff00 if is_enabled else 0xff0000
            )

            status_emoji = "✅" if is_enabled else "❌"
            embed.add_field(name="Status", value=f"{status_emoji} {'Enabled' if is_enabled else 'Disabled'}",
                            inline=True)
            embed.add_field(name="Total Responses", value=str(len(current_responses)), inline=True)
            embed.add_field(name="Max Allowed", value="50", inline=True)

            if current_responses:
                recent = sorted(current_responses, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
                recent_list = "\n".join([f"• {r['trigger']}" for r in recent])
                embed.add_field(name="Recent Additions", value=recent_list, inline=False)

            embed.add_field(
                name="Settings",
                value=f"Enable: `{self.bot.command_prefix}settings autoresponses on`\nDisable: `{self.bot.command_prefix}settings autoresponses off`",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error getting status: {e}")

    @autoresponse_group.command(name="clear")
    @admin_required()
    async def clear_responses(self, ctx):
        """Clear all auto-responses with confirmation (Admin Only)"""
        try:
            guild_id = ctx.guild.id
            current_responses = self.bot.get_setting(guild_id, "autoresponse_file") or []

            if not current_responses:
                await ctx.send("No auto-responses to clear.")
                return

            # Confirmation with timeout
            embed = discord.Embed(
                title="⚠️ **DANGER: Clear All Auto-Responses**",
                description=(
                    f"This will **permanently delete** all {len(current_responses)} auto-responses.\n\n"
                    "**This action cannot be undone!**\n\n"
                    "Type `DELETE ALL` to confirm or anything else to cancel."
                ),
                color=0xff0000
            )
            await ctx.send(embed=embed)

            # Wait for exact confirmation
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                response = await self.bot.wait_for('message', timeout=30.0, check=check)
                if response.content == "DELETE ALL":
                    await self.bot.update_setting(guild_id, "autoresponse_file", [])

                    embed = discord.Embed(
                        description=f"✅ All {len(current_responses)} auto-responses have been cleared by {ctx.author.mention}",
                        color=0x00ff00
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Cancelled - responses were not deleted.")
            except:
                await ctx.send("❌ Timed out - responses were not deleted.")

        except Exception as e:
            await ctx.send(f"❌ Error clearing auto-responses: {e}")


async def setup(bot):
    await bot.add_cog(AutoResponses(bot))