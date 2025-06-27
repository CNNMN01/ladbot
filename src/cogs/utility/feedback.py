"""
Feedback command for user suggestions
"""

import sys


import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class Feedback(commands.Cog):
    """User feedback system"""

    def __init__(self, bot):
        self.bot = bot

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

        # Try to send to admin channel (silently)
        console_channel_id = getattr(self.bot.config, 'console_channel_id', None)

        if console_channel_id:
            try:
                admin_channel = self.bot.get_channel(console_channel_id)
                if admin_channel:
                    feedback_embed = discord.Embed(
                        title="📝 New Feedback",
                        description=message,
                        color=0x00ff00
                    )
                    feedback_embed.add_field(
                        name="User",
                        value=f"{ctx.author} ({ctx.author.id})",
                        inline=True
                    )
                    feedback_embed.add_field(
                        name="Server",
                        value=f"{ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "DM",
                        inline=True
                    )
                    feedback_embed.add_field(
                        name="Channel",
                        value=f"#{ctx.channel.name}" if hasattr(ctx.channel, 'name') else "DM",
                        inline=True
                    )

                    await admin_channel.send(embed=feedback_embed)
            except Exception as e:
                # Log error but don't tell user about it
                logger.error(f"Failed to send feedback to admin channel: {e}")

        # Simple, clean response to user
        embed = discord.Embed(
            description="✅ Thank you for your feedback! Your message has been sent to the developers.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Feedback(bot))