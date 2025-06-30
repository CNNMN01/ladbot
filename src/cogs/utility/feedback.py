"""
Enhanced Feedback command for user suggestions
"""

import sys
import os

import discord
from discord.ext import commands
from utils.decorators import admin_required
import logging

logger = logging.getLogger(__name__)


class Feedback(commands.Cog):
    """User feedback system"""

    def __init__(self, bot):
        self.bot = bot

    def _get_console_channel_id(self):
        """Get console channel ID from multiple possible sources"""
        # Try multiple ways to get the channel ID
        possible_sources = [
            # Environment variables
            os.getenv('CONSOLE_CHANNEL_ID'),
            os.getenv('console_channel_id'),
            os.getenv('ADMIN_CHANNEL_ID'),
            os.getenv('FEEDBACK_CHANNEL_ID'),
            os.getenv('ERROR_CHANNEL_ID'),

            # Bot config attributes
            getattr(self.bot.config, 'CONSOLE_CHANNEL_ID', None),
            getattr(self.bot.config, 'console_channel_id', None),
            getattr(self.bot.config, 'admin_channel_id', None),
            getattr(self.bot.config, 'feedback_channel_id', None),

            # Bot settings attributes
            getattr(getattr(self.bot, 'settings', None), 'CONSOLE_CHANNEL_ID', None),
            getattr(getattr(self.bot, 'settings', None), 'console_channel_id', None),
        ]

        # Return the first valid channel ID found
        for source in possible_sources:
            if source:
                try:
                    return int(source)
                except (ValueError, TypeError):
                    continue

        return None

    @commands.command()
    async def feedback(self, ctx, *, message: str = None):
        """Send feedback to the bot developers

        Usage: l.feedback <your message>
        """
        if not message:
            embed = discord.Embed(
                description=f"❌ Please provide a feedback message! Use: `{self.bot.command_prefix}feedback <your message>`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        # Log feedback (always works)
        logger.info(f"Feedback from {ctx.author} ({ctx.author.id}): {message}")

        # Try to send to admin channel
        console_channel_id = self._get_console_channel_id()

        # Debug logging
        logger.info(f"Console channel ID found: {console_channel_id}")

        admin_notification_sent = False

        if console_channel_id:
            try:
                admin_channel = self.bot.get_channel(console_channel_id)
                logger.info(f"Admin channel object: {admin_channel}")

                if admin_channel:
                    feedback_embed = discord.Embed(
                        title="📝 New Feedback",
                        description=message,
                        color=0x00ff00,
                        timestamp=ctx.message.created_at
                    )
                    feedback_embed.add_field(
                        name="👤 User",
                        value=f"{ctx.author.mention}\n`{ctx.author}` ({ctx.author.id})",
                        inline=True
                    )
                    feedback_embed.add_field(
                        name="🏠 Server",
                        value=f"{ctx.guild.name}\n`{ctx.guild.id}`" if ctx.guild else "Direct Message",
                        inline=True
                    )
                    feedback_embed.add_field(
                        name="💬 Channel",
                        value=f"#{ctx.channel.name}\n`{ctx.channel.id}`" if hasattr(ctx.channel, 'name') else "DM",
                        inline=True
                    )

                    # Add a direct link to the original message if possible
                    if ctx.guild:
                        message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
                        feedback_embed.add_field(
                            name="🔗 Message Link",
                            value=f"[Jump to Message]({message_link})",
                            inline=False
                        )

                    await admin_channel.send(embed=feedback_embed)
                    admin_notification_sent = True
                    logger.info(f"Successfully sent feedback to admin channel {console_channel_id}")

                else:
                    logger.warning(f"Admin channel {console_channel_id} not found or not accessible")

            except discord.Forbidden:
                logger.error(f"No permission to send message to admin channel {console_channel_id}")
            except discord.NotFound:
                logger.error(f"Admin channel {console_channel_id} not found")
            except Exception as e:
                logger.error(f"Failed to send feedback to admin channel {console_channel_id}: {e}")
        else:
            logger.warning("No console channel ID configured for feedback notifications")

        # Send confirmation to user
        if admin_notification_sent:
            embed = discord.Embed(
                description="✅ Thank you for your feedback! Your message has been sent to the developers and they will review it soon.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                description="✅ Thank you for your feedback! Your message has been logged for review.",
                color=0x00ff00
            )

        embed.set_footer(text="Your feedback helps improve the bot!")
        await ctx.send(embed=embed)

    @commands.command()
    @admin_required()
    async def feedback_debug(self, ctx):
        """Debug command to check feedback configuration (Admin only)"""
        console_channel_id = self._get_console_channel_id()

        embed = discord.Embed(
            title="🔧 Feedback Debug Information",
            color=0x0099ff
        )

        # Show channel ID detection
        embed.add_field(
            name="Console Channel ID",
            value=f"`{console_channel_id}`" if console_channel_id else "❌ Not found",
            inline=False
        )

        # Test channel access
        if console_channel_id:
            admin_channel = self.bot.get_channel(console_channel_id)
            embed.add_field(
                name="Channel Access",
                value=f"✅ `{admin_channel}`" if admin_channel else "❌ Channel not accessible",
                inline=False
            )

            # Test permissions
            if admin_channel:
                permissions = admin_channel.permissions_for(ctx.guild.me)
                can_send = permissions.send_messages
                can_embed = permissions.embed_links

                embed.add_field(
                    name="Bot Permissions",
                    value=f"Send Messages: {'✅' if can_send else '❌'}\nEmbed Links: {'✅' if can_embed else '❌'}",
                    inline=False
                )

        # Show environment variables
        env_vars = []
        for var in ['CONSOLE_CHANNEL_ID', 'console_channel_id', 'ADMIN_CHANNEL_ID', 'FEEDBACK_CHANNEL_ID']:
            value = os.getenv(var)
            if value:
                env_vars.append(f"{var}: `{value}`")

        if env_vars:
            embed.add_field(
                name="Environment Variables",
                value="\n".join(env_vars),
                inline=False
            )
        else:
            embed.add_field(
                name="Environment Variables",
                value="❌ No relevant environment variables found",
                inline=False
            )

        # Show bot configuration sources
        config_sources = []

        # Check bot.config attributes
        for attr in ['CONSOLE_CHANNEL_ID', 'console_channel_id', 'admin_channel_id']:
            value = getattr(self.bot.config, attr, None)
            if value:
                config_sources.append(f"bot.config.{attr}: `{value}`")

        # Check bot.settings attributes
        if hasattr(self.bot, 'settings'):
            for attr in ['CONSOLE_CHANNEL_ID', 'console_channel_id']:
                value = getattr(self.bot.settings, attr, None)
                if value:
                    config_sources.append(f"bot.settings.{attr}: `{value}`")

        if config_sources:
            embed.add_field(
                name="Bot Configuration",
                value="\n".join(config_sources),
                inline=False
            )
        else:
            embed.add_field(
                name="Bot Configuration",
                value="❌ No configuration sources found",
                inline=False
            )

        embed.set_footer(text="Use this information to troubleshoot feedback delivery issues")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Feedback(bot))