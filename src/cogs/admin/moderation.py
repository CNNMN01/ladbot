"""
Basic moderation commands for administrators
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from discord.ext import commands
from utils.decorators import admin_required
import logging

logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    """Basic moderation commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @admin_required()
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member from the server (Admin Only)

        Usage: l.kick @user [reason]
        """
        try:
            # Check if bot can kick this user
            if member.top_role >= ctx.guild.me.top_role:
                await ctx.send("❌ I cannot kick this user - they have a higher or equal role to me.")
                return

            # Check if admin is trying to kick someone with higher role
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ You cannot kick someone with a higher or equal role.")
                return

            await member.kick(reason=f"Kicked by {ctx.author}: {reason}")

            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"**{member}** has been kicked from the server.",
                color=0xff9900
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")

            await ctx.send(embed=embed)
            logger.info(f"Admin {ctx.author} kicked {member} - Reason: {reason}")

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick members.")
        except Exception as e:
            await ctx.send(f"❌ Error kicking member: {e}")

    @commands.command()
    @admin_required()
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a member from the server (Admin Only)

        Usage: l.ban @user [reason]
        """
        try:
            # Check if bot can ban this user
            if member.top_role >= ctx.guild.me.top_role:
                await ctx.send("❌ I cannot ban this user - they have a higher or equal role to me.")
                return

            # Check if admin is trying to ban someone with higher role
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ You cannot ban someone with a higher or equal role.")
                return

            await member.ban(reason=f"Banned by {ctx.author}: {reason}")

            embed = discord.Embed(
                title="🔨 Member Banned",
                description=f"**{member}** has been banned from the server.",
                color=0xff0000
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")

            await ctx.send(embed=embed)
            logger.warning(f"Admin {ctx.author} banned {member} - Reason: {reason}")

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban members.")
        except Exception as e:
            await ctx.send(f"❌ Error banning member: {e}")

    @commands.command()
    @admin_required()
    async def unban(self, ctx, user_id: int, *, reason="No reason provided"):
        """Unban a user by their ID (Admin Only)

        Usage: l.unban <user_id> [reason]
        """
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author}: {reason}")

            embed = discord.Embed(
                title="✅ Member Unbanned",
                description=f"**{user}** has been unbanned from the server.",
                color=0x00ff00
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"User ID: {user.id}")

            await ctx.send(embed=embed)
            logger.info(f"Admin {ctx.author} unbanned {user} - Reason: {reason}")

        except discord.NotFound:
            await ctx.send("❌ User not found or not banned.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban members.")
        except Exception as e:
            await ctx.send(f"❌ Error unbanning user: {e}")

    @commands.command()
    @admin_required()
    async def purge(self, ctx, amount: int = 10):
        """Delete multiple messages (Admin Only)

        Usage: l.purge [amount]
        """
        try:
            if amount > 100:
                await ctx.send("❌ Cannot purge more than 100 messages at once.")
                return

            if amount < 1:
                await ctx.send("❌ Must purge at least 1 message.")
                return

            # Delete the command message first
            await ctx.message.delete()

            # Delete the specified amount of messages
            deleted = await ctx.channel.purge(limit=amount)

            embed = discord.Embed(
                title="🗑️ Messages Purged",
                description=f"Deleted **{len(deleted)}** messages.",
                color=0x00ff00
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)

            # Send confirmation and auto-delete after 5 seconds
            msg = await ctx.send(embed=embed, delete_after=5)
            logger.info(f"Admin {ctx.author} purged {len(deleted)} messages in {ctx.channel}")

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages.")
        except Exception as e:
            await ctx.send(f"❌ Error purging messages: {e}")


async def setup(bot):
    await bot.add_cog(Moderation(bot))