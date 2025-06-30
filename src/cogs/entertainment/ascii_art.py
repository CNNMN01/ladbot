"""
Hybrid ASCII Art - Works with or without the 'art' library
"""

import sys


import discord
from discord.ext import commands
import random
from typing import Optional, Dict, List
from utils.decorators import guild_setting_enabled, typing_context


class AsciiArt(commands.Cog):
    """ASCII Art generator commands"""

    def __init__(self, bot):
        self.bot = bot

        # Check if art library is available
        self.has_art_library = self._check_art_library()

        # Art library fonts (only used if library is available)
        self.art_fonts = {
            'standard': 'standard',
            'big': 'big',
            'small': 'small',
            'block': 'block',
            'bubble': 'bubble',
            'digital': 'digital',
            'lean': 'lean',
            'mini': 'mini',
            'script': 'script',
            'shadow': 'shadow',
            'slant': 'slant',
            'speed': 'speed',
            '3d': '3-d',
            'cyber': 'cyberlarge',
            'doom': 'doom',
            'fire': 'fire_font-k',
            'ghost': 'ghost',
            'graffiti': 'graffiti',
            'hollywood': 'hollywood',
            'nancyj': 'nancyj',
            'puffy': 'puffy',
            'rounded': 'rounded'
        }

        # Built-in ASCII patterns for fallback
        self.ascii_patterns = {
            'A': ["  ██  ", " ████ ", "██  ██", "██████", "██  ██", "██  ██"],
            'B': ["██████", "██  ██", "██████", "██████", "██  ██", "██████"],
            'C': [" █████", "██    ", "██    ", "██    ", "██    ", " █████"],
            'D': ["██████", "██  ██", "██  ██", "██  ██", "██  ██", "██████"],
            'E': ["██████", "██    ", "█████ ", "█████ ", "██    ", "██████"],
            'F': ["██████", "██    ", "█████ ", "█████ ", "██    ", "██    "],
            'G': [" █████", "██    ", "██ ███", "██  ██", "██  ██", " █████"],
            'H': ["██  ██", "██  ██", "██████", "██████", "██  ██", "██  ██"],
            'I': ["██████", "  ██  ", "  ██  ", "  ██  ", "  ██  ", "██████"],
            'J': ["██████", "    ██", "    ██", "    ██", "██  ██", " █████"],
            'K': ["██  ██", "██ ██ ", "████  ", "████  ", "██ ██ ", "██  ██"],
            'L': ["██    ", "██    ", "██    ", "██    ", "██    ", "██████"],
            'M': ["██  ██", "██████", "██████", "██  ██", "██  ██", "██  ██"],
            'N': ["██  ██", "███ ██", "██████", "██ ███", "██  ██", "██  ██"],
            'O': [" █████", "██  ██", "██  ██", "██  ██", "██  ██", " █████"],
            'P': ["██████", "██  ██", "██████", "██    ", "██    ", "██    "],
            'Q': [" █████", "██  ██", "██  ██", "██ ███", "██  ██", " ██████"],
            'R': ["██████", "██  ██", "██████", "██ ██ ", "██  ██", "██  ██"],
            'S': [" █████", "██    ", " ████ ", "    ██", "    ██", "█████ "],
            'T': ["██████", "  ██  ", "  ██  ", "  ██  ", "  ██  ", "  ██  "],
            'U': ["██  ██", "██  ██", "██  ██", "██  ██", "██  ██", " █████"],
            'V': ["██  ██", "██  ██", "██  ██", "██  ██", " ████ ", "  ██  "],
            'W': ["██  ██", "██  ██", "██  ██", "██████", "██████", "██  ██"],
            'X': ["██  ██", " ████ ", "  ██  ", "  ██  ", " ████ ", "██  ██"],
            'Y': ["██  ██", "██  ██", " ████ ", "  ██  ", "  ██  ", "  ██  "],
            'Z': ["██████", "    ██", "   ██ ", "  ██  ", " ██   ", "██████"],
            '0': [" █████", "██  ██", "██  ██", "██  ██", "██  ██", " █████"],
            '1': ["  ██  ", " ███  ", "  ██  ", "  ██  ", "  ██  ", "██████"],
            '2': [" █████", "██  ██", "   ██ ", "  ██  ", " ██   ", "██████"],
            '3': [" █████", "██  ██", "  ███ ", "   ██ ", "██  ██", " █████"],
            '4': ["██  ██", "██  ██", "██████", "    ██", "    ██", "    ██"],
            '5': ["██████", "██    ", "█████ ", "    ██", "██  ██", " █████"],
            '6': [" █████", "██    ", "██████", "██  ██", "██  ██", " █████"],
            '7': ["██████", "    ██", "   ██ ", "  ██  ", " ██   ", "██    "],
            '8': [" █████", "██  ██", " █████", " █████", "██  ██", " █████"],
            '9': [" █████", "██  ██", "██  ██", " ██████", "    ██", " █████"],
            ' ': ["      ", "      ", "      ", "      ", "      ", "      "],
            '!': ["  ██  ", "  ██  ", "  ██  ", "  ██  ", "      ", "  ██  "],
            '?': [" █████", "██  ██", "   ██ ", "  ██  ", "      ", "  ██  "],
            '.': ["      ", "      ", "      ", "      ", "      ", "  ██  "],
            '-': ["      ", "      ", "██████", "      ", "      ", "      "],
        }

        # Built-in styles that work without external libraries
        self.builtin_styles = {
            'built_block': self._generate_block_ascii,
            'simple': self._simple_box,
            'box': self._double_box,
            'stars': self._star_box,
            'fancy': self._fancy_box,
            'mini': self._mini_ascii,
            'wave': self._wave_style,
            'outline': self._outline_style
        }

    def _check_art_library(self) -> bool:
        """Check if the art library is available"""
        try:
            import art
            return True
        except ImportError:
            return False

    def create_code_block(self, content: str) -> str:
        """Helper to create Discord code blocks safely"""
        return f"```\n{content}\n```"

    @commands.group(name="ascii", aliases=["art", "text2art"], invoke_without_command=True)
    @guild_setting_enabled("ascii")
    @typing_context()
    async def ascii_art(self, ctx, font: str = "auto", *, text: str = None):
        """Generate ASCII art from text

        Usage:
        l.ascii <text> - Auto-select best available font
        l.ascii <font> <text> - Use specific font
        l.ascii fonts - List available fonts
        l.ascii status - Show library status

        Examples:
        l.ascii Hello World
        l.ascii big Discord Bot
        l.ascii slant Programming
        """

        # Handle case where font is actually the text
        if text is None and font not in ["fonts", "status", "help"]:
            text = font
            font = "auto"

        if not text:
            await self._show_help(ctx)
            return

        # Validate text length
        max_length = 15 if self.has_art_library else 10
        if len(text) > max_length:
            embed = discord.Embed(
                description=f"❌ Text too long! Maximum {max_length} characters.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        await self._generate_ascii(ctx, text, font)

    @ascii_art.command(name="fonts", aliases=["list"])
    async def list_fonts(self, ctx):
        """List all available fonts"""
        embed = discord.Embed(
            title="🎨 Available ASCII Fonts",
            color=0x00ff00
        )

        if self.has_art_library:
            # Show art library fonts
            art_fonts = list(self.art_fonts.keys())
            embed.add_field(
                name="🚀 Art Library Fonts (Premium)",
                value="```\n" + " • ".join(art_fonts[:12]) + "\n```",
                inline=False
            )
            if len(art_fonts) > 12:
                embed.add_field(
                    name="🚀 More Art Library Fonts",
                    value="```\n" + " • ".join(art_fonts[12:]) + "\n```",
                    inline=False
                )

        # Show built-in fonts
        builtin_fonts = list(self.builtin_styles.keys())
        embed.add_field(
            name="🔧 Built-in Fonts (Always Available)",
            value="```\n" + " • ".join(builtin_fonts) + "\n```",
            inline=False
        )

        embed.add_field(
            name="💡 Usage",
            value=f"`{ctx.prefix}ascii <font> <text>` or `{ctx.prefix}ascii <text>`",
            inline=False
        )

        # Library status
        status = "✅ Installed" if self.has_art_library else "❌ Not installed"
        embed.set_footer(text=f"Art Library Status: {status}")

        await ctx.send(embed=embed)

    @ascii_art.command(name="status")
    async def show_status(self, ctx):
        """Show ASCII art system status"""
        embed = discord.Embed(
            title="🔧 ASCII Art System Status",
            color=0x00ff00 if self.has_art_library else 0xffaa00
        )

        # Library status
        if self.has_art_library:
            embed.add_field(
                name="🚀 Art Library",
                value="✅ **Installed and Available**\nAccess to 20+ premium fonts",
                inline=False
            )
            embed.add_field(
                name="📊 Available Fonts",
                value=f"**Premium:** {len(self.art_fonts)} fonts\n**Built-in:** {len(self.builtin_styles)} styles\n**Total:** {len(self.art_fonts) + len(self.builtin_styles)}",
                inline=True
            )
        else:
            embed.add_field(
                name="⚠️ Art Library",
                value="❌ **Not Installed**\nUsing built-in fonts only",
                inline=False
            )
            embed.add_field(
                name="📊 Available Fonts",
                value=f"**Built-in:** {len(self.builtin_styles)} styles\n**Premium:** Install art library for more!",
                inline=True
            )

        embed.add_field(
            name="📋 Basic Usage",
            value=f"`{ctx.prefix}ascii <text>` - Auto-select font\n`{ctx.prefix}ascii <font> <text>` - Specific font",
            inline=False
        )

        embed.add_field(
            name="🎯 Quick Commands",
            value=f"`{ctx.prefix}ascii fonts` - List fonts\n`{ctx.prefix}ascii status` - System info\n`{ctx.prefix}ascii random <text>` - Random font",
            inline=False
        )

        if not self.has_art_library:
            embed.add_field(
                name="🚀 Want More Fonts?",
                value="Install art library: `pip install art`\nThen restart bot for 20+ premium fonts!",
                inline=False
            )

        await ctx.send(embed=embed)

    @ascii_art.command(name="random")
    async def random_font(self, ctx, *, text: str = None):
        """Generate ASCII art with a random font"""
        if not text:
            await ctx.send("❌ Please provide text!")
            return

        # Choose random font from available options
        available_fonts = list(self.builtin_styles.keys())
        if self.has_art_library:
            available_fonts.extend(list(self.art_fonts.keys()))

        font = random.choice(available_fonts)
        await self._generate_ascii(ctx, text, font, is_random=True)

    async def _generate_ascii(self, ctx, text: str, font: str, is_random: bool = False):
        """Generate ASCII art with intelligent font selection - Clean user output"""

        # Auto-select best font
        if font == "auto":
            if self.has_art_library:
                font = "standard" if len(text) <= 8 else "mini"
            else:
                font = "built_block" if len(text) <= 6 else "mini"

        # Try to generate with requested font
        result = await self._try_generate_font(text, font)

        if not result:
            # Fallback to built-in block style
            result = self._generate_block_ascii(text.upper())

        # Check result size
        if len(result) > 1900:
            await ctx.send("❌ Generated ASCII art is too large for Discord!")
            return

        # Create clean embed without developer info
        if is_random:
            title = f"🎲 Random ASCII Art"
        else:
            title = f"🎨 ASCII Art"

        embed = discord.Embed(
            title=title,
            description=self.create_code_block(result),
            color=0x00ff00
        )

        # Only show the text that was converted (clean and simple)
        embed.add_field(name="📝 Text", value=f"`{text}`", inline=True)

        # Add helpful footer only if using built-in fallback and art library not available
        if not self.has_art_library and font in self.builtin_styles:
            embed.set_footer(text="💡 Install 'art' library for more fonts and better quality")

        await ctx.send(embed=embed)

    async def _try_generate_font(self, text: str, font: str) -> Optional[str]:
        """Try to generate ASCII art with the specified font"""

        # Try art library first
        if self.has_art_library and font in self.art_fonts:
            try:
                import art
                art_font = self.art_fonts[font]
                result = art.text2art(text, font=art_font)
                if result and len(result.strip()) > 0:
                    return result.strip()
            except Exception:
                pass

        # Try built-in styles
        if font in self.builtin_styles:
            try:
                return self.builtin_styles[font](text)
            except Exception:
                pass

        return None

    # Built-in ASCII generation methods
    def _generate_block_ascii(self, text: str) -> str:
        """Generate block-style ASCII using patterns"""
        text = text.upper()
        if not text:
            return "Empty text"

        # Create lines for each row of the ASCII pattern
        lines = ["", "", "", "", "", ""]

        for char in text:
            if char in self.ascii_patterns:
                pattern = self.ascii_patterns[char]
                for i in range(6):
                    lines[i] += pattern[i] + " "
            else:
                # Unknown character, use space pattern
                for i in range(6):
                    lines[i] += "      " + " "

        return '\n'.join(lines)

    def _simple_box(self, text: str) -> str:
        """Simple box around text"""
        text = text.upper()
        width = len(text) + 4
        top_bottom = "+" + "-" * (width - 2) + "+"
        middle = f"| {text} |"
        return f"{top_bottom}\n{middle}\n{top_bottom}"

    def _double_box(self, text: str) -> str:
        """Double-line box around text"""
        text = text.upper()
        width = len(text) + 4
        top = "╔" + "═" * (width - 2) + "╗"
        middle = f"║ {text} ║"
        bottom = "╚" + "═" * (width - 2) + "╝"
        return f"{top}\n{middle}\n{bottom}"

    def _star_box(self, text: str) -> str:
        """Star box around text"""
        text = text.upper()
        width = len(text) + 4
        star_line = "*" * width
        middle = f"* {text} *"
        return f"{star_line}\n{middle}\n{star_line}"

    def _fancy_box(self, text: str) -> str:
        """Fancy decorated box"""
        text = text.upper()
        width = len(text) + 6
        top = "┌" + "─" * (width - 2) + "┐"
        middle = f"│ ★ {text} ★ │"
        bottom = "└" + "─" * (width - 2) + "┘"
        return f"{top}\n{middle}\n{bottom}"

    def _mini_ascii(self, text: str) -> str:
        """Mini 3-line ASCII"""
        mini_patterns = {
            'A': ['▄▀█', '█▀█', '█ █'], 'B': ['█▀▄', '█▀▄', '█▄▀'], 'C': ['▄▀▀', '█  ', '▀▀▀'],
            'D': ['█▀▄', '█ █', '█▄▀'], 'E': ['█▀▀', '█▀▀', '▀▀▀'], 'F': ['█▀▀', '█▀▀', '█  '],
            'G': ['▄▀█', '█▄█', '▀▀▀'], 'H': ['█ █', '█▀█', '█ █'], 'I': ['▀█▀', ' █ ', '▀▀▀'],
            'J': ['  █', '  █', '▀▀▀'], 'K': ['█ █', '██ ', '█ █'], 'L': ['█  ', '█  ', '▀▀▀'],
            'M': ['█▄█', '█▀█', '█ █'], 'N': ['█▄█', '█▀█', '█ █'], 'O': ['▄▀█', '█▄█', '▀▀▀'],
            'P': ['█▀▄', '█▀ ', '█  '], 'Q': ['▄▀█', '█▄█', '▀▀█'], 'R': ['█▀▄', '█▀▄', '█ █'],
            'S': ['▄▀▀', '▀▀▄', '▀▀▀'], 'T': ['▀█▀', ' █ ', ' █ '], 'U': ['█ █', '█ █', '▀▀▀'],
            'V': ['█ █', '█ █', ' █ '], 'W': ['█ █', '█▄█', '█▄█'], 'X': ['█ █', ' █ ', '█ █'],
            'Y': ['█ █', ' █ ', ' █ '], 'Z': ['▀▀▀', ' ▄▀', '▀▀▀'], ' ': [' ', ' ', ' '],
            '0': ['▄▀█', '█▄█', '▀▀▀'], '1': [' █ ', ' █ ', '▀▀▀'], '2': ['▀▀▄', '▄▀ ', '▀▀▀'],
            '3': ['▀▀▄', '▀▀▄', '▀▀▀'], '4': ['█ █', '▀▀█', '  █'], '5': ['█▀▀', '▀▀▄', '▀▀▀']
        }

        lines = ['', '', '']
        for char in text.upper():
            pattern = mini_patterns.get(char, [' ', ' ', ' '])
            for i in range(3):
                lines[i] += pattern[i] + ' '

        return '\n'.join(lines)

    def _wave_style(self, text: str) -> str:
        """Wave-like text style"""
        text = text.upper()
        wave_chars = "~≈≋≈~"
        width = len(text) + 6
        top_wave = wave_chars * (width // len(wave_chars) + 1)
        bottom_wave = wave_chars[::-1] * (width // len(wave_chars) + 1)
        return f"{top_wave[:width]}\n≋≈ {text} ≈≋\n{bottom_wave[:width]}"

    def _outline_style(self, text: str) -> str:
        """Outline text style"""
        text = text.upper()
        return f"┌─ {text} ─┐\n└{'─' * (len(text) + 2)}┘"

    async def _show_help(self, ctx):
        """Show help information"""
        embed = discord.Embed(
            title="🎨 ASCII Art Generator",
            description="Transform text into awesome ASCII art!",
            color=0x00ff00
        )

        status = "✅ Enhanced" if self.has_art_library else "⚠️ Basic"
        embed.add_field(
            name=f"🔧 System Status: {status}",
            value=f"Art Library: {'Installed' if self.has_art_library else 'Not installed'}",
            inline=False
        )

        embed.add_field(
            name="📋 Basic Usage",
            value=f"`{ctx.prefix}ascii <text>` - Auto-select font\n`{ctx.prefix}ascii <font> <text>` - Specific font",
            inline=False
        )

        embed.add_field(
            name="🎯 Quick Commands",
            value=f"`{ctx.prefix}ascii fonts` - List fonts\n`{ctx.prefix}ascii status` - System info\n`{ctx.prefix}ascii random <text>` - Random font",
            inline=False
        )

        font_count = len(self.builtin_styles)
        if self.has_art_library:
            font_count += len(self.art_fonts)

        embed.add_field(
            name="📊 Available Options",
            value=f"**{font_count} total fonts available**\nBuilt-in: {len(self.builtin_styles)} | Premium: {len(self.art_fonts) if self.has_art_library else 0}",
            inline=False
        )

        if not self.has_art_library:
            embed.add_field(
                name="🚀 Want More Fonts?",
                value="Install art library: `pip install art`\nThen restart bot for 20+ premium fonts!",
                inline=False
            )

        await ctx.send(embed=embed)

    # Quick command aliases
    @commands.command(name="bigtext")
    @guild_setting_enabled("ascii")
    async def big_text(self, ctx, *, text: str = None):
        """Generate big ASCII text"""
        if not text:
            await ctx.send("❌ Please provide text!")
            return
        font = "big" if self.has_art_library else "built_block"
        await self._generate_ascii(ctx, text, font)


async def setup(bot):
    await bot.add_cog(AsciiArt(bot))