"""
Enhanced Dinosaur information with reliable fallback data
"""

import discord
from discord.ext import commands
import aiohttp
import json
import random
import asyncio
from utils.decorators import guild_setting_enabled, typing_context
import logging

logger = logging.getLogger(__name__)


class Dinosaurs(commands.Cog):
    """Dinosaur facts"""

    def __init__(self, bot):
        self.bot = bot

        # Comprehensive dinosaur database with aliases
        self.dinosaur_data = {
            # T-Rex and variants
            'tyrannosaurus': {
                'name': 'Tyrannosaurus Rex',
                'description': '''**Classification:** Theropod dinosaur
**Time Period:** Late Cretaceous (68-66 million years ago)
**Diet:** Carnivore (apex predator)
**Size:** Up to 40 feet long, 12 feet tall at hips
**Weight:** 8-9 tons
**Found in:** North America (Montana, Wyoming, South Dakota)
**Fun Fact:** Had teeth up to 8 inches long and one of the strongest bite forces ever recorded!''',
                'scientific_name': 'Tyrannosaurus rex',
                'aliases': ['t-rex', 'trex', 't rex', 'tyrannosaurus rex']
            },
            'triceratops': {
                'name': 'Triceratops',
                'description': '''**Classification:** Ceratopsid dinosaur
**Time Period:** Late Cretaceous (68-66 million years ago)
**Diet:** Herbivore (plant-eater)
**Size:** Up to 30 feet long, 10 feet tall
**Weight:** 6-12 tons
**Found in:** North America (Colorado, Wyoming, Montana)
**Fun Fact:** Its iconic three-horned skull could grow up to 7 feet long!''',
                'scientific_name': 'Triceratops horridus',
                'aliases': ['three horn', 'threehorn']
            },
            'velociraptor': {
                'name': 'Velociraptor',
                'description': '''**Classification:** Dromaeosaurid dinosaur
**Time Period:** Late Cretaceous (75-71 million years ago)
**Diet:** Carnivore (pack hunter)
**Size:** 6.8 feet long, 1.6 feet tall at hips
**Weight:** 33-43 pounds
**Found in:** Mongolia and China
**Fun Fact:** Actually turkey-sized with feathers, not the giant movie monsters!''',
                'scientific_name': 'Velociraptor mongoliensis',
                'aliases': ['raptor', 'velociraptors']
            },
            'stegosaurus': {
                'name': 'Stegosaurus',
                'description': '''**Classification:** Stegosaurid dinosaur
**Time Period:** Late Jurassic (155-150 million years ago)
**Diet:** Herbivore (low-browsing plant-eater)
**Size:** Up to 30 feet long, 14 feet tall
**Weight:** 5 tons
**Found in:** Western United States
**Fun Fact:** Had a brain the size of a walnut but survived for millions of years!''',
                'scientific_name': 'Stegosaurus stenops',
                'aliases': ['stego', 'spike tail']
            },
            'spinosaurus': {
                'name': 'Spinosaurus',
                'description': '''**Classification:** Spinosaurid dinosaur
**Time Period:** Mid-Cretaceous (112-93 million years ago)
**Diet:** Piscivore (fish-eater) and carnivore
**Size:** Up to 50 feet long, 16 feet tall
**Weight:** 7-20 tons
**Found in:** North Africa (Egypt, Morocco)
**Fun Fact:** First known semi-aquatic dinosaur with a massive sail on its back!''',
                'scientific_name': 'Spinosaurus aegyptiacus',
                'aliases': ['spino', 'sail back']
            },
            'brontosaurus': {
                'name': 'Brontosaurus',
                'description': '''**Classification:** Diplodocid sauropod dinosaur
**Time Period:** Late Jurassic (156-146 million years ago)
**Diet:** Herbivore (high-browsing plant-eater)
**Size:** Up to 72 feet long, 15 feet tall at shoulders
**Weight:** 15-17 tons
**Found in:** Western United States
**Fun Fact:** Name means "thunder lizard" - once thought to be Apatosaurus but proven distinct in 2015!''',
                'scientific_name': 'Brontosaurus excelsus',
                'aliases': ['thunder lizard', 'apatosaurus', 'long neck']
            },
            'allosaurus': {
                'name': 'Allosaurus',
                'description': '''**Classification:** Theropod dinosaur
**Time Period:** Late Jurassic (155-145 million years ago)
**Diet:** Carnivore (pack hunter)
**Size:** Up to 32 feet long, 9.5 feet tall at hips
**Weight:** 3-5 tons
**Found in:** Western United States
**Fun Fact:** One of the first well-known predatory dinosaurs and lived alongside Stegosaurus!''',
                'scientific_name': 'Allosaurus fragilis',
                'aliases': ['allo']
            },
            'diplodocus': {
                'name': 'Diplodocus',
                'description': '''**Classification:** Diplodocid sauropod dinosaur
**Time Period:** Late Jurassic (154-150 million years ago)
**Diet:** Herbivore (low-browsing plant-eater)
**Size:** Up to 90 feet long, 13 feet tall at shoulders
**Weight:** 10-16 tons
**Found in:** Western United States
**Fun Fact:** One of the longest dinosaurs ever discovered with an incredibly long whip-like tail!''',
                'scientific_name': 'Diplodocus carnegii',
                'aliases': ['diplo', 'whip tail']
            },
            'ankylosaurus': {
                'name': 'Ankylosaurus',
                'description': '''**Classification:** Ankylosaurid dinosaur
**Time Period:** Late Cretaceous (68-66 million years ago)
**Diet:** Herbivore (low-browsing plant-eater)
**Size:** Up to 35 feet long, 5.5 feet tall
**Weight:** 6-8 tons
**Found in:** North America (Montana, Wyoming, Alberta)
**Fun Fact:** Living tank with a massive club tail that could break the bones of predators!''',
                'scientific_name': 'Ankylosaurus magniventris',
                'aliases': ['armored dinosaur', 'club tail', 'tank dinosaur']
            },
            'carnotaurus': {
                'name': 'Carnotaurus',
                'description': '''**Classification:** Abelisaurid theropod dinosaur
**Time Period:** Late Cretaceous (72-69 million years ago)
**Diet:** Carnivore (fast pursuit predator)
**Size:** Up to 26 feet long, 11 feet tall
**Weight:** 1.35-2.1 tons
**Found in:** Argentina, South America
**Fun Fact:** The "meat-eating bull" with horns above its eyes and tiny, almost useless arms!''',
                'scientific_name': 'Carnotaurus sastrei',
                'aliases': ['meat eating bull', 'horned carnivore']
            },
            'parasaurolophus': {
                'name': 'Parasaurolophus',
                'description': '''**Classification:** Hadrosaurid dinosaur
**Time Period:** Late Cretaceous (76-73 million years ago)
**Diet:** Herbivore (duck-billed plant-eater)
**Size:** Up to 31 feet long, 16 feet tall
**Weight:** 2.5-5 tons
**Found in:** North America (Alberta, Utah, New Mexico)
**Fun Fact:** Could make loud honking sounds through its distinctive hollow crest!''',
                'scientific_name': 'Parasaurolophus walkeri',
                'aliases': ['duck bill', 'honker', 'trumpet dinosaur']
            },
            'iguanodon': {
                'name': 'Iguanodon',
                'description': '''**Classification:** Iguanodontid dinosaur
**Time Period:** Early Cretaceous (140-110 million years ago)
**Diet:** Herbivore (browsing plant-eater)
**Size:** Up to 43 feet long, 16 feet tall
**Weight:** 3-5 tons
**Found in:** Europe (England, Belgium, Germany)
**Fun Fact:** One of the first dinosaurs ever discovered and had distinctive thumb spikes!''',
                'scientific_name': 'Iguanodon bernissartensis',
                'aliases': ['thumb spike', 'iguana tooth']
            }
        }

        # Popular dinosaurs for random selection
        self._popular_dinos = list(self.dinosaur_data.keys())

    def _find_dinosaur(self, search_name):
        """Find dinosaur by name or alias with flexible matching"""
        search_name = search_name.lower().strip().replace('-', ' ').replace('_', ' ')

        # Try exact match first
        if search_name in self.dinosaur_data:
            return self.dinosaur_data[search_name]

        # Try aliases
        for dino_key, dino_data in self.dinosaur_data.items():
            aliases = dino_data.get('aliases', [])
            if search_name in [alias.lower() for alias in aliases]:
                return dino_data

        # Try partial matches
        for dino_key, dino_data in self.dinosaur_data.items():
            if search_name in dino_key.lower() or dino_key.lower() in search_name:
                return dino_data

            # Check if search term is in the dinosaur name
            if search_name in dino_data['name'].lower():
                return dino_data

        return None

    async def _try_api_fetch(self, dino_name):
        """Try to fetch from API with timeout"""
        try:
            url = f"https://paleobiodb.org/data1.2/taxa/list.json?name={dino_name}&show=attr&format=json"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get('records', [])
                        if records:
                            return records[0]
            return None
        except Exception as e:
            logger.debug(f"API fetch failed for {dino_name}: {e}")
            return None

    @commands.group(aliases=["dinosaur", "dinos"], invoke_without_command=True)
    @guild_setting_enabled("dinosaurs")
    @typing_context()
    async def dino(self, ctx, *, dinosaur_name: str = None):
        """Get detailed information about dinosaurs

        Usage:
        l.dino [dinosaur name] - Get specific dinosaur info
        l.dino - Random popular dinosaur
        l.dino random - Random dinosaur

        Examples:
        l.dino Tyrannosaurus
        l.dino T-Rex
        l.dino Triceratops
        """
        try:
            # If no dinosaur specified, get a random popular one
            if not dinosaur_name:
                dinosaur_name = random.choice(self._popular_dinos)
                is_random = True
            elif dinosaur_name.lower() in ['random', 'rand', 'r']:
                dinosaur_name = random.choice(self._popular_dinos)
                is_random = True
            else:
                is_random = False

            # Try to find the dinosaur
            dino_info = self._find_dinosaur(dinosaur_name)

            if not dino_info:
                # Show helpful error message
                embed = discord.Embed(
                    description=f"🦕 Sorry, I couldn't find information about `{dinosaur_name}`.",
                    color=0xff0000
                )

                # Suggest some alternatives
                suggestions = random.sample(self._popular_dinos, min(3, len(self._popular_dinos)))
                suggest_text = '\n'.join([f"• `l.dino {dino.title()}`" for dino in suggestions])

                embed.add_field(
                    name="💡 Try these dinosaurs:",
                    value=suggest_text,
                    inline=False
                )

                embed.add_field(
                    name="📚 More Options",
                    value="`l.dino random` - Random dinosaur\n`l.dino popular` - Show all available",
                    inline=False
                )

                await ctx.send(embed=embed)
                return

            # Create beautiful dinosaur embed
            embed = discord.Embed(
                title=f"🦕 {dino_info['name']}",
                description=dino_info['description'],
                color=0x228B22
            )

            # Add scientific name if different
            if dino_info.get('scientific_name') and dino_info['scientific_name'] != dino_info['name']:
                embed.add_field(
                    name="🔬 Scientific Name",
                    value=f"*{dino_info['scientific_name']}*",
                    inline=True
                )

            if is_random:
                embed.add_field(
                    name="🎲 Random Discovery",
                    value="Randomly selected dinosaur",
                    inline=True
                )

            # Add footer
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name} • Enhanced Paleontology Database",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in dino command: {e}")
            embed = discord.Embed(
                description="🦕 Sorry, there was an error getting dinosaur information. Please try again!",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    @dino.command(name="random")
    @guild_setting_enabled("dinosaurs")
    async def dino_random(self, ctx, count: int = 1):
        """Get random dinosaur(s)

        Usage: l.dino random [count]
        Example: l.dino random 3
        """
        if count > 5:
            await ctx.send("❌ Maximum 5 dinosaurs at once to avoid spam!")
            return
        elif count < 1:
            count = 1

        for i in range(count):
            if i > 0:
                await asyncio.sleep(1)  # Small delay between multiple results
            await self.dino.callback(self, ctx, dinosaur_name="random")

    @dino.command(name="popular")
    @guild_setting_enabled("dinosaurs")
    async def dino_popular(self, ctx):
        """Show all available dinosaurs"""
        embed = discord.Embed(
            title="🦕 Available Dinosaurs",
            description=f"Here are all {len(self.dinosaur_data)} dinosaurs in our database:",
            color=0x228B22
        )

        # Split into chunks for better display
        dino_names = [data['name'] for data in self.dinosaur_data.values()]
        chunk_size = 6
        chunks = [dino_names[i:i + chunk_size] for i in range(0, len(dino_names), chunk_size)]

        for i, chunk in enumerate(chunks):
            dino_list = '\n'.join([f"🦴 {dino}" for dino in chunk])
            embed.add_field(
                name=f"Group {i + 1}",
                value=dino_list,
                inline=True
            )

        embed.add_field(
            name="📝 Usage",
            value="`l.dino [name]` to learn about any dinosaur!\nExample: `l.dino T-Rex`",
            inline=False
        )

        await ctx.send(embed=embed)

    @dino.command(name="help")
    @guild_setting_enabled("dinosaurs")
    async def dino_help(self, ctx):
        """Show help for dinosaur commands"""
        embed = discord.Embed(
            title="🦕 Dinosaur Commands Help",
            description="Everything you need to know about dinosaur commands:",
            color=0x228B22
        )

        commands_help = [
            ("`l.dino [name]`", "Get detailed info about a specific dinosaur"),
            ("`l.dino random [count]`", "Get random dinosaur(s)"),
            ("`l.dino popular`", "Show all available dinosaurs"),
            ("`l.dino help`", "Show this help message")
        ]

        for command, description in commands_help:
            embed.add_field(
                name=command,
                value=description,
                inline=False
            )

        embed.add_field(
            name="📝 Examples",
            value=(
                "`l.dino T-Rex` - Learn about Tyrannosaurus\n"
                "`l.dino random 3` - Get 3 random dinosaurs\n"
                "`l.dino Triceratops` - Three-horned dinosaur\n"
                "`l.dino raptor` - Velociraptor info"
            ),
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Dinosaurs(bot))