"""
Dice rolling command
"""

import sys


import discord
from discord.ext import commands
import random
import re


class Roll(commands.Cog):
    """Dice rolling commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx, dice: str = "1d6"):
        """Roll dice using D&D notation

        Examples:
        l.roll 1d6 - Roll one 6-sided die
        l.roll 2d10 - Roll two 10-sided dice
        l.roll 3d8+5 - Roll three 8-sided dice and add 5
        """
        try:
            # Parse dice notation (e.g., "2d6", "1d20+3", "3d8-2")
            pattern = r'(\d+)d(\d+)([+-]\d+)?'
            match = re.match(pattern, dice.lower().replace(' ', ''))

            if not match:
                embed = discord.Embed(
                    description="❌ Invalid dice format! Use format like: `2d6`, `1d20+3`, `3d8-2`",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            num_dice = int(match.group(1))
            die_size = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0

            # Validate input
            if num_dice > 50:
                await ctx.send("❌ Maximum 50 dice allowed!")
                return
            if die_size > 1000:
                await ctx.send("❌ Maximum 1000-sided die allowed!")
                return
            if num_dice < 1 or die_size < 1:
                await ctx.send("❌ Dice must be positive numbers!")
                return

            # Roll the dice
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            total = sum(rolls) + modifier

            # Create result embed
            embed = discord.Embed(
                title=f"🎲 Dice Roll: {dice}",
                color=0x00ff00
            )

            # Show individual rolls if not too many
            if num_dice <= 20:
                rolls_text = " + ".join(str(roll) for roll in rolls)
                if modifier:
                    rolls_text += f" {modifier:+d}"
                embed.add_field(name="Rolls", value=rolls_text, inline=False)
            else:
                embed.add_field(name="Number of Dice", value=str(num_dice), inline=True)
                embed.add_field(name="Die Size", value=f"d{die_size}", inline=True)
                if modifier:
                    embed.add_field(name="Modifier", value=f"{modifier:+d}", inline=True)

            embed.add_field(name="**Total**", value=f"**{total}**", inline=False)

            # Add some flavor for special rolls
            if num_dice == 1:
                if rolls[0] == die_size:
                    embed.add_field(name="🎉", value="Maximum roll!", inline=True)
                elif rolls[0] == 1:
                    embed.add_field(name="💥", value="Minimum roll!", inline=True)

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error rolling dice: {e}")


async def setup(bot):
    await bot.add_cog(Roll(bot))