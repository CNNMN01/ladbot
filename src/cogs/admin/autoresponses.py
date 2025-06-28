"""
Auto-response system for Ladbot - Enhanced Version
"""

import discord
from discord.ext import commands
import json
import logging
from utils.decorators import admin_required
from utils.validators import sanitize_input

logger = logging.getLogger(__name__)


class AutoResponses(commands.Cog):
    """Auto-response system with admin controls"""

    def __init__(self, bot):
        self.bot = bot
        self.response_cache = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle auto-responses to messages"""
        # CRITICAL: Ignore bot messages and commands to prevent conflicts
        if message.author.bot:
            return

        # CRITICAL: Ignore any message that starts with the bot prefix
        if message.content.startswith(self.bot.command_prefix):
            return

        # CRITICAL: Ignore any message that starts with common prefixes
        common_prefixes = ['!', '?', '$', '%', '&', '*', '+', '=', '/', '\\', '|', '~', '`']
        if any(message.content.startswith(prefix) for prefix in common_prefixes):
            return

        # Check if auto-responses are enabled for this guild
        if not message.guild:
            return

        guild_id = message.guild.id
        if not self.bot.get_setting(guild_id, "autoresponses"):
            return

        # Get responses for this guild
        responses = self._get_guild_responses(guild_id)
        if not responses:
            return

        # Check for trigger matches (case-insensitive)
        message_lower = message.content.lower().strip()

        for response_data in responses:
            trigger = response_data.get("trigger", "").lower()
            response_text = response_data.get("response", "")

            if not trigger or not response_text:
                continue

            # Exact match or word boundary match
            if trigger == message_lower or f" {trigger} " in f" {message_lower} ":
                try:
                    # Add a small delay to feel more natural
                    await message.channel.typing()
                    await asyncio.sleep(1)

                    # Send the response
                    await message.channel.send(response_text)
                    logger.info(f"Auto-response triggered in {message.guild.name}: '{trigger}' -> '{response_text[:50]}...'")
                    break  # Only respond to first match

                except discord.Forbidden:
                    logger.warning(f"No permission to send auto-response in {message.guild.name}")
                except Exception as e:
                    logger.error(f"Error sending auto-response: {e}")

    def _get_guild_responses(self, guild_id):
        """Get auto-responses for a guild with caching"""
        if guild_id in self.response_cache:
            return self.response_cache[guild_id]

        try:
            responses_file = self.bot.data_manager.data_dir / f"autoresponses_{guild_id}.json"
            if responses_file.exists():
                with open(responses_file, 'r') as f:
                    responses = json.load(f)
                    self.response_cache[guild_id] = responses
                    return responses
        except Exception as e:
            logger.error(f"Error loading auto-responses for guild {guild_id}: {e}")

        return []

    def _save_guild_responses(self, guild_id, responses):
        """Save auto-responses for a guild"""
        try:
            responses_file = self.bot.data_manager.data_dir / f"autoresponses_{guild_id}.json"
            with open(responses_file, 'w') as f:
                json.dump(responses, f, indent=2)

            # Update cache
            self.response_cache[guild_id] = responses
            return True
        except Exception as e:
            logger.error(f"Error saving auto-responses for guild {guild_id}: {e}")
            return False

    @commands.group(invoke_without_command=True)
    @admin_required()
    async def autoresponse(self, ctx):
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

    @autoresponse.command(name="add")
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

            # Prevent command conflicts
            if trigger.lower().startswith(self.bot.command_prefix.lower()):
                await ctx.send("❌ Triggers cannot start with the bot command prefix.")
                return

            guild_id = ctx.guild.id
            current_responses = self._get_guild_responses(guild_id)

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
                "response": sanitize_input(response, max_length=500),
                "created_by": ctx.author.id,
                "created_at": ctx.message.created_at.isoformat()
            }

            current_responses.append(new_response)

            if self._save_guild_responses(guild_id, current_responses):
                embed = discord.Embed(
                    title="✅ Auto-Response Added",
                    description=f"**Trigger:** `{trigger}`\n**Response:** {response[:100]}{'...' if len(response) > 100 else ''}",
                    color=0x00ff00
                )
                await ctx.send(embed=embed)
                logger.info(f"Auto-response added by {ctx.author} in {ctx.guild.name}: '{trigger}'")
            else:
                await ctx.send("❌ Failed to save auto-response. Please try again.")

        except Exception as e:
            logger.error(f"Error adding auto-response: {e}")
            await ctx.send("❌ An error occurred while adding the auto-response.")

    @autoresponse.command(name="remove", aliases=["delete"])
    @admin_required()
    async def remove_response(self, ctx, *, trigger: str):
        """Remove an auto-response (Admin Only)"""
        try:
            guild_id = ctx.guild.id
            current_responses = self._get_guild_responses(guild_id)

            # Find and remove the response
            for i, response in enumerate(current_responses):
                if response["trigger"].lower() == trigger.lower():
                    removed_response = current_responses.pop(i)

                    if self._save_guild_responses(guild_id, current_responses):
                        embed = discord.Embed(
                            title="✅ Auto-Response Removed",
                            description=f"**Trigger:** `{removed_response['trigger']}`",
                            color=0x00ff00
                        )
                        await ctx.send(embed=embed)
                        logger.info(f"Auto-response removed by {ctx.author} in {ctx.guild.name}: '{trigger}'")
                    else:
                        await ctx.send("❌ Failed to save changes. Please try again.")
                    return

            await ctx.send(f"❌ No auto-response found with trigger `{trigger}`.")

        except Exception as e:
            logger.error(f"Error removing auto-response: {e}")
            await ctx.send("❌ An error occurred while removing the auto-response.")

    @autoresponse.command(name="list")
    @admin_required()
    async def list_responses(self, ctx):
        """List all auto-responses for this server (Admin Only)"""
        try:
            guild_id = ctx.guild.id
            responses = self._get_guild_responses(guild_id)

            if not responses:
                await ctx.send("📝 No auto-responses configured for this server.")
                return

            embed = discord.Embed(
                title=f"🤖 Auto-Responses for {ctx.guild.name}",
                description=f"Total: {len(responses)} response(s)",
                color=0x00ff00
            )

            # Show responses in chunks
            for i, response in enumerate(responses[:20]):  # Limit to 20 for embed size
                trigger = response.get("trigger", "Unknown")
                response_text = response.get("response", "Unknown")

                # Truncate long responses
                if len(response_text) > 100:
                    response_text = response_text[:97] + "..."

                embed.add_field(
                    name=f"{i+1}. `{trigger}`",
                    value=response_text,
                    inline=False
                )

            if len(responses) > 20:
                embed.set_footer(text=f"Showing first 20 of {len(responses)} responses")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing auto-responses: {e}")
            await ctx.send("❌ An error occurred while listing auto-responses.")

    @autoresponse.command(name="clear")
    @admin_required()
    async def clear_responses(self, ctx):
        """Clear all auto-responses for this server (Admin Only)"""
        try:
            guild_id = ctx.guild.id
            current_responses = self._get_guild_responses(guild_id)

            if not current_responses:
                await ctx.send("📝 No auto-responses to clear.")
                return

            count = len(current_responses)

            if self._save_guild_responses(guild_id, []):
                embed = discord.Embed(
                    title="✅ Auto-Responses Cleared",
                    description=f"Removed {count} auto-response(s) from this server.",
                    color=0x00ff00
                )
                await ctx.send(embed=embed)
                logger.info(f"All auto-responses cleared by {ctx.author} in {ctx.guild.name}")
            else:
                await ctx.send("❌ Failed to clear auto-responses. Please try again.")

        except Exception as e:
            logger.error(f"Error clearing auto-responses: {e}")
            await ctx.send("❌ An error occurred while clearing auto-responses.")


async def setup(bot):
    await bot.add_cog(AutoResponses(bot))