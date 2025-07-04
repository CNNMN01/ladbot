"""
Auto-Response System - Modern with Full Backwards Compatibility
Clean, safe implementation that supports both old and new command formats
"""

import discord
from discord.ext import commands
import json
import logging
from pathlib import Path
from utils.decorators import admin_required

logger = logging.getLogger(__name__)


class AutoResponseSystem(commands.Cog):
    """Auto-response system"""

    def __init__(self, bot):
        self.bot = bot
        self.name = "AutoResponses"

        # Cache for fast lookups
        self._response_cache = {}
        self._last_response_time = {}  # Anti-spam protection

    def _get_responses_file(self, guild_id):
        """Get the path to guild's responses file"""
        return self.bot.data_manager.data_dir / f"autoresponses_{guild_id}.json"

    def _load_responses(self, guild_id):
        """Load responses for a guild with caching"""
        if guild_id in self._response_cache:
            return self._response_cache[guild_id]

        responses_file = self._get_responses_file(guild_id)
        if not responses_file.exists():
            self._response_cache[guild_id] = []
            return []

        try:
            with open(responses_file, 'r', encoding='utf-8') as f:
                responses = json.load(f)

                # Backwards compatibility: convert old format to new format
                for response in responses:
                    if 'created_by' not in response:
                        response['created_by'] = 'legacy'
                    if 'created_at' not in response:
                        response['created_at'] = 'unknown'

                self._response_cache[guild_id] = responses
                return responses
        except Exception as e:
            logger.error(f"Error loading autoresponses for guild {guild_id}: {e}")
            self._response_cache[guild_id] = []
            return []

    def _save_responses(self, guild_id, responses):
        """Save responses for a guild"""
        responses_file = self._get_responses_file(guild_id)
        try:
            with open(responses_file, 'w', encoding='utf-8') as f:
                json.dump(responses, f, indent=2, ensure_ascii=False)
            self._response_cache[guild_id] = responses
            return True
        except Exception as e:
            logger.error(f"Error saving autoresponses for guild {guild_id}: {e}")
            return False

    def _is_command(self, content):
        """Check if message is a command (comprehensive detection)"""
        # Check bot prefix
        if content.startswith(self.bot.command_prefix):
            return True

        # Check common bot prefixes to avoid conflicts
        common_prefixes = ['!', '?', '$', '%', '&', '*', '+', '=', '/', '\\', '|', '~', '`', '-', '.', '>', '<']
        if any(content.startswith(prefix) for prefix in common_prefixes):
            return True

        # Check if it looks like a command (word + space/end)
        first_word = content.split()[0] if content.split() else ""
        if len(first_word) > 0 and (first_word.islower() and len(first_word) < 20):
            # Could be a command, be safe
            if any(char in first_word for char in ['help', 'ping', 'info', 'reload']):
                return True

        return False

    async def _should_respond(self, message):
        """Determine if we should check for auto-responses - FIXED WITH AWAIT"""
        # Never respond to bots
        if message.author.bot:
            return False

        # Never respond in DMs
        if not message.guild:
            return False

        # Never respond to commands
        if self._is_command(message.content):
            return False

        # Check if autoresponses are enabled for this guild - FIXED WITH AWAIT
        if not await self.bot.get_setting(message.guild.id, "autoresponses"):
            return False

        # Anti-spam: max 1 response per 3 seconds per channel
        channel_key = f"{message.guild.id}_{message.channel.id}"
        now = message.created_at.timestamp()

        if channel_key in self._last_response_time:
            if now - self._last_response_time[channel_key] < 3:
                return False

        return True

    def _find_matching_response(self, message_content, responses):
        """Find the first matching response"""
        message_lower = message_content.lower().strip()

        for response in responses:
            trigger = response.get("trigger", "").lower()
            match_type = response.get("match_type", "contains")

            if match_type == "exact" and message_lower == trigger:
                return response
            elif match_type == "contains" and trigger in message_lower:
                return response
            elif match_type == "starts_with" and message_lower.startswith(trigger):
                return response
            elif match_type == "ends_with" and message_lower.endswith(trigger):
                return response

        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle auto-responses - FIXED WITH AWAIT"""
        try:
            if not await self._should_respond(message):
                return

            responses = self._load_responses(message.guild.id)
            if not responses:
                return

            # Find matching response
            matching_response = self._find_matching_response(message.content, responses)
            if not matching_response:
                return

            # Update anti-spam tracker
            channel_key = f"{message.guild.id}_{message.channel.id}"
            self._last_response_time[channel_key] = message.created_at.timestamp()

            # Send response
            response_text = matching_response.get("response", "")
            if response_text:
                await message.channel.send(response_text)
                logger.info(f"Auto-response sent in {message.guild.name}: '{matching_response['trigger']}' -> '{response_text[:50]}...'")

        except Exception as e:
            # Silent fail - don't break other functionality
            logger.error(f"Auto-response error: {e}")

    # NEW STYLE COMMANDS (Short aliases)
    @commands.group(name="ar", invoke_without_command=True)
    @admin_required()
    async def autoresponse_short(self, ctx):
        """Auto-response management - Short version (Admin Only)"""
        await self._show_help(ctx)

    # OLD STYLE COMMANDS (Full backwards compatibility)
    @commands.group(name="autoresponse", invoke_without_command=True)
    @admin_required()
    async def autoresponse_full(self, ctx):
        """Auto-response management - Full version (Admin Only)"""
        await self._show_help(ctx)

    async def _show_help(self, ctx):
        """Show help for autoresponse commands - FIXED WITH AWAIT"""
        embed = discord.Embed(
            title="🤖 Auto-Response System",
            description="Manage automatic responses for your server",
            color=0x00ff00
        )

        # Show current status
        responses = self._load_responses(ctx.guild.id)
        enabled = await self.bot.get_setting(ctx.guild.id, "autoresponses")  # FIXED WITH AWAIT

        embed.add_field(
            name="📊 Status",
            value=f"**Enabled:** {'✅ Yes' if enabled else '❌ No'}\n**Responses:** {len(responses)}",
            inline=True
        )

        embed.add_field(
            name="🛠️ Commands (Both formats work)",
            value=(
                f"**New:** `{ctx.prefix}ar add <trigger> <response>`\n"
                f"**Old:** `{ctx.prefix}autoresponse add <trigger> <response>`\n\n"
                f"• `add <trigger> <response>` - Add response\n"
                f"• `remove <trigger>` - Remove response\n"
                f"• `list` - Show all responses\n"
                f"• `clear` - Clear all responses\n"
                f"• `toggle` - Enable/disable system"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    # ADD COMMANDS - Both versions
    @autoresponse_short.command(name="add")
    @admin_required()
    async def add_response_short(self, ctx, trigger: str, *, response: str):
        """Add auto-response (short command)"""
        await self._add_response(ctx, trigger, response)

    @autoresponse_full.command(name="add")
    @admin_required()
    async def add_response_full(self, ctx, trigger: str, *, response: str):
        """Add auto-response (full command)"""
        await self._add_response(ctx, trigger, response)

    async def _add_response(self, ctx, trigger: str, response: str):
        """Internal method to add a response - FIXED WITH AWAIT"""
        # Validation
        if len(trigger) > 100:
            return await ctx.send("❌ Trigger must be 100 characters or less.")

        if len(response) > 1000:
            return await ctx.send("❌ Response must be 1000 characters or less.")

        # Prevent command conflicts
        if self._is_command(trigger):
            return await ctx.send("❌ Trigger cannot look like a command.")

        # Load current responses
        responses = self._load_responses(ctx.guild.id)

        # Check for duplicates
        for existing in responses:
            if existing.get("trigger", "").lower() == trigger.lower():
                return await ctx.send(f"❌ Trigger `{trigger}` already exists. Remove it first.")

        # Limit responses per server
        if len(responses) >= 100:
            return await ctx.send("❌ Maximum 100 auto-responses per server.")

        # Add new response
        new_response = {
            "trigger": trigger,
            "response": response,
            "created_by": str(ctx.author.id),
            "created_at": ctx.message.created_at.isoformat(),
            "match_type": "contains"  # Default match type
        }

        responses.append(new_response)

        if self._save_responses(ctx.guild.id, responses):
            embed = discord.Embed(
                title="✅ Auto-Response Added",
                color=0x00ff00
            )
            embed.add_field(name="Trigger", value=f"`{trigger}`", inline=True)
            embed.add_field(name="Response", value=response[:100] + ("..." if len(response) > 100 else ""), inline=False)

            # Show if system is enabled - FIXED WITH AWAIT
            enabled = await self.bot.get_setting(ctx.guild.id, "autoresponses")
            if not enabled:
                embed.add_field(
                    name="⚠️ Notice",
                    value="Auto-responses are currently disabled. Use `l.ar toggle` to enable them.",
                    inline=False
                )

            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to save auto-response.")

    # REMOVE COMMANDS - Both versions
    @autoresponse_short.command(name="remove", aliases=["delete", "del"])
    @admin_required()
    async def remove_response_short(self, ctx, *, trigger: str):
        """Remove auto-response (short command)"""
        await self._remove_response(ctx, trigger)

    @autoresponse_full.command(name="remove", aliases=["delete", "del"])
    @admin_required()
    async def remove_response_full(self, ctx, *, trigger: str):
        """Remove auto-response (full command)"""
        await self._remove_response(ctx, trigger)

    async def _remove_response(self, ctx, trigger: str):
        """Internal method to remove a response"""
        responses = self._load_responses(ctx.guild.id)

        for i, response in enumerate(responses):
            if response.get("trigger", "").lower() == trigger.lower():
                removed = responses.pop(i)

                if self._save_responses(ctx.guild.id, responses):
                    embed = discord.Embed(
                        title="✅ Auto-Response Removed",
                        description=f"Removed trigger: `{removed['trigger']}`",
                        color=0x00ff00
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Failed to save changes.")
                return

        await ctx.send(f"❌ No auto-response found with trigger `{trigger}`.")

    # LIST COMMANDS - Both versions
    @autoresponse_short.command(name="list", aliases=["show"])
    @admin_required()
    async def list_responses_short(self, ctx):
        """List auto-responses (short command)"""
        await self._list_responses(ctx)

    @autoresponse_full.command(name="list", aliases=["show"])
    @admin_required()
    async def list_responses_full(self, ctx):
        """List auto-responses (full command)"""
        await self._list_responses(ctx)

    async def _list_responses(self, ctx):
        """Internal method to list responses - FIXED WITH AWAIT"""
        responses = self._load_responses(ctx.guild.id)

        if not responses:
            return await ctx.send("📝 No auto-responses configured.")

        embed = discord.Embed(
            title=f"🤖 Auto-Responses ({len(responses)})",
            color=0x00ff00
        )

        # Show current status - FIXED WITH AWAIT
        enabled = await self.bot.get_setting(ctx.guild.id, "autoresponses")
        embed.add_field(
            name="📊 System Status",
            value=f"{'✅ Enabled' if enabled else '❌ Disabled'}",
            inline=True
        )

        # Show up to 10 responses
        for i, response in enumerate(responses[:10]):
            trigger = response.get("trigger", "Unknown")
            resp_text = response.get("response", "Unknown")

            # Truncate long responses
            if len(resp_text) > 100:
                resp_text = resp_text[:97] + "..."

            embed.add_field(
                name=f"{i+1}. `{trigger}`",
                value=resp_text,
                inline=False
            )

        if len(responses) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(responses)} responses")

        await ctx.send(embed=embed)

    # CLEAR COMMANDS - Both versions
    @autoresponse_short.command(name="clear")
    @admin_required()
    async def clear_responses_short(self, ctx):
        """Clear auto-responses (short command)"""
        await self._clear_responses(ctx)

    @autoresponse_full.command(name="clear")
    @admin_required()
    async def clear_responses_full(self, ctx):
        """Clear auto-responses (full command)"""
        await self._clear_responses(ctx)

    async def _clear_responses(self, ctx):
        """Internal method to clear responses"""
        responses = self._load_responses(ctx.guild.id)

        if not responses:
            return await ctx.send("📝 No auto-responses to clear.")

        # Confirmation
        embed = discord.Embed(
            title="⚠️ Confirm Clear All",
            description=f"This will delete all {len(responses)} auto-responses.\n\nType `CONFIRM` to proceed.",
            color=0xff9900
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.upper() == "CONFIRM":
                if self._save_responses(ctx.guild.id, []):
                    await ctx.send(f"✅ Cleared all {len(responses)} auto-responses.")
                else:
                    await ctx.send("❌ Failed to clear responses.")
            else:
                await ctx.send("❌ Cancelled.")
        except:
            await ctx.send("❌ Timed out.")

    # TOGGLE COMMANDS - Both versions
    @autoresponse_short.command(name="toggle")
    @admin_required()
    async def toggle_system_short(self, ctx):
        """Toggle auto-responses (short command)"""
        await self._toggle_system(ctx)

    @autoresponse_full.command(name="toggle")
    @admin_required()
    async def toggle_system_full(self, ctx):
        """Toggle auto-responses (full command)"""
        await self._toggle_system(ctx)

    async def _toggle_system(self, ctx):
        """Internal method to toggle system - FIXED WITH AWAIT"""
        try:
            # Get current setting - FIXED WITH AWAIT
            current = await self.bot.get_setting(ctx.guild.id, "autoresponses")
            new_state = not current

            # Update the setting using database - SIMPLIFIED TO USE BOT METHOD
            success = await self.bot.set_setting(ctx.guild.id, "autoresponses", new_state)

            if not success:
                embed = discord.Embed(
                    title="❌ Toggle Failed",
                    description="Failed to update auto-response setting in database.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            # Verify the setting actually changed by checking it again - FIXED WITH AWAIT
            updated_setting = await self.bot.get_setting(ctx.guild.id, "autoresponses")

            if updated_setting == new_state:
                # Setting actually changed - show success
                status = "enabled" if new_state else "disabled"
                embed = discord.Embed(
                    title=f"✅ Auto-Responses {status.title()}",
                    description=f"Auto-response system is now **{status}** for this server.",
                    color=0x00ff00 if new_state else 0xff9900
                )

                if new_state:
                    responses = self._load_responses(ctx.guild.id)
                    embed.add_field(
                        name="📊 Current Responses",
                        value=f"{len(responses)} auto-responses ready",
                        inline=True
                    )
                    embed.add_field(
                        name="✅ Status",
                        value="Auto-responses will now trigger",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="ℹ️ Note",
                        value="Responses are saved but won't trigger until re-enabled",
                        inline=False
                    )

                logger.info(f"🗄️ DATABASE: Auto-responses {status} for guild {ctx.guild.id}")
            else:
                # Setting didn't actually change - show error
                embed = discord.Embed(
                    title="❌ Toggle Failed",
                    description="Failed to update auto-response setting. The setting may not have changed.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🔍 Debug Info",
                    value=f"Current: {current}, Attempted: {new_state}, Actual: {updated_setting}",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error toggling autoresponses: {e}")
            await ctx.send("❌ Error toggling auto-response system.")


async def setup(bot):
    await bot.add_cog(AutoResponseSystem(bot))