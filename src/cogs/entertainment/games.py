"""
Classic Minesweeper Game - Following Microsoft Standards
Completely original implementation inspired by the classic game
"""

import discord
from discord.ext import commands
import random
import asyncio
from typing import Dict, Tuple, Set
from utils.decorators import guild_setting_enabled
import time


class ClassicMinesweeperGame:
    """
    Classic Minesweeper Game Implementation
    Following Microsoft Minesweeper conventions and standards
    """

    # Standard Microsoft Minesweeper difficulty levels
    DIFFICULTY_LEVELS = {
        "beginner": {
            "width": 9, "height": 9, "mines": 10,
            "description": "Perfect for new players",
            "emoji": "🟢"
        },
        "intermediate": {
            "width": 16, "height": 16, "mines": 40,
            "description": "A good challenge",
            "emoji": "🟡"
        },
        "expert": {
            "width": 30, "height": 16, "mines": 99,
            "description": "For experienced players",
            "emoji": "🔴"
        },
        "custom": {
            "width": 0, "height": 0, "mines": 0,
            "description": "Custom game settings",
            "emoji": "⚙️"
        }
    }

    # Display symbols following classic conventions
    SYMBOLS = {
        "hidden": "⬛",
        "revealed": "⬜",
        "flag": "🚩",
        "mine": "💣",
        "question": "❓",
        "cursor": "🟨",
        "numbers": ["⬜", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    }

    def __init__(self, width: int, height: int, mines: int, player_id: int, difficulty: str = "custom"):
        """Initialize a new Minesweeper game following Microsoft conventions"""
        self.width = min(width, 30)  # Microsoft limit
        self.height = min(height, 24)  # Discord message limit consideration
        self.mines = min(mines, (self.width * self.height) - 9)  # Ensure solvable
        self.player_id = player_id
        self.difficulty = difficulty

        # Game state
        self.board = None  # Will be generated on first reveal (Microsoft standard)
        self.revealed: Set[Tuple[int, int]] = set()
        self.flagged: Set[Tuple[int, int]] = set()
        self.questioned: Set[Tuple[int, int]] = set()  # Question marks
        self.game_over = False
        self.won = False
        self.first_reveal = True
        self.start_time = None
        self.end_time = None

        # UI state
        self.message = None
        self.cursor_x = 0
        self.cursor_y = 0

        # Statistics
        self.cells_remaining = (self.width * self.height) - self.mines
        self.flags_remaining = self.mines

    def _generate_board_safe(self, safe_x: int, safe_y: int):
        """
        Generate board ensuring the first click is safe (Microsoft standard)
        The first click and surrounding area must be mine-free
        """
        board = [[0 for _ in range(self.width)] for _ in range(self.height)]

        # Create safe zone around first click (3x3 area)
        safe_zone = set()
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                sx, sy = safe_x + dx, safe_y + dy
                if 0 <= sx < self.width and 0 <= sy < self.height:
                    safe_zone.add((sx, sy))

        # Place mines randomly, avoiding safe zone
        available_positions = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) not in safe_zone:
                    available_positions.append((x, y))

        # Ensure we have enough positions for mines
        mines_to_place = min(self.mines, len(available_positions))
        mine_positions = random.sample(available_positions, mines_to_place)

        # Place mines
        for x, y in mine_positions:
            board[y][x] = -1

        # Calculate adjacent mine counts
        for y in range(self.height):
            for x in range(self.width):
                if board[y][x] != -1:
                    count = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < self.height and 0 <= nx < self.width:
                                if board[ny][nx] == -1:
                                    count += 1
                    board[y][x] = count

        self.board = board
        self.mines = len(mine_positions)  # Update actual mine count
        self.flags_remaining = self.mines

    def reveal_cell(self, x: int, y: int) -> bool:
        """
        Reveal a cell following Microsoft Minesweeper rules
        Returns True if game continues, False if game over
        """
        # First click generates the board
        if self.first_reveal:
            self._generate_board_safe(x, y)
            self.first_reveal = False
            self.start_time = time.time()

        # Can't reveal flagged or already revealed cells
        if (x, y) in self.flagged or (x, y) in self.revealed:
            return True

        # Reveal the cell
        self.revealed.add((x, y))

        # Remove question mark if present
        self.questioned.discard((x, y))

        # Check if it's a mine
        if self.board[y][x] == -1:
            self.game_over = True
            self.end_time = time.time()
            return False

        # Auto-reveal adjacent cells if it's a 0 (Microsoft behavior)
        if self.board[y][x] == 0:
            self._flood_reveal(x, y)

        # Check win condition
        revealed_safe_cells = len([cell for cell in self.revealed
                                 if self.board[cell[1]][cell[0]] != -1])
        if revealed_safe_cells == self.cells_remaining:
            self.won = True
            self.game_over = True
            self.end_time = time.time()
            # Auto-flag remaining mines (Microsoft behavior)
            for y in range(self.height):
                for x in range(self.width):
                    if self.board[y][x] == -1:
                        self.flagged.add((x, y))

        return True

    def _flood_reveal(self, start_x: int, start_y: int):
        """
        Flood fill reveal for empty cells (Microsoft standard behavior)
        """
        stack = [(start_x, start_y)]

        while stack:
            x, y = stack.pop()

            # Check all 8 adjacent cells
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue

                    nx, ny = x + dx, y + dy

                    # Skip if out of bounds or already revealed
                    if (not (0 <= nx < self.width and 0 <= ny < self.height) or
                        (nx, ny) in self.revealed or (nx, ny) in self.flagged):
                        continue

                    # Reveal the cell
                    self.revealed.add((nx, ny))
                    self.questioned.discard((nx, ny))

                    # If it's also empty, add to stack for further flood fill
                    if self.board[ny][nx] == 0:
                        stack.append((nx, ny))

    def toggle_flag(self, x: int, y: int):
        """
        Toggle flag/question mark on a cell (Microsoft 3-state system)
        States: Hidden -> Flag -> Question -> Hidden
        """
        if (x, y) in self.revealed:
            return  # Can't flag revealed cells

        if (x, y) in self.flagged:
            # Flag -> Question
            self.flagged.remove((x, y))
            self.questioned.add((x, y))
            self.flags_remaining += 1
        elif (x, y) in self.questioned:
            # Question -> Hidden
            self.questioned.remove((x, y))
        else:
            # Hidden -> Flag
            if self.flags_remaining > 0:
                self.flagged.add((x, y))
                self.flags_remaining -= 1

    def get_display_board(self) -> str:
        """
        Generate the visual board display following Discord formatting limits
        """
        if self.width > 16:  # For expert mode, use compact display
            return self._get_compact_display()

        result = ""

        for y in range(self.height):
            for x in range(self.width):
                # Cursor highlight
                if x == self.cursor_x and y == self.cursor_y:
                    result += self.SYMBOLS["cursor"]
                # Flagged cells
                elif (x, y) in self.flagged:
                    result += self.SYMBOLS["flag"]
                # Question marked cells
                elif (x, y) in self.questioned:
                    result += self.SYMBOLS["question"]
                # Revealed cells
                elif (x, y) in self.revealed:
                    if self.board[y][x] == -1:
                        result += self.SYMBOLS["mine"]
                    else:
                        result += self.SYMBOLS["numbers"][self.board[y][x]]
                # Hidden cells
                else:
                    result += self.SYMBOLS["hidden"]
            result += "\n"

        return result

    def _get_compact_display(self) -> str:
        """Compact display for large boards (expert mode)"""
        # For expert mode, show only a portion of the board around cursor
        view_radius = 7
        start_x = max(0, self.cursor_x - view_radius)
        end_x = min(self.width, self.cursor_x + view_radius + 1)
        start_y = max(0, self.cursor_y - view_radius)
        end_y = min(self.height, self.cursor_y + view_radius + 1)

        result = f"**View: ({start_x+1}-{end_x}, {start_y+1}-{end_y}) of ({self.width}x{self.height})**\n"

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if x == self.cursor_x and y == self.cursor_y:
                    result += self.SYMBOLS["cursor"]
                elif (x, y) in self.flagged:
                    result += self.SYMBOLS["flag"]
                elif (x, y) in self.questioned:
                    result += self.SYMBOLS["question"]
                elif (x, y) in self.revealed:
                    if self.board and self.board[y][x] == -1:
                        result += self.SYMBOLS["mine"]
                    elif self.board:
                        result += self.SYMBOLS["numbers"][self.board[y][x]]
                    else:
                        result += self.SYMBOLS["revealed"]
                else:
                    result += self.SYMBOLS["hidden"]
            result += "\n"

        return result

    def move_cursor(self, direction: str):
        """Move cursor in specified direction"""
        if direction == "left":
            self.cursor_x = max(0, self.cursor_x - 1)
        elif direction == "right":
            self.cursor_x = min(self.width - 1, self.cursor_x + 1)
        elif direction == "up":
            self.cursor_y = max(0, self.cursor_y - 1)
        elif direction == "down":
            self.cursor_y = min(self.height - 1, self.cursor_y + 1)

    def get_game_stats(self) -> dict:
        """Get current game statistics"""
        elapsed = 0
        if self.start_time:
            end = self.end_time if self.end_time else time.time()
            elapsed = int(end - self.start_time)

        return {
            "mines_total": self.mines,
            "flags_remaining": self.flags_remaining,
            "cells_remaining": self.cells_remaining - len([c for c in self.revealed if self.board and self.board[c[1]][c[0]] != -1]),
            "time_elapsed": elapsed,
            "difficulty": self.difficulty,
            "board_size": f"{self.width}×{self.height}"
        }


