"""
Reddit browsing commands
"""

import sys


import discord
from discord.ext import commands
import aiohttp
import json
import random
from utils.decorators import guild_setting_enabled, typing_context
from utils.pagination import PaginatedEmbed


class Reddit(commands.Cog):
    """Reddit browsing commands"""

    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://www.reddit.com"
        self.user_agent = "Ladbot/2.0 Discord Bot"

    @commands.command(aliases=["r"])
    @guild_setting_enabled("reddit")
    @typing_context()
    async def reddit(self, ctx, subreddit: str = None, sort: str = "hot", limit: int = 5):
        """Browse Reddit posts from a subreddit

        Usage: l.reddit <subreddit> [sort] [limit]
        Examples:
        l.reddit funny
        l.reddit gaming hot 3
        l.reddit aww top 10

        Sort options: hot, new, top, rising
        """
        if not subreddit:
            embed = discord.Embed(
                title="📱 Reddit Browser",
                description="Browse Reddit posts right in Discord!",
                color=0xFF4500
            )

            embed.add_field(
                name="Usage",
                value=f"`{self.bot.command_prefix}reddit <subreddit> [sort] [limit]`",
                inline=False
            )

            embed.add_field(
                name="Examples",
                value=(
                    f"`{self.bot.command_prefix}reddit funny` - Hot posts from r/funny\n"
                    f"`{self.bot.command_prefix}reddit gaming new 3` - 3 new posts from r/gaming\n"
                    f"`{self.bot.command_prefix}reddit aww top 10` - Top 10 posts from r/aww"
                ),
                inline=False
            )

            embed.add_field(
                name="Sort Options",
                value="**hot**, **new**, **top**, **rising**",
                inline=False
            )

            embed.add_field(
                name="Popular Subreddits",
                value="funny, gaming, aww, memes, pics, todayilearned, askreddit",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        # Validate inputs
        if limit > 25:
            limit = 25
        elif limit < 1:
            limit = 5

        if sort not in ["hot", "new", "top", "rising"]:
            sort = "hot"

        # Clean subreddit name
        if subreddit.startswith("r/"):
            subreddit = subreddit[2:]

        try:
            # Fetch Reddit data
            url = f"{self.base_url}/r/{subreddit}/{sort}.json"
            headers = {"User-Agent": self.user_agent}
            params = {"limit": limit}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 404:
                        embed = discord.Embed(
                            description=f"❌ Subreddit `r/{subreddit}` not found or is private.",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                        return
                    elif response.status != 200:
                        await ctx.send("❌ Reddit is currently unavailable. Please try again later.")
                        return

                    data = await response.json()

            posts = data["data"]["children"]

            if not posts:
                embed = discord.Embed(
                    description=f"❌ No posts found in r/{subreddit}",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            # Create embeds for each post
            embeds = []
            for i, post_data in enumerate(posts, 1):
                post = post_data["data"]
                embed = self._create_post_embed(post, subreddit, i, len(posts))
                embeds.append(embed)

            # Send paginated embeds
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                paginator = PaginatedEmbed(ctx, embeds, timeout=120)
                await paginator.start()

        except Exception as e:
            await ctx.send(f"❌ Error fetching Reddit posts: {e}")

    def _create_post_embed(self, post, subreddit, post_num, total_posts):
        """Create an embed for a Reddit post"""
        title = post.get("title", "No Title")
        if len(title) > 256:
            title = title[:253] + "..."

        author = post.get("author", "Unknown")
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        url = f"https://reddit.com{post.get('permalink', '')}"

        # Content
        selftext = post.get("selftext", "")
        if selftext and len(selftext) > 500:
            selftext = selftext[:497] + "..."

        # Create embed
        embed = discord.Embed(
            title=title,
            url=url,
            description=selftext if selftext else None,
            color=0xFF4500
        )

        # Post info
        embed.add_field(
            name="📊 Stats",
            value=f"⬆️ {score:,} upvotes\n💬 {num_comments:,} comments",
            inline=True
        )

        embed.add_field(
            name="👤 Author",
            value=f"u/{author}",
            inline=True
        )

        embed.add_field(
            name="📱 Subreddit",
            value=f"r/{subreddit}",
            inline=True
        )

        # Handle images
        if post.get("post_hint") == "image" and not post.get("over_18", False):
            embed.set_image(url=post.get("url"))
        elif post.get("thumbnail") and post.get("thumbnail") not in ["self", "default", "nsfw"]:
            embed.set_thumbnail(url=post.get("thumbnail"))

        embed.set_footer(text=f"Post {post_num}/{total_posts} • Click title to view on Reddit")

        return embed


async def setup(bot):
    await bot.add_cog(Reddit(bot))