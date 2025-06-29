"""
Classic Minesweeper Game - Following Microsoft Standards
"""

import discord
from discord.ext import commands
import random
import asyncio
from typing import Dict, Tuple, Set
from utils.decorators import guild_setting_enabled
import time


class ClassicMinesweeperGame:
    """Classic Minesweeper Game Implementation"""

    DIFFICULTY_LEVELS = {
        "beginner": {"width": 9, "height": 9, "mines": 10, "description": "Perfect for new players", "emoji": "🟢"},
        "intermediate": {"width": 16, "height": 16, "mines": 40, "description": "A good challenge", "emoji": "🟡"},
        "expert": {"width": 30, "height": 16, "mines": 99, "description": "For experienced players", "emoji": "🔴"},
        "custom": {"width": 0, "height": 0, "mines": 0, "description": "Custom game settings", "emoji": "⚙️"}
    }

    SYMBOLS = {
        "hidden": "⬛", "revealed": "⬜", "flag": "🚩", "mine": "💣", "question": "❓", "cursor": "🟨",
        "numbers": ["⬜", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    }

    def __init__(self, width: int, height: int, mines: int, player_id: int, difficulty: str = "custom"):
        self.width = min(width, 30)
        self.height = min(height, 24)
        self.mines = min(mines, (self.width * self.height) - 9)
        self.player_id = player_id
        self.difficulty = difficulty
        self.board = None
        self.revealed: Set[Tuple[int, int]] = set()
        self.flagged: Set[Tuple[int, int]] = set()
        self.questioned: Set[Tuple[int, int]] = set()
        self.game_over = False
        self.won = False
        self.first_reveal = True
        self.start_time = None
        self.end_time = None
        self.message = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.cells_remaining = (self.width * self.height) - self.mines
        self.flags_remaining = self.mines

    def _generate_board_safe(self, safe_x: int, safe_y: int):
        board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        safe_zone = set()
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                sx, sy = safe_x + dx, safe_y + dy
                if 0 <= sx < self.width and 0 <= sy < self.height:
                    safe_zone.add((sx, sy))

        available_positions = [(x, y) for y in range(self.height) for x in range(self.width) if (x, y) not in safe_zone]
        mines_to_place = min(self.mines, len(available_positions))
        mine_positions = random.sample(available_positions, mines_to_place)

        for x, y in mine_positions:
            board[y][x] = -1

        for y in range(self.height):
            for x in range(self.width):
                if board[y][x] != -1:
                    count = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < self.height and 0 <= nx < self.width and board[ny][nx] == -1:
                                count += 1
                    board[y][x] = count

        self.board = board
        self.mines = len(mine_positions)
        self.flags_remaining = self.mines

    def reveal_cell(self, x: int, y: int) -> bool:
        if self.first_reveal:
            self._generate_board_safe(x, y)
            self.first_reveal = False
            self.start_time = time.time()

        if (x, y) in self.flagged or (x, y) in self.revealed:
            return True

        self.revealed.add((x, y))
        self.questioned.discard((x, y))

        if self.board[y][x] == -1:
            self.game_over = True
            self.end_time = time.time()
            return False

        if self.board[y][x] == 0:
            self._flood_reveal(x, y)

        revealed_safe_cells = len([cell for cell in self.revealed if self.board[cell[1]][cell[0]] != -1])
        if revealed_safe_cells == self.cells_remaining:
            self.won = True
            self.game_over = True
            self.end_time = time.time()
            for y in range(self.height):
                for x in range(self.width):
                    if self.board[y][x] == -1:
                        self.flagged.add((x, y))
        return True

    def _flood_reveal(self, start_x: int, start_y: int):
        stack = [(start_x, start_y)]
        while stack:
            x, y = stack.pop()
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if (not (0 <= nx < self.width and 0 <= ny < self.height) or
                            (nx, ny) in self.revealed or (nx, ny) in self.flagged):
                        continue
                    self.revealed.add((nx, ny))
                    self.questioned.discard((nx, ny))
                    if self.board[ny][nx] == 0:
                        stack.append((nx, ny))

    def toggle_flag(self, x: int, y: int):
        if (x, y) in self.revealed:
            return
        if (x, y) in self.flagged:
            self.flagged.remove((x, y))
            self.questioned.add((x, y))
            self.flags_remaining += 1
        elif (x, y) in self.questioned:
            self.questioned.remove((x, y))
        else:
            if self.flags_remaining > 0:
                self.flagged.add((x, y))
                self.flags_remaining -= 1

    def get_display_board(self) -> str:
        if self.width > 16:
            return self._get_compact_display()
        result = ""
        for y in range(self.height):
            for x in range(self.width):
                if x == self.cursor_x and y == self.cursor_y:
                    result += self.SYMBOLS["cursor"]
                elif (x, y) in self.flagged:
                    result += self.SYMBOLS["flag"]
                elif (x, y) in self.questioned:
                    result += self.SYMBOLS["question"]
                elif (x, y) in self.revealed:
                    if self.board[y][x] == -1:
                        result += self.SYMBOLS["mine"]
                    else:
                        result += self.SYMBOLS["numbers"][self.board[y][x]]
                else:
                    result += self.SYMBOLS["hidden"]
            result += "\n"
        return result

    def _get_compact_display(self) -> str:
        view_radius = 7
        start_x = max(0, self.cursor_x - view_radius)
        end_x = min(self.width, self.cursor_x + view_radius + 1)
        start_y = max(0, self.cursor_y - view_radius)
        end_y = min(self.height, self.cursor_y + view_radius + 1)
        result = f"**View: ({start_x + 1}-{end_x}, {start_y + 1}-{end_y}) of ({self.width}x{self.height})**\n"
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
        if direction == "left":
            self.cursor_x = max(0, self.cursor_x - 1)
        elif direction == "right":
            self.cursor_x = min(self.width - 1, self.cursor_x + 1)
        elif direction == "up":
            self.cursor_y = max(0, self.cursor_y - 1)
        elif direction == "down":
            self.cursor_y = min(self.height - 1, self.cursor_y + 1)

    def get_game_stats(self) -> dict:
        elapsed = 0
        if self.start_time:
            end = self.end_time if self.end_time else time.time()
            elapsed = int(end - self.start_time)
        return {
            "mines_total": self.mines, "flags_remaining": self.flags_remaining,
            "cells_remaining": self.cells_remaining - len(
                [c for c in self.revealed if self.board and self.board[c[1]][c[0]] != -1]),
            "time_elapsed": elapsed, "difficulty": self.difficulty, "board_size": f"{self.width}×{self.height}"
        }


class ClassicGames(commands.Cog):
    """Classic games collection"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, ClassicMinesweeperGame] = {}

    @commands.command(aliases=["mines", "sweeper", "classic-mines"])
    @guild_setting_enabled("minesweeper")
    async def minesweeper(self, ctx, difficulty: str = None, width: int = None, height: int = None, mines: int = None):
        """Start a classic Minesweeper game following Microsoft standards"""
        if difficulty is None:
            await self._show_difficulty_menu(ctx)
            return
        if ctx.author.id in self.active_games:
            await self._show_active_game_warning(ctx)
            return
        if difficulty.lower() == "custom":
            if not all([width, height, mines]):
                await self._show_custom_help(ctx)
                return
            if not (5 <= width <= 30 and 5 <= height <= 24 and 1 <= mines <= (width * height - 9)):
                embed = discord.Embed(title="❌ Invalid Custom Parameters",
                                      description="Custom game limits:\n• Width: 5-30\n• Height: 5-24\n• Mines: 1 to (width×height-9)",
                                      color=0xff0000)
                await ctx.send(embed=embed)
                return
            game = ClassicMinesweeperGame(width, height, mines, ctx.author.id, "custom")
        elif difficulty.lower() in ClassicMinesweeperGame.DIFFICULTY_LEVELS:
            level = ClassicMinesweeperGame.DIFFICULTY_LEVELS[difficulty.lower()]
            game = ClassicMinesweeperGame(level["width"], level["height"], level["mines"], ctx.author.id,
                                          difficulty.lower())
        else:
            await self._show_invalid_difficulty(ctx)
            return
        self.active_games[ctx.author.id] = game
        await self._start_game_display(ctx, game)

    async def _show_difficulty_menu(self, ctx):
        embed = discord.Embed(title="💣 Classic Minesweeper", description="Choose your difficulty level", color=0x00ff00)
        for diff, info in ClassicMinesweeperGame.DIFFICULTY_LEVELS.items():
            if diff == "custom":
                continue
            mine_density = (info["mines"] / (info["width"] * info["height"])) * 100
            embed.add_field(name=f"{info['emoji']} {diff.title()}",
                            value=f"**{info['width']}×{info['height']}** board\n**{info['mines']}** mines ({mine_density:.1f}%)\n*{info['description']}*",
                            inline=True)
        embed.add_field(name="⚙️ Custom Game",
                        value="Create your own board\n`l.minesweeper custom <width> <height> <mines>`", inline=True)
        embed.set_footer(text="💡 New to Minesweeper? Start with 'beginner'!")
        await ctx.send(embed=embed)

    async def _show_active_game_warning(self, ctx):
        embed = discord.Embed(title="⚠️ Game Already Active",
                              description="You already have a Minesweeper game in progress!", color=0xffaa00)
        embed.add_field(name="Options",
                        value=f"• `{ctx.prefix}mines-continue` - Continue current game\n• `{ctx.prefix}mines-quit` - End current game",
                        inline=False)
        await ctx.send(embed=embed)

    async def _start_game_display(self, ctx, game):
        difficulty_info = ClassicMinesweeperGame.DIFFICULTY_LEVELS.get(game.difficulty,
                                                                       {"emoji": "⚙️", "description": "Custom game"})
        embed = discord.Embed(title=f"💣 Classic Minesweeper - {difficulty_info['emoji']} {game.difficulty.title()}",
                              description=game.get_display_board(), color=0x00ff00)
        stats = game.get_game_stats()
        embed.add_field(name="📊 Game Info",
                        value=f"**Board:** {stats['board_size']}\n**Mines:** {stats['mines_total']}\n**Flags left:** {stats['flags_remaining']}",
                        inline=True)
        embed.add_field(name="🎮 Controls",
                        value="⬅️➡️⬆️⬇️ Move cursor\n💥 Reveal cell\n🚩 Flag/Question cell\n❌ Quit game", inline=True)
        embed.set_footer(text=f"Good luck, {ctx.author.display_name}!")
        message = await ctx.send(embed=embed)
        game.message = message
        reactions = ["⬅️", "➡️", "⬆️", "⬇️", "💥", "🚩", "❌"]
        for reaction in reactions:
            await message.add_reaction(reaction)
        self.bot.loop.create_task(self._handle_game_reactions(ctx, game))

    async def _handle_game_reactions(self, ctx, game):
        def check(reaction, user):
            return (user.id == game.player_id and reaction.message.id == game.message.id and not user.bot)

        while not game.game_over:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
                emoji = str(reaction.emoji)
                try:
                    await reaction.remove(user)
                except:
                    pass
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
        difficulty_info = ClassicMinesweeperGame.DIFFICULTY_LEVELS.get(game.difficulty, {"emoji": "⚙️"})
        embed = discord.Embed(title=f"💣 Classic Minesweeper - {difficulty_info['emoji']} {game.difficulty.title()}",
                              description=game.get_display_board(), color=0x00ff00)
        stats = game.get_game_stats()
        embed.add_field(name="📊 Progress",
                        value=f"**Flags left:** {stats['flags_remaining']}\n**Safe cells left:** {stats['cells_remaining']}\n**Time:** {stats['time_elapsed']}s",
                        inline=True)
        embed.add_field(name="📍 Position",
                        value=f"Cursor: ({game.cursor_x + 1}, {game.cursor_y + 1})\nBoard: {stats['board_size']}",
                        inline=True)
        await game.message.edit(embed=embed)

    async def _end_game_display(self, game):
        stats = game.get_game_stats()
        if game.won:
            embed = discord.Embed(title="🎉 Victory! You Won!", description=game.get_display_board(), color=0x00ff00)
            embed.add_field(name="🏆 Congratulations!",
                            value=f"You cleared the minefield!\n**Time:** {stats['time_elapsed']} seconds\n**Difficulty:** {game.difficulty.title()}",
                            inline=False)
        else:
            for y in range(game.height):
                for x in range(game.width):
                    if game.board and game.board[y][x] == -1:
                        game.revealed.add((x, y))
            embed = discord.Embed(title="💥 Game Over!", description=game.get_display_board(), color=0xff0000)
            embed.add_field(name="💣 Mine Hit!",
                            value=f"Better luck next time!\n**Time:** {stats['time_elapsed']} seconds\n**Difficulty:** {game.difficulty.title()}",
                            inline=False)
        embed.add_field(name="🔄 Play Again", value=f"Use `{self.bot.command_prefix}minesweeper` to start a new game!",
                        inline=False)
        await game.message.edit(embed=embed)
        await game.message.clear_reactions()
        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    async def _quit_game(self, game):
        embed = discord.Embed(title="✅ Game Ended", description="Thanks for playing Classic Minesweeper!",
                              color=0x00ff00)
        await game.message.edit(embed=embed)
        await game.message.clear_reactions()
        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    async def _timeout_game(self, game):
        embed = discord.Embed(title="⏰ Game Timed Out",
                              description="Your Minesweeper game timed out due to inactivity.", color=0xffaa00)
        await game.message.edit(embed=embed)
        await game.message.clear_reactions()
        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    @commands.command(aliases=["mines-continue"])
    async def mines_continue(self, ctx):
        """Continue your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active Minesweeper game!")
            return
        game = self.active_games[ctx.author.id]
        await self._update_game_display(game)
        await ctx.send("🔄 Game board updated!", delete_after=5)

    @commands.command(aliases=["mines-quit"])
    async def mines_quit(self, ctx):
        """Quit your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active Minesweeper game!")
            return
        game = self.active_games[ctx.author.id]
        await self._quit_game(game)

    @commands.command(aliases=["mines-stats"])
    async def mines_stats(self, ctx):
        """View statistics for your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active Minesweeper game!")
            return
        game = self.active_games[ctx.author.id]
        stats = game.get_game_stats()
        embed = discord.Embed(title="📊 Minesweeper Statistics", color=0x00ff00)
        embed.add_field(name="🎮 Game Info",
                        value=f"**Difficulty:** {game.difficulty.title()}\n**Board Size:** {stats['board_size']}\n**Total Mines:** {stats['mines_total']}",
                        inline=True)
        embed.add_field(name="⏱️ Progress",
                        value=f"**Time Elapsed:** {stats['time_elapsed']}s\n**Cells Revealed:** {len(game.revealed)}\n**Safe Cells Left:** {stats['cells_remaining']}",
                        inline=True)
        embed.add_field(name="🚩 Flags",
                        value=f"**Flags Remaining:** {stats['flags_remaining']}\n**Flags Placed:** {stats['mines_total'] - stats['flags_remaining']}\n**Question Marks:** {len(game.questioned)}",
                        inline=True)
        await ctx.send(embed=embed)

    async def _show_custom_help(self, ctx):
        embed = discord.Embed(title="⚙️ Custom Minesweeper Game", description="Create your own Minesweeper challenge!",
                              color=0x00ff00)
        embed.add_field(name="📐 Usage", value=f"`{ctx.prefix}minesweeper custom <width> <height> <mines>`",
                        inline=False)
        embed.add_field(name="📏 Limits",
                        value="**Width:** 5-30 cells\n**Height:** 5-24 cells\n**Mines:** 1 to (width×height-9)",
                        inline=True)
        embed.add_field(name="💡 Examples",
                        value=f"`{ctx.prefix}minesweeper custom 12 12 20`\n`{ctx.prefix}minesweeper custom 20 10 35`",
                        inline=True)
        await ctx.send(embed=embed)

    async def _show_invalid_difficulty(self, ctx):
        embed = discord.Embed(title="❌ Invalid Difficulty", description="That's not a valid difficulty level.",
                              color=0xff0000)
        valid_difficulties = list(ClassicMinesweeperGame.DIFFICULTY_LEVELS.keys())
        embed.add_field(name="✅ Valid Options", value=", ".join(valid_difficulties), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ClassicGames(bot))