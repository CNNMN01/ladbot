"""
Enhanced Dinosaur information using API data
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
    """Enhanced dinosaur facts using real paleontology APIs"""

    def __init__(self, bot):
        self.bot = bot

        # Multiple API endpoints for dinosaur data
        self.apis = {
            'paleodb': 'https://paleobiodb.org/data1.2/taxa/list.json',
            'dinoapi': 'https://chinguun.github.io/dinoapi',
            'nhm': 'https://data.nhm.ac.uk/api/3/action/datastore_search'
        }

        # Cache for performance
        self._dino_cache = {}
        self._popular_dinos = [
            'Tyrannosaurus', 'Triceratops', 'Velociraptor', 'Stegosaurus',
            'Allosaurus', 'Brontosaurus', 'Spinosaurus', 'Diplodocus',
            'Ankylosaurus', 'Parasaurolophus', 'Carnotaurus', 'Iguanodon'
        ]

    async def _fetch_dinosaur_info(self, dino_name):
        """Fetch dinosaur information from APIs"""
        try:
            # Try PaleoDB API first (most comprehensive)
            url = f"{self.apis['paleodb']}?name={dino_name}&show=attr,ecospace,taphonomy&format=json"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get('records', [])

                        if records:
                            dino = records[0]  # Get first match
                            return self._format_paleodb_data(dino)

            # Fallback to local enhanced data if API fails
            return self._get_enhanced_fallback_data(dino_name)

        except Exception as e:
            logger.warning(f"API fetch failed for {dino_name}: {e}")
            return self._get_enhanced_fallback_data(dino_name)

    def _format_paleodb_data(self, dino_data):
        """Format PaleoDB API data into readable format"""
        name = dino_data.get('taxon_name', 'Unknown')
        rank = dino_data.get('taxon_rank', 'species')

        # Build description from available data
        description_parts = []

        # Basic classification
        if dino_data.get('taxon_rank'):
            description_parts.append(f"**Classification:** {rank.title()}")

        # Time period
        early_interval = dino_data.get('early_interval', '')
        late_interval = dino_data.get('late_interval', '')
        if early_interval and late_interval:
            if early_interval == late_interval:
                description_parts.append(f"**Time Period:** {early_interval}")
            else:
                description_parts.append(f"**Time Period:** {early_interval} to {late_interval}")
        elif early_interval:
            description_parts.append(f"**Time Period:** {early_interval}")

        # Geographic info
        if dino_data.get('cc', []):
            countries = ', '.join(dino_data['cc'][:3])  # First 3 countries
            description_parts.append(f"**Found in:** {countries}")

        # Ecological information
        if dino_data.get('environment'):
            env = dino_data['environment']
            description_parts.append(f"**Environment:** {env}")

        # Diet information (if available)
        if 'carnivore' in name.lower() or 'carno' in name.lower():
            description_parts.append(f"**Diet:** Carnivore (meat-eater)")
        elif any(word in name.lower() for word in ['sauro', 'ceratops', 'stego']):
            description_parts.append(f"**Diet:** Herbivore (plant-eater)")

        description = '\n'.join(description_parts) if description_parts else "A fascinating dinosaur species!"

        return {
            'name': name,
            'description': description,
            'scientific_name': dino_data.get('taxon_name', name),
            'rank': rank,
            'source': 'Paleobiology Database'
        }

    def _get_enhanced_fallback_data(self, dino_name):
        """Enhanced fallback dinosaur data with more details"""
        fallback_data = {
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
                'rank': 'species',
                'source': 'Enhanced Database'
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
                'rank': 'species',
                'source': 'Enhanced Database'
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
                'rank': 'species',
                'source': 'Enhanced Database'
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
                'rank': 'species',
                'source': 'Enhanced Database'
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
                'rank': 'species',
                'source': 'Enhanced Database'
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
                'rank': 'species',
                'source': 'Enhanced Database'
            }
        }

        key = dino_name.lower().replace(' ', '').replace('-', '')
        return fallback_data.get(key)

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

            # Clean the name
            dinosaur_name = dinosaur_name.strip()

            # Fetch dinosaur information
            dino_info = await self._fetch_dinosaur_info(dinosaur_name)

            if not dino_info:
                embed = discord.Embed(
                    description=f"🦕 Sorry, I couldn't find information about `{dinosaur_name}`.\n\nTry searching for popular dinosaurs like T-Rex, Triceratops, or Stegosaurus!",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Suggestions",
                    value=f"• `l.dino random` - Random dinosaur\n• `l.dino popular` - Show popular dinosaurs\n• `l.dino Tyrannosaurus` - Specific dinosaur",
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
                text=f"Requested by {ctx.author.display_name} • Data from {dino_info.get('source', 'Paleontology APIs')}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in dino command: {e}")
            embed = discord.Embed(
                description="🦕 Sorry, there was an error getting dinosaur information. Please try again later!",
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
        """Show popular dinosaurs"""
        embed = discord.Embed(
            title="🦕 Popular Dinosaurs",
            description="Here are some of the most well-known dinosaurs:",
            color=0x228B22
        )

        # Split into chunks for better display
        chunk_size = 6
        chunks = [self._popular_dinos[i:i + chunk_size] for i in range(0, len(self._popular_dinos), chunk_size)]

        for i, chunk in enumerate(chunks):
            dino_list = '\n'.join([f"🦴 {dino}" for dino in chunk])
            embed.add_field(
                name=f"Group {i + 1}",
                value=dino_list,
                inline=True
            )

        embed.add_field(
            name="📝 Usage",
            value="`l.dino [name]` to learn about any of these dinosaurs!",
            inline=False
        )

        await ctx.send(embed=embed)

    @dino.command(name="search")
    @guild_setting_enabled("dinosaurs")
    async def dino_search(self, ctx, *, keywords: str):
        """Search for dinosaurs by characteristics"""
        # Simple keyword-based suggestions
        keyword_suggestions = {
            'carnivore': ['Tyrannosaurus', 'Velociraptor', 'Allosaurus', 'Carnotaurus'],
            'herbivore': ['Triceratops', 'Stegosaurus', 'Brontosaurus', 'Iguanodon'],
            'flying': ['Pteranodon', 'Quetzalcoatlus', 'Archaeopteryx'],
            'marine': ['Plesiosaur', 'Mosasaurus', 'Ichthyosaur'],
            'armored': ['Ankylosaurus', 'Stegosaurus', 'Triceratops'],
            'long neck': ['Brontosaurus', 'Diplodocus', 'Brachiosaurus'],
            'small': ['Velociraptor', 'Compsognathus', 'Microraptor'],
            'large': ['Tyrannosaurus', 'Spinosaurus', 'Giganotosaurus']
        }

        keywords_lower = keywords.lower()
        matches = []

        for key, dinos in keyword_suggestions.items():
            if key in keywords_lower:
                matches.extend(dinos)

        if matches:
            # Remove duplicates and limit results
            matches = list(set(matches))[:8]

            embed = discord.Embed(
                title=f"🔍 Search Results for '{keywords}'",
                description=f"Found {len(matches)} dinosaurs matching your search:",
                color=0x228B22
            )

            match_list = '\n'.join([f"🦴 {dino}" for dino in matches])
            embed.add_field(
                name="Matching Dinosaurs",
                value=match_list,
                inline=False
            )

            embed.add_field(
                name="📝 Next Steps",
                value=f"Use `l.dino [name]` to learn more about any of these dinosaurs!",
                inline=False
            )

        else:
            embed = discord.Embed(
                title="🔍 No Matches Found",
                description=f"No dinosaurs found matching '{keywords}'.",
                color=0xffaa00
            )

            embed.add_field(
                name="💡 Try These Keywords",
                value="carnivore, herbivore, armored, flying, marine, long neck, small, large",
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
            ("`l.dino random`", "Get a random dinosaur"),
            ("`l.dino popular`", "Show popular dinosaurs"),
            ("`l.dino search [keywords]`", "Search dinosaurs by characteristics"),
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
                "`l.dino Tyrannosaurus` - Learn about T-Rex\n"
                "`l.dino random 3` - Get 3 random dinosaurs\n"
                "`l.dino search carnivore` - Find meat-eating dinosaurs\n"
                "`l.dino search armored` - Find armored dinosaurs"
            ),
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Dinosaurs(bot))