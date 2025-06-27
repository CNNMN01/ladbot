"""
Ping command - Check bot latency
"""

import sys


import discord
from discord.ext import commands


class Ping(commands.Cog):
    """Ping command to check bot latency"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Check the bot's latency"""
        try:
            latency_ms = round(self.bot.latency * 1000)

            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Hey, {ctx.author.mention}. Current ping is: `{latency_ms}ms`",
                color=0x00ff00
            )

            # Use modern avatar access
            try:
                avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                embed.set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=avatar_url
                )
            except:
                embed.set_footer(text=f"Requested by {ctx.author.display_name}")

            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error in ping command: {e}")
            await ctx.send(f"🏓 Pong! Latency: {round(self.bot.latency * 1000)}ms")

    @commands.command()
    async def amiadmin(self, ctx):
        """Check if you have admin permissions"""
        try:
            # Check Discord server admin permission
            has_server_admin = ctx.author.guild_permissions.administrator if ctx.guild else False

            # Check bot admin list
            is_bot_admin = ctx.author.id in ctx.bot.settings.admin_ids

            embed = discord.Embed(
                title=f"🔍 Admin Status for {ctx.author.display_name}",
                color=0x00ff00 if (has_server_admin or is_bot_admin) else 0xff0000
            )

            embed.add_field(
                name="Your Discord User ID",
                value=str(ctx.author.id),
                inline=False
            )

            embed.add_field(
                name="Server Administrator Permission",
                value="✅ Yes" if has_server_admin else "❌ No",
                inline=True
            )

            embed.add_field(
                name="Bot Admin List",
                value="✅ Yes" if is_bot_admin else "❌ No",
                inline=True
            )

            # Show the actual admin IDs for debugging
            embed.add_field(
                name="Bot Admin IDs",
                value=str(ctx.bot.settings.admin_ids) if ctx.bot.settings.admin_ids else "None configured",
                inline=False
            )

            # Overall status
            is_admin = has_server_admin or is_bot_admin
            embed.add_field(
                name="**Overall Admin Status**",
                value=f"**{'✅ ADMIN' if is_admin else '❌ NOT ADMIN'}**",
                inline=False
            )

            if not is_admin:
                embed.add_field(
                    name="How to Become Admin",
                    value="• Get Administrator permission in this server, OR\n• Ask bot owner to add your ID to bot admin list",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error checking admin status: {e}")


async def setup(bot):
    await bot.add_cog(Ping(bot))