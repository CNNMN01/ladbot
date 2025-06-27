"""
Dinosaur facts and information
"""

import sys


import discord
from discord.ext import commands
import json
import random
from utils.decorators import guild_setting_enabled, typing_context
from fuzzywuzzy import process


class Dinosaurs(commands.Cog):
    """Dinosaur facts and information"""

    def __init__(self, bot):
        self.bot = bot
        self._dino_data = None

    @property
    def dino_data(self):
        """Lazy load dinosaur data"""
        if self._dino_data is None:
            try:
                self._dino_data = self.bot.data_manager.get_json("dinos")
            except:
                self._dino_data = self._get_fallback_dinos()
        return self._dino_data

    def _get_fallback_dinos(self):
        """Fallback dinosaur data if file not found"""
        return {
            "Tyrannosaurus": "Tyrannosaurus rex was one of the largest land predators ever known. It lived during the late Cretaceous period and could grow up to 40 feet long!",
            "Triceratops": "Triceratops was a large herbivorous dinosaur with three distinctive horns and a large bony frill. It lived during the late Cretaceous period.",
            "Stegosaurus": "Stegosaurus was a large, heavily built dinosaur with distinctive plates along its back and spikes on its tail for defense.",
            "Velociraptor": "Despite popular media portrayals, Velociraptors were actually about the size of a large turkey, but they were incredibly intelligent pack hunters.",
            "Brontosaurus": "Brontosaurus was a long-necked sauropod dinosaur that lived during the late Jurassic period. It could grow up to 72 feet long!"
        }

    @commands.command(aliases=["dinosaur", "dinos"])
    @guild_setting_enabled("dino")
    @typing_context()
    async def dino(self, ctx, *, dinosaur_name: str = None):
        """Get information about dinosaurs

        Usage: l.dino [dinosaur name]
        Examples: l.dino, l.dino random, l.dino t-rex, l.dino Triceratops
        """
        try:
            if not dinosaur_name:
                # Random dinosaur when no name provided
                all_dino_names = list(self.dino_data.keys())
                dino_name = random.choice(all_dino_names)
                dino_info = self.dino_data[dino_name]
                is_random = True
            else:
                # Check if user specifically wants random
                if dinosaur_name.lower() in ["random", "rand", "r"]:
                    all_dino_names = list(self.dino_data.keys())
                    dino_name = random.choice(all_dino_names)
                    dino_info = self.dino_data[dino_name]
                    is_random = True
                else:
                    # Search for specific dinosaur
                    dino_names = list(self.dino_data.keys())

                    # Try exact match first
                    exact_match = None
                    for name in dino_names:
                        if name.lower() == dinosaur_name.lower():
                            exact_match = name
                            break

                    if exact_match:
                        dino_name = exact_match
                        dino_info = self.dino_data[dino_name]
                        is_random = False
                    else:
                        # Fuzzy search
                        best_match = process.extractOne(dinosaur_name, dino_names)
                        if best_match and best_match[1] >= 60:  # 60% similarity threshold
                            dino_name = best_match[0]
                            dino_info = self.dino_data[dino_name]
                            is_random = False
                        else:
                            # No good match found
                            embed = discord.Embed(
                                title="🦕 Dinosaur Not Found",
                                description=f"Couldn't find information about `{dinosaur_name}`.",
                                color=0xff0000
                            )

                            # Suggest similar dinosaurs
                            suggestions = process.extract(dinosaur_name, dino_names, limit=3)
                            if suggestions:
                                suggest_text = "\n".join([f"• {name}" for name, score in suggestions])
                                embed.add_field(
                                    name="Did you mean?",
                                    value=suggest_text,
                                    inline=False
                                )

                            embed.add_field(
                                name="💡 Tip",
                                value=f"Use `{self.bot.command_prefix}dino` or `{self.bot.command_prefix}dino random` for a random dinosaur!",
                                inline=False
                            )

                            await ctx.send(embed=embed)
                            return

            # Create dinosaur embed
            embed = discord.Embed(
                title=f"🦕 {dino_name}",
                description=dino_info,
                color=0x228B22
            )

            # Add dinosaur image from icons
            try:
                dino_icons = self.bot.data_manager.icons.get("dinos", [])
                if dino_icons:
                    icon_url = random.choice(dino_icons)
                    embed.set_thumbnail(url=icon_url)
            except:
                pass

            if is_random:
                embed.add_field(
                    name="🎲 Type",
                    value="Random Dinosaur",
                    inline=True
                )

            embed.add_field(
                name="📚 Total Dinosaurs",
                value=str(len(self.dino_data)),
                inline=True
            )

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Use l.dino <name> for specific dinosaurs",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error getting dinosaur info: {e}")

    @commands.command()
    @guild_setting_enabled("dino")
    async def dinolist(self, ctx):
        """List all available dinosaurs"""
        try:
            dino_names = sorted(self.dino_data.keys())

            # Split into chunks for multiple embeds if needed
            chunk_size = 20
            chunks = [dino_names[i:i + chunk_size] for i in range(0, len(dino_names), chunk_size)]

            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=f"🦕 Available Dinosaurs ({len(dino_names)} total)",
                    color=0x228B22
                )

                # Format dinosaur names in columns
                dino_list = "\n".join(chunk)
                embed.add_field(
                    name=f"Page {i + 1}/{len(chunks)}",
                    value=dino_list,
                    inline=False
                )

                embed.set_footer(text=f"Use {self.bot.command_prefix}dino <name> to learn about a specific dinosaur")

                await ctx.send(embed=embed)

                # Only send first page for now to avoid spam
                if len(chunks) > 1:
                    embed.add_field(
                        name="📄 More Pages",
                        value=f"This is page 1 of {len(chunks)}. More dinosaurs available!",
                        inline=False
                    )
                    break

        except Exception as e:
            await ctx.send(f"❌ Error listing dinosaurs: {e}")


async def setup(bot):
    await bot.add_cog(Dinosaurs(bot))