class ClassicGames(commands.Cog):
    """Classic games collection - Original implementations"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, ClassicMinesweeperGame] = {}

    @commands.command(aliases=["mines", "sweeper", "classic-mines"])
    @guild_setting_enabled("minesweeper")
    async def minesweeper(self, ctx, difficulty: str = None, width: int = None, height: int = None, mines: int = None):
        """
        Start a classic Minesweeper game following Microsoft standards

        Usage:
        l.minesweeper - Show difficulty menu
        l.minesweeper beginner - Start beginner game (9×9, 10 mines)
        l.minesweeper intermediate - Start intermediate game (16×16, 40 mines)
        l.minesweeper expert - Start expert game (30×16, 99 mines)
        l.minesweeper custom 12 12 20 - Start custom game (width height mines)
        """

        # Show difficulty menu if no parameters
        if difficulty is None:
            await self._show_difficulty_menu(ctx)
            return

        # Check if player already has a game
        if ctx.author.id in self.active_games:
            await self._show_active_game_warning(ctx)
            return

        # Handle custom difficulty
        if difficulty.lower() == "custom":
            if not all([width, height, mines]):
                await self._show_custom_help(ctx)
                return

            # Validate custom parameters
            if not (5 <= width <= 30 and 5 <= height <= 24 and 1 <= mines <= (width * height - 9)):
                embed = discord.Embed(
                    title="❌ Invalid Custom Parameters",
                    description="Custom game limits:\n• Width: 5-30\n• Height: 5-24\n• Mines: 1 to (width×height-9)",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            game = ClassicMinesweeperGame(width, height, mines, ctx.author.id, "custom")

        # Handle standard difficulties
        elif difficulty.lower() in ClassicMinesweeperGame.DIFFICULTY_LEVELS:
            level = ClassicMinesweeperGame.DIFFICULTY_LEVELS[difficulty.lower()]
            game = ClassicMinesweeperGame(level["width"], level["height"], level["mines"],
                                        ctx.author.id, difficulty.lower())
        else:
            await self._show_invalid_difficulty(ctx)
            return

        # Start the game
        self.active_games[ctx.author.id] = game
        await self._start_game_display(ctx, game)

    async def _show_difficulty_menu(self, ctx):
        """Show the classic difficulty selection menu"""
        embed = discord.Embed(
            title="💣 Classic Minesweeper",
            description="Choose your difficulty level following Microsoft Minesweeper standards",
            color=0x00ff00
        )

        for diff, info in ClassicMinesweeperGame.DIFFICULTY_LEVELS.items():
            if diff == "custom":
                continue

            mine_density = (info["mines"] / (info["width"] * info["height"])) * 100

            embed.add_field(
                name=f"{info['emoji']} {diff.title()}",
                value=f"**{info['width']}×{info['height']}** board\n"
                      f"**{info['mines']}** mines ({mine_density:.1f}%)\n"
                      f"*{info['description']}*",
                inline=True
            )

        embed.add_field(
            name="⚙️ Custom Game",
            value="Create your own board size\nUse: `l.minesweeper custom <width> <height> <mines>`",
            inline=True
        )

        embed.add_field(
            name="🎮 How to Start",
            value=f"Examples:\n"
                  f"• `{ctx.prefix}minesweeper beginner`\n"
                  f"• `{ctx.prefix}minesweeper expert`\n"
                  f"• `{ctx.prefix}minesweeper custom 12 12 20`",
            inline=False
        )

        embed.set_footer(text="💡 New to Minesweeper? Start with 'beginner' difficulty!")
        await ctx.send(embed=embed)

    async def _show_active_game_warning(self, ctx):
        """Show warning about existing active game"""
        embed = discord.Embed(
            title="⚠️ Game Already Active",
            description="You already have a Minesweeper game in progress!",
            color=0xffaa00
        )
        embed.add_field(
            name="Options",
            value=f"• `{ctx.prefix}mines-continue` - Continue current game\n"
                  f"• `{ctx.prefix}mines-quit` - End current game\n"
                  f"• `{ctx.prefix}mines-stats` - View game statistics",
            inline=False
        )
        await ctx.send(embed=embed)

    async def _start_game_display(self, ctx, game):
        """Initialize the game display"""
        difficulty_info = ClassicMinesweeperGame.DIFFICULTY_LEVELS.get(
            game.difficulty, {"emoji": "⚙️", "description": "Custom game"}
        )

        embed = discord.Embed(
            title=f"💣 Classic Minesweeper - {difficulty_info['emoji']} {game.difficulty.title()}",
            description=game.get_display_board(),
            color=0x00ff00
        )

        stats = game.get_game_stats()
        embed.add_field(
            name="📊 Game Info",
            value=f"**Board:** {stats['board_size']}\n"
                  f"**Mines:** {stats['mines_total']}\n"
                  f"**Flags left:** {stats['flags_remaining']}",
            inline=True
        )

        embed.add_field(
            name="🎮 Controls",
            value="⬅️➡️⬆️⬇️ Move cursor\n"
                  "💥 Reveal cell\n"
                  "🚩 Flag/Question cell\n"
                  "❌ Quit game",
            inline=True
        )

        embed.add_field(
            name="📖 Legend",
            value="🟨 Cursor position\n"
                  "⬛ Hidden cell\n"
                  "🚩 Flagged (mine suspected)\n"
                  "❓ Question mark\n"
                  "1️⃣-8️⃣ Adjacent mine count",
            inline=False
        )

        embed.set_footer(text=f"Good luck, {ctx.author.display_name}! Follow Microsoft Minesweeper rules.")

        message = await ctx.send(embed=embed)
        game.message = message

        # Add reaction controls
        reactions = ["⬅️", "➡️", "⬆️", "⬇️", "💥", "🚩", "❌"]
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Start reaction handler
        self.bot.loop.create_task(self._handle_game_reactions(ctx, game))

    async def _handle_game_reactions(self, ctx, game):
        """Handle reaction-based game controls"""
        def check(reaction, user):
            return (user.id == game.player_id and
                   reaction.message.id == game.message.id and
                   not user.bot)

        while not game.game_over:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=check)
                emoji = str(reaction.emoji)

                # Remove user reaction
                try:
                    await reaction.remove(user)
                except:
                    pass

                # Handle controls
                if emoji == "❌":
                    await self._quit_game(game)
                    return
                elif emoji in ["⬅️", "➡️", "⬆️", "⬇️"]:
                    direction_map = {"⬅️": "left", "➡️": "right", "⬆️": "up", "⬇️": "down"}
                    game.move_cursor(direction_map[emoji])
                    await self._update_game_display(game)
                elif emoji == "💥":
                    continue_game = game.reveal_cell(game.cursor_x, game.cursor_y)
                    if game.won or not continue_game:
                        await self._end_game_display(game)
                        return
                    else:
                        await self._update_game_display(game)
                elif emoji == "🚩":
                    game.toggle_flag(game.cursor_x, game.cursor_y)
                    await self._update_game_display(game)

            except asyncio.TimeoutError:
                await self._timeout_game(game)
                return

    async def _update_game_display(self, game):
        """Update the game display with current state"""
        difficulty_info = ClassicMinesweeperGame.DIFFICULTY_LEVELS.get(
            game.difficulty, {"emoji": "⚙️"}
        )

        embed = discord.Embed(
            title=f"💣 Classic Minesweeper - {difficulty_info['emoji']} {game.difficulty.title()}",
            description=game.get_display_board(),
            color=0x00ff00
        )

        stats = game.get_game_stats()
        embed.add_field(
            name="📊 Progress",
            value=f"**Flags left:** {stats['flags_remaining']}\n"
                  f"**Safe cells left:** {stats['cells_remaining']}\n"
                  f"**Time:** {stats['time_elapsed']}s",
            inline=True
        )

        embed.add_field(
            name="📍 Position",
            value=f"Cursor: ({game.cursor_x + 1}, {game.cursor_y + 1})\n"
                  f"Board: {stats['board_size']}",
            inline=True
        )

        await game.message.edit(embed=embed)

    async def _end_game_display(self, game):
        """Display game end screen"""
        stats = game.get_game_stats()

        if game.won:
            embed = discord.Embed(
                title="🎉 Victory! You Won!",
                description=game.get_display_board(),
                color=0x00ff00
            )
            embed.add_field(
                name="🏆 Congratulations!",
                value=f"You successfully cleared the minefield!\n"
                      f"**Time:** {stats['time_elapsed']} seconds\n"
                      f"**Difficulty:** {game.difficulty.title()}\n"
                      f"**Board:** {stats['board_size']}",
                inline=False
            )
        else:
            # Reveal all mines for game over
            for y in range(game.height):
                for x in range(game.width):
                    if game.board and game.board[y][x] == -1:
                        game.revealed.add((x, y))

            embed = discord.Embed(
                title="💥 Game Over!",
                description=game.get_display_board(),
                color=0xff0000
            )
            embed.add_field(
                name="💣 Mine Hit!",
                value=f"Better luck next time!\n"
                      f"**Time survived:** {stats['time_elapsed']} seconds\n"
                      f"**Difficulty:** {game.difficulty.title()}\n"
                      f"**Cells cleared:** {len(game.revealed) - 1}/{stats['cells_remaining'] + len(game.revealed) - 1}",
                inline=False
            )

        embed.add_field(
            name="🔄 Play Again",
            value=f"Use `{self.bot.command_prefix}minesweeper` to start a new game!",
            inline=False
        )

        await game.message.edit(embed=embed)
        await game.message.clear_reactions()

        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    async def _quit_game(self, game):
        """Handle game quit"""
        embed = discord.Embed(
            title="✅ Game Ended",
            description="Thanks for playing Classic Minesweeper!",
            color=0x00ff00
        )

        stats = game.get_game_stats()
        if stats['time_elapsed'] > 0:
            embed.add_field(
                name="📊 Session Stats",
                value=f"**Time played:** {stats['time_elapsed']} seconds\n"
                      f"**Cells revealed:** {len(game.revealed)}\n"
                      f"**Flags placed:** {game.mines - stats['flags_remaining']}",
                inline=False
            )

        await game.message.edit(embed=embed)
        await game.message.clear_reactions()

        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    async def _timeout_game(self, game):
        """Handle game timeout"""
        embed = discord.Embed(
            title="⏰ Game Timed Out",
            description="Your Minesweeper game timed out due to inactivity.",
            color=0xffaa00
        )

        await game.message.edit(embed=embed)
        await game.message.clear_reactions()

        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    # Additional support commands
    @commands.command(aliases=["mines-continue", "mines-show"])
    async def mines_continue(self, ctx):
        """Continue your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active Minesweeper game! Use `l.minesweeper` to start one.")
            return

        game = self.active_games[ctx.author.id]
        await self._update_game_display(game)
        await ctx.send("🔄 Game board updated! Use reactions to continue playing.", delete_after=5)

    @commands.command(aliases=["mines-quit", "mines-end"])
    async def mines_quit(self, ctx):
        """Quit your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active Minesweeper game!")
            return

        game = self.active_games[ctx.author.id]
        await self._quit_game(game)

    @commands.command(aliases=["mines-stats", "mines-info"])
    async def mines_stats(self, ctx):
        """View statistics for your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active Minesweeper game!")
            return

        game = self.active_games[ctx.author.id]
        stats = game.get_game_stats()

        embed = discord.Embed(
            title="📊 Minesweeper Statistics",
            color=0x00ff00
        )

        embed.add_field(
            name="🎮 Game Info",
            value=f"**Difficulty:** {game.difficulty.title()}\n"
                  f"**Board Size:** {stats['board_size']}\n"
                  f"**Total Mines:** {stats['mines_total']}",
            inline=True
        )

        embed.add_field(
            name="⏱️ Progress",
            value=f"**Time Elapsed:** {stats['time_elapsed']}s\n"
                  f"**Cells Revealed:** {len(game.revealed)}\n"
                  f"**Safe Cells Left:** {stats['cells_remaining']}",
            inline=True
        )

        embed.add_field(
            name="🚩 Flags",
            value=f"**Flags Remaining:** {stats['flags_remaining']}\n"
                  f"**Flags Placed:** {stats['mines_total'] - stats['flags_remaining']}\n"
                  f"**Question Marks:** {len(game.questioned)}",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["mines-help", "minesweeper-help"])
    async def mines_help(self, ctx):
        """Get help with Classic Minesweeper"""
        embed = discord.Embed(
            title="💣 Classic Minesweeper Help",
            description="Learn how to play following Microsoft Minesweeper rules",
            color=0x00ff00
        )

        embed.add_field(
            name="🎯 Objective",
            value="Reveal all safe cells without hitting any mines. Use number clues to deduce mine locations.",
            inline=False
        )

        embed.add_field(
            name="🎮 Controls",
            value="**⬅️➡️⬆️⬇️** Move cursor\n"
                  "**💥** Reveal selected cell\n"
                  "**🚩** Cycle: Flag → Question → Hidden\n"
                  "**❌** Quit game",
            inline=True
        )

        embed.add_field(
            name="🗺️ Reading the Board",
            value="**🟨** Your cursor position\n"
                  "**⬛** Hidden cell\n"
                  "**🚩** Flagged (suspected mine)\n"
                  "**❓** Question mark (uncertain)\n"
                  "**1️⃣-8️⃣** Number of adjacent mines\n"
                 "**💣** Mine (game over!)",
           inline=True
       )

       embed.add_field(
           name="🧠 Strategy Tips",
           value="• **Start with corners and edges** - fewer adjacent cells\n"
                 "• **Look for patterns** - numbers tell you exactly how many mines are nearby\n"
                 "• **Use flags wisely** - mark certain mines to avoid accidents\n"
                 "• **Question marks** - use for uncertain cells\n"
                 "• **First click is always safe** - the game ensures this",
           inline=False
       )

       embed.add_field(
           name="🏆 Difficulty Levels",
           value="**Beginner:** 9×9, 10 mines (good for learning)\n"
                 "**Intermediate:** 16×16, 40 mines (moderate challenge)\n"
                 "**Expert:** 30×16, 99 mines (for experienced players)\n"
                 "**Custom:** Design your own board",
           inline=False
       )

       embed.add_field(
           name="📚 Commands",
           value=f"`{ctx.prefix}minesweeper` - Start new game\n"
                 f"`{ctx.prefix}mines-continue` - Resume current game\n"
                 f"`{ctx.prefix}mines-stats` - View game statistics\n"
                 f"`{ctx.prefix}mines-quit` - End current game",
           inline=False
       )

       embed.set_footer(text="💡 Pro tip: The numbers are your best friend - they never lie!")
       await ctx.send(embed=embed)

   async def _show_custom_help(self, ctx):
       """Show help for custom game creation"""
       embed = discord.Embed(
           title="⚙️ Custom Minesweeper Game",
           description="Create your own Minesweeper challenge!",
           color=0x00ff00
       )

       embed.add_field(
           name="📐 Usage",
           value=f"`{ctx.prefix}minesweeper custom <width> <height> <mines>`",
           inline=False
       )

       embed.add_field(
           name="📏 Limits",
           value="**Width:** 5-30 cells\n**Height:** 5-24 cells\n**Mines:** 1 to (width×height-9)",
           inline=True
       )

       embed.add_field(
           name="💡 Examples",
           value=f"`{ctx.prefix}minesweeper custom 12 12 20`\n"
                 f"`{ctx.prefix}minesweeper custom 20 10 35`\n"
                 f"`{ctx.prefix}minesweeper custom 8 8 12`",
           inline=True
       )

       embed.add_field(
           name="⚖️ Balance Tips",
           value="• **10-15%** mine density = Easy\n"
                 "• **15-20%** mine density = Medium\n"
                 "• **20%+** mine density = Hard\n"
                 "• Leave at least 9 safe cells for solvability",
           inline=False
       )

       await ctx.send(embed=embed)

   async def _show_invalid_difficulty(self, ctx):
       """Show error for invalid difficulty"""
       embed = discord.Embed(
           title="❌ Invalid Difficulty",
           description="That's not a valid difficulty level.",
           color=0xff0000
       )

       valid_difficulties = list(ClassicMinesweeperGame.DIFFICULTY_LEVELS.keys())
       embed.add_field(
           name="✅ Valid Options",
           value=", ".join(valid_difficulties),
           inline=False
       )

       embed.add_field(
           name="💡 Try Instead",
           value=f"`{ctx.prefix}minesweeper` - See all options\n"
                 f"`{ctx.prefix}minesweeper beginner` - Start easy game",
           inline=False
       )

       await ctx.send(embed=embed)


async def setup(bot):
   await bot.add_cog(ClassicGames(bot))