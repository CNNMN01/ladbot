"""
Classic Minesweeper Game - Following Microsoft Standards
Complete version with comprehensive error handling
"""

import discord
from discord.ext import commands
import random
import asyncio
from typing import Dict, Tuple, Set, Optional
from utils.decorators import guild_setting_enabled
import time
import logging

logger = logging.getLogger(__name__)


class ClassicMinesweeperGame:
    """Classic Minesweeper Game Implementation with comprehensive error handling"""

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
        self.width = min(max(width, 5), 30)  # Ensure bounds
        self.height = min(max(height, 5), 24)
        self.mines = min(max(mines, 1), (self.width * self.height) - 9)
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
        self.is_active = True

    def _generate_board_safe(self, safe_x: int, safe_y: int):
        """Generate board with safe first click"""
        try:
            board = [[0 for _ in range(self.width)] for _ in range(self.height)]
            safe_zone = set()

            # Create 3x3 safe zone around first click
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    sx, sy = safe_x + dx, safe_y + dy
                    if 0 <= sx < self.width and 0 <= sy < self.height:
                        safe_zone.add((sx, sy))

            # Get available positions for mines
            available_positions = [(x, y) for y in range(self.height) for x in range(self.width) if (x, y) not in safe_zone]
            mines_to_place = min(self.mines, len(available_positions))

            if mines_to_place > 0:
                mine_positions = random.sample(available_positions, mines_to_place)
                for x, y in mine_positions:
                    board[y][x] = -1

            # Calculate adjacent numbers
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
            self.mines = mines_to_place
            self.flags_remaining = self.mines
            logger.debug(f"Board generated: {self.width}x{self.height}, {self.mines} mines")

        except Exception as e:
            logger.error(f"Error generating board: {e}")
            # Fallback: create empty board
            self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]

    def reveal_cell(self, x: int, y: int) -> bool:
        """Reveal a cell with comprehensive error handling"""
        try:
            # Validate coordinates
            if not (0 <= x < self.width and 0 <= y < self.height):
                logger.warning(f"Invalid coordinates: ({x}, {y})")
                return True

            # Generate board on first reveal
            if self.first_reveal:
                self._generate_board_safe(x, y)
                self.first_reveal = False
                self.start_time = time.time()

            # Check if already revealed or flagged
            if (x, y) in self.flagged or (x, y) in self.revealed:
                return True

            # Reveal the cell
            self.revealed.add((x, y))
            self.questioned.discard((x, y))

            # Check for mine
            if self.board and self.board[y][x] == -1:
                self.game_over = True
                self.end_time = time.time()
                self.is_active = False
                return False

            # Flood fill for empty cells
            if self.board and self.board[y][x] == 0:
                self._flood_reveal(x, y)

            # Check win condition
            revealed_safe_cells = len([cell for cell in self.revealed
                                     if self.board and self.board[cell[1]][cell[0]] != -1])
            if revealed_safe_cells >= self.cells_remaining:
                self.won = True
                self.game_over = True
                self.end_time = time.time()
                self.is_active = False
                # Auto-flag remaining mines
                if self.board:
                    for y in range(self.height):
                        for x in range(self.width):
                            if self.board[y][x] == -1:
                                self.flagged.add((x, y))

            return True

        except Exception as e:
            logger.error(f"Error revealing cell ({x}, {y}): {e}")
            return True

    def _flood_reveal(self, start_x: int, start_y: int):
        """Flood fill reveal with error handling"""
        try:
            stack = [(start_x, start_y)]
            processed = set()

            while stack and len(processed) < 200:  # Prevent infinite loops
                x, y = stack.pop()
                if (x, y) in processed:
                    continue
                processed.add((x, y))

                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if (not (0 <= nx < self.width and 0 <= ny < self.height) or
                            (nx, ny) in self.revealed or (nx, ny) in self.flagged or (nx, ny) in processed):
                            continue
                        self.revealed.add((nx, ny))
                        self.questioned.discard((nx, ny))
                        if self.board and self.board[ny][nx] == 0:
                            stack.append((nx, ny))

        except Exception as e:
            logger.error(f"Error in flood reveal: {e}")

    def toggle_flag(self, x: int, y: int):
        """Toggle flag with validation"""
        try:
            if not (0 <= x < self.width and 0 <= y < self.height) or (x, y) in self.revealed:
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

        except Exception as e:
            logger.error(f"Error toggling flag at ({x}, {y}): {e}")

    def get_display_board(self) -> str:
        """Get board display with error handling"""
        try:
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
                        if self.board and self.board[y][x] == -1:
                            result += self.SYMBOLS["mine"]
                        elif self.board:
                            result += self.SYMBOLS["numbers"][min(self.board[y][x], 8)]
                        else:
                            result += self.SYMBOLS["revealed"]
                    else:
                        result += self.SYMBOLS["hidden"]
                result += "\n"
            return result

        except Exception as e:
            logger.error(f"Error generating display board: {e}")
            return "❌ Error displaying board"

    def _get_compact_display(self) -> str:
        """Compact display for large boards"""
        try:
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
                            result += self.SYMBOLS["numbers"][min(self.board[y][x], 8)]
                        else:
                            result += self.SYMBOLS["revealed"]
                    else:
                        result += self.SYMBOLS["hidden"]
                result += "\n"
            return result

        except Exception as e:
            logger.error(f"Error generating compact display: {e}")
            return "❌ Error displaying board"

    def move_cursor(self, direction: str):
        """Move cursor with bounds checking"""
        try:
            if direction == "left":
                self.cursor_x = max(0, self.cursor_x - 1)
            elif direction == "right":
                self.cursor_x = min(self.width - 1, self.cursor_x + 1)
            elif direction == "up":
                self.cursor_y = max(0, self.cursor_y - 1)
            elif direction == "down":
                self.cursor_y = min(self.height - 1, self.cursor_y + 1)
        except Exception as e:
            logger.error(f"Error moving cursor: {e}")

    def get_game_stats(self) -> dict:
        """Get game statistics with error handling"""
        try:
            elapsed = 0
            if self.start_time:
                end = self.end_time if self.end_time else time.time()
                elapsed = int(end - self.start_time)

            safe_cells_revealed = 0
            if self.board:
                safe_cells_revealed = len([c for c in self.revealed if self.board[c[1]][c[0]] != -1])

            return {
                "mines_total": self.mines,
                "flags_remaining": self.flags_remaining,
                "cells_remaining": max(0, self.cells_remaining - safe_cells_revealed),
                "time_elapsed": elapsed,
                "difficulty": self.difficulty,
                "board_size": f"{self.width}×{self.height}",
                "is_active": self.is_active
            }
        except Exception as e:
            logger.error(f"Error getting game stats: {e}")
            return {"error": "Stats unavailable"}

    def cleanup(self):
        """Clean up game resources"""
        try:
            self.is_active = False
            self.message = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class ClassicGames(commands.Cog):
    """Classic games collection"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, ClassicMinesweeperGame] = {}

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        try:
            for game in self.active_games.values():
                game.cleanup()
            self.active_games.clear()
        except Exception as e:
            logger.error(f"Error during cog unload: {e}")

    @commands.command(aliases=["mines", "sweeper", "classic-mines"])
    @guild_setting_enabled("minesweeper")
    async def minesweeper(self, ctx, difficulty: str = None, width: int = None, height: int = None, mines: int = None):
        """Start a classic Minesweeper game following Microsoft standards"""
        try:
            if difficulty is None:
                await self._show_difficulty_menu(ctx)
                return

            if ctx.author.id in self.active_games:
                await self._show_active_game_warning(ctx)
                return

            # Handle custom difficulty
            if difficulty.lower() == "custom":
                if not all([width, height, mines]):
                    await self._show_custom_help(ctx)
                    return

                if not (5 <= width <= 30 and 5 <= height <= 24 and 1 <= mines <= (width * height - 9)):
                    embed = discord.Embed(
                        title="❌ Invalid Custom Parameters",
                        description="Custom game limits:\n• Width: 5-30\n• Height: 5-24\n• Mines: 1 to (width×height-9)",
                        color=0xff0000
                    )
                    await ctx.send(embed=embed)
                    return

                game = ClassicMinesweeperGame(width, height, mines, ctx.author.id, "custom")

            elif difficulty.lower() in ClassicMinesweeperGame.DIFFICULTY_LEVELS:
                level = ClassicMinesweeperGame.DIFFICULTY_LEVELS[difficulty.lower()]
                game = ClassicMinesweeperGame(level["width"], level["height"], level["mines"], ctx.author.id, difficulty.lower())
            else:
                await self._show_invalid_difficulty(ctx)
                return

            self.active_games[ctx.author.id] = game
            await self._start_game_display(ctx, game)

        except Exception as e:
            logger.error(f"Error starting minesweeper: {e}")
            await ctx.send("❌ Error starting game. Please try again.")

    async def _show_difficulty_menu(self, ctx):
        """Show difficulty menu with error handling"""
        try:
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
                    value=f"**{info['width']}×{info['height']}** board\n**{info['mines']}** mines ({mine_density:.1f}%)\n*{info['description']}*",
                    inline=True
                )

            embed.add_field(
                name="⚙️ Custom Game",
                value="Create your own board size\nUse: `l.minesweeper custom <width> <height> <mines>`",
                inline=True
            )

            embed.add_field(
                name="🎮 How to Start",
                value=f"Examples:\n• `{ctx.prefix}minesweeper beginner`\n• `{ctx.prefix}minesweeper expert`\n• `{ctx.prefix}minesweeper custom 12 12 20`",
                inline=False
            )

            embed.set_footer(text="💡 New to Minesweeper? Start with 'beginner' difficulty!")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing difficulty menu: {e}")
            await ctx.send("❌ Error displaying menu. Try: `l.minesweeper beginner`")

    async def _show_active_game_warning(self, ctx):
        """Show active game warning with error handling"""
        try:
            embed = discord.Embed(
                title="⚠️ Game Already Active",
                description="You already have a Minesweeper game in progress!",
                color=0xffaa00
            )
            embed.add_field(
                name="Options",
                value=f"• `{ctx.prefix}mines-continue` - Continue current game\n• `{ctx.prefix}mines-quit` - End current game\n• `{ctx.prefix}mines-stats` - View game statistics",
                inline=False
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error showing active game warning: {e}")
            await ctx.send("❌ You already have an active game. Use `l.mines-quit` to end it.")

    async def _start_game_display(self, ctx, game):
        """Start game display with comprehensive error handling"""
        try:
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
                value=f"**Board:** {stats['board_size']}\n**Mines:** {stats['mines_total']}\n**Flags left:** {stats['flags_remaining']}",
                inline=True
            )

            embed.add_field(
                name="🎮 Controls",
                value="⬅️➡️⬆️⬇️ Move cursor\n💥 Reveal cell\n🚩 Flag/Question cell\n❌ Quit game",
                inline=True
            )

            embed.add_field(
                name="📖 Legend",
                value="🟨 Cursor position\n⬛ Hidden cell\n🚩 Flagged (mine suspected)\n❓ Question mark\n1️⃣-8️⃣ Adjacent mine count",
                inline=False
            )

            embed.set_footer(text=f"Good luck, {ctx.author.display_name}! Follow Microsoft Minesweeper rules.")

            message = await ctx.send(embed=embed)
            game.message = message

            # Add reaction controls
            reactions = ["⬅️", "➡️", "⬆️", "⬇️", "💥", "🚩", "❌"]
            for reaction in reactions:
                try:
                    await message.add_reaction(reaction)
                except discord.errors.NotFound:
                    break
                except Exception as e:
                    logger.warning(f"Error adding reaction {reaction}: {e}")

            # Start reaction handler
            self.bot.loop.create_task(self._handle_game_reactions(ctx, game))

        except Exception as e:
            logger.error(f"Error starting game display: {e}")
            await ctx.send("❌ Error creating game display. Game may not work properly.")

    async def _handle_game_reactions(self, ctx, game):
        """Handle reactions with comprehensive error handling"""
        def check(reaction, user):
            return (user.id == game.player_id and
                   reaction.message.id == game.message.id and
                   not user.bot)

        while game.is_active and not game.game_over:
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
                    await self._force_quit_game(ctx, game)
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
            except Exception as e:
                logger.error(f"Error handling reaction: {e}")
                break

    async def _update_game_display(self, game):
        """Update game display with error handling"""
        try:
            if not game.message or not game.is_active:
                return

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
                value=f"**Flags left:** {stats['flags_remaining']}\n**Safe cells left:** {stats['cells_remaining']}\n**Time:** {stats['time_elapsed']}s",
                inline=True
            )

            embed.add_field(
                name="📍 Position",
                value=f"Cursor: ({game.cursor_x + 1}, {game.cursor_y + 1})\nBoard: {stats['board_size']}",
                inline=True
            )

            await game.message.edit(embed=embed)

        except discord.errors.NotFound:
            # Message was deleted
            game.cleanup()
            if game.player_id in self.active_games:
                del self.active_games[game.player_id]
        except Exception as e:
            logger.error(f"Error updating game display: {e}")

    async def _end_game_display(self, game):
        """End game display with error handling"""
        try:
            stats = game.get_game_stats()

            if game.won:
                embed = discord.Embed(
                    title="🎉 Victory! You Won!",
                    description=game.get_display_board(),
                    color=0x00ff00
                )
                embed.add_field(
                    name="🏆 Congratulations!",
                    value=f"You successfully cleared the minefield!\n**Time:** {stats['time_elapsed']} seconds\n**Difficulty:** {game.difficulty.title()}\n**Board:** {stats['board_size']}",
                    inline=False
                )
            else:
                # Reveal all mines for game over
                if game.board:
                    for y in range(game.height):
                        for x in range(game.width):
                            if game.board[y][x] == -1:
                                game.revealed.add((x, y))

                embed = discord.Embed(
                    title="💥 Game Over!",
                    description=game.get_display_board(),
                    color=0xff0000
                )
                embed.add_field(
                    name="💣 Mine Hit!",
                    value=f"Better luck next time!\n**Time survived:** {stats['time_elapsed']} seconds\n**Difficulty:** {game.difficulty.title()}\n**Cells cleared:** {len(game.revealed) - 1}",
                    inline=False
                )

            embed.add_field(
                name="🔄 Play Again",
                value=f"Use `{self.bot.command_prefix}minesweeper` to start a new game!",
                inline=False
            )

            if game.message:
                await game.message.edit(embed=embed)
                try:
                    await game.message.clear_reactions()
                except:
                    pass

            # Clean up
            game.cleanup()
            if game.player_id in self.active_games:
                del self.active_games[game.player_id]

        except Exception as e:
            logger.error(f"Error ending game display: {e}")
            await self._force_cleanup_game(game)

    async def _force_quit_game(self, ctx, game):
        """Force quit with comprehensive cleanup"""
        try:
            embed = discord.Embed(
                title="✅ Game Ended",
                description="Thanks for playing Classic Minesweeper!",
                color=0x00ff00
            )

            stats = game.get_game_stats()
            if stats.get('time_elapsed', 0) > 0:
                embed.add_field(
                    name="📊 Session Stats",
                    value=f"**Time played:** {stats['time_elapsed']} seconds\n**Cells revealed:** {len(game.revealed)}\n**Flags placed:** {game.mines - stats['flags_remaining']}",
                    inline=False
                )

            if game.message:
                await game.message.edit(embed=embed)
                try:
                    await game.message.clear_reactions()
                except:
                    pass

            # Clean up
            game.cleanup()
            if game.player_id in self.active_games:
                del self.active_games[game.player_id]

            await ctx.send("✅ Minesweeper game successfully ended!")

        except Exception as e:
            logger.error(f"Error force quitting game: {e}")
            await self._force_cleanup_game(game)
            await ctx.send("✅ Game ended (with cleanup errors)")

    async def _force_cleanup_game(self, game):
        """Emergency cleanup"""
        try:
            game.cleanup()
            if game.player_id in self.active_games:
                del self.active_games[game.player_id]
        except Exception as e:
            logger.error(f"Error in force cleanup: {e}")

    async def _timeout_game(self, game):
        """Handle game timeout with cleanup"""
        try:
            embed = discord.Embed(
                title="⏰ Game Timed Out",
                description="Your Minesweeper game timed out due to inactivity.",
                color=0xffaa00
            )

            if game.message:
                await game.message.edit(embed=embed)
                try:
                    await game.message.clear_reactions()
                except:
                    pass

            game.cleanup()
            if game.player_id in self.active_games:
                del self.active_games[game.player_id]

        except Exception as e:
            logger.error(f"Error timing out game: {e}")
            await self._force_cleanup_game(game)

    @commands.command(aliases=["mines-continue", "mines-show"])
    async def mines_continue(self, ctx):
        """Continue current game with error handling"""
        try:
            if ctx.author.id not in self.active_games:
                await ctx.send("❌ You don't have an active Minesweeper game! Use `l.minesweeper` to start one.")
                return

            game = self.active_games[ctx.author.id]
            if not game.is_active:
                del self.active_games[ctx.author.id]
                await ctx.send("❌ Your game is no longer active. Use `l.minesweeper` to start a new one.")
                return

            await self._update_game_display(game)
            await ctx.send("🔄 Game board updated! Use reactions to continue playing.", delete_after=5)

        except Exception as e:
            logger.error(f"Error continuing game: {e}")
            await ctx.send("❌ Error accessing your game. It may have expired.")

    @commands.command(aliases=["mines-quit", "mines-end", "minquit"])
    async def mines_quit(self, ctx):
        """Quit current game with comprehensive error handling"""
        try:
            if ctx.author.id not in self.active_games:
                await ctx.send("❌ You don't have an active Minesweeper game!")
                return

            game = self.active_games[ctx.author.id]
            await self._force_quit_game(ctx, game)

        except Exception as e:
            logger.error(f"Error quitting game: {e}")
            # Emergency cleanup
            try:
                if ctx.author.id in self.active_games:
                    game = self.active_games[ctx.author.id]
                    game.cleanup()
                    del self.active_games[ctx.author.id]
                await ctx.send("✅ Game forcefully ended!")
            except Exception as cleanup_error:
                logger.error(f"Error in emergency cleanup: {cleanup_error}")
                await ctx.send("⚠️ Game ended but cleanup failed. Please try starting a new game.")

        @commands.command(aliases=["mines-stats", "mines-info"])
        async def mines_stats(self, ctx):
            """View game statistics with error handling"""
            try:
                if ctx.author.id not in self.active_games:
                    await ctx.send("❌ You don't have an active Minesweeper game!")
                    return

                game = self.active_games[ctx.author.id]
                if not game.is_active:
                    del self.active_games[ctx.author.id]
                    await ctx.send("❌ Your game is no longer active.")
                    return

                stats = game.get_game_stats()
                if "error" in stats:
                    await ctx.send("❌ Error retrieving game statistics.")
                    return

                embed = discord.Embed(title="📊 Minesweeper Statistics", color=0x00ff00)

                embed.add_field(
                    name="🎮 Game Info",
                    value=f"**Difficulty:** {game.difficulty.title()}\n**Board Size:** {stats['board_size']}\n**Total Mines:** {stats['mines_total']}",
                    inline=True
                )

                embed.add_field(
                    name="⏱️ Progress",
                    value=f"**Time Elapsed:** {stats['time_elapsed']}s\n**Cells Revealed:** {len(game.revealed)}\n**Safe Cells Left:** {stats['cells_remaining']}",
                    inline=True
                )

                embed.add_field(
                    name="🚩 Flags",
                    value=f"**Flags Remaining:** {stats['flags_remaining']}\n**Flags Placed:** {stats['mines_total'] - stats['flags_remaining']}\n**Question Marks:** {len(game.questioned)}",
                    inline=True
                )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error showing game stats: {e}")
                await ctx.send("❌ Error retrieving game statistics.")

        @commands.command(aliases=["mines-help", "minesweeper-help"])
        async def mines_help(self, ctx):
            """Get help with Classic Minesweeper"""
            try:
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
                    value="**⬅️➡️⬆️⬇️** Move cursor\n**💥** Reveal selected cell\n**🚩** Cycle: Flag → Question → Hidden\n**❌** Quit game",
                    inline=True
                )

                embed.add_field(
                    name="🗺️ Reading the Board",
                    value="**🟨** Your cursor position\n**⬛** Hidden cell\n**🚩** Flagged (suspected mine)\n**❓** Question mark (uncertain)\n**1️⃣-8️⃣** Number of adjacent mines\n**💣** Mine (game over!)",
                    inline=True
                )

                embed.add_field(
                    name="🧠 Strategy Tips",
                    value="• **Start with corners and edges** - fewer adjacent cells\n• **Look for patterns** - numbers tell you exactly how many mines are nearby\n• **Use flags wisely** - mark certain mines to avoid accidents\n• **Question marks** - use for uncertain cells\n• **First click is always safe** - the game ensures this",
                    inline=False
                )

                embed.add_field(
                    name="🏆 Difficulty Levels",
                    value="**Beginner:** 9×9, 10 mines (good for learning)\n**Intermediate:** 16×16, 40 mines (moderate challenge)\n**Expert:** 30×16, 99 mines (for experienced players)\n**Custom:** Design your own board",
                    inline=False
                )

                embed.add_field(
                    name="📚 Commands",
                    value=f"`{ctx.prefix}minesweeper` - Start new game\n`{ctx.prefix}mines-continue` - Resume current game\n`{ctx.prefix}mines-stats` - View game statistics\n`{ctx.prefix}mines-quit` - End current game",
                    inline=False
                )

                embed.set_footer(text="💡 Pro tip: The numbers are your best friend - they never lie!")
                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error showing help: {e}")
                await ctx.send("❌ Error loading help information.")

        async def _show_custom_help(self, ctx):
            """Show custom help with error handling"""
            try:
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
                    value=f"`{ctx.prefix}minesweeper custom 12 12 20`\n`{ctx.prefix}minesweeper custom 20 10 35`\n`{ctx.prefix}minesweeper custom 8 8 12`",
                    inline=True
                )

                embed.add_field(
                    name="⚖️ Balance Tips",
                    value="• **10-15%** mine density = Easy\n• **15-20%** mine density = Medium\n• **20%+** mine density = Hard\n• Leave at least 9 safe cells for solvability",
                    inline=False
                )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error showing custom help: {e}")
                await ctx.send("❌ Error loading custom game help.")

        async def _show_invalid_difficulty(self, ctx):
            """Show invalid difficulty error with error handling"""
            try:
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
                    value=f"`{ctx.prefix}minesweeper` - See all options\n`{ctx.prefix}minesweeper beginner` - Start easy game",
                    inline=False
                )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error showing invalid difficulty: {e}")
                await ctx.send("❌ Invalid difficulty. Try: `l.minesweeper beginner`")

        # Legacy text commands for backward compatibility
        @commands.command()
        async def minreveal(self, ctx, x: int = None, y: int = None):
            """Reveal a cell using coordinates with error handling"""
            try:
                if ctx.author.id not in self.active_games:
                    await ctx.send("❌ You don't have an active Minesweeper game! Use `l.minesweeper` to start one.")
                    return

                if x is None or y is None:
                    await ctx.send(f"❌ Please specify coordinates! Usage: `{ctx.prefix}minreveal <x> <y>`")
                    return

                game = self.active_games[ctx.author.id]
                if not game.is_active or game.game_over:
                    await ctx.send("❌ Game is not active! Use `l.minesweeper` to start a new game.")
                    return

                # Convert to 0-based coordinates
                x -= 1
                y -= 1

                if not (0 <= x < game.width and 0 <= y < game.height):
                    await ctx.send(f"❌ Invalid coordinates! Use 1-{game.width} for x and 1-{game.height} for y.")
                    return

                # Reveal the cell
                continue_game = game.reveal_cell(x, y)

                if game.won or not continue_game:
                    await self._end_game_display(game)
                else:
                    await self._update_game_display(game)
                    await ctx.send("✅ Cell revealed! Check the game board above.", delete_after=3)

            except Exception as e:
                logger.error(f"Error in minreveal: {e}")
                await ctx.send("❌ Error revealing cell.")

        @commands.command()
        async def minflag(self, ctx, x: int = None, y: int = None):
            """Toggle a flag using coordinates with error handling"""
            try:
                if ctx.author.id not in self.active_games:
                    await ctx.send("❌ You don't have an active Minesweeper game!")
                    return

                if x is None or y is None:
                    await ctx.send(f"❌ Please specify coordinates! Usage: `{ctx.prefix}minflag <x> <y>`")
                    return

                game = self.active_games[ctx.author.id]
                if not game.is_active or game.game_over:
                    await ctx.send("❌ Game is not active!")
                    return

                x -= 1
                y -= 1

                if not (0 <= x < game.width and 0 <= y < game.height):
                    await ctx.send(f"❌ Invalid coordinates! Use 1-{game.width} for x and 1-{game.height} for y.")
                    return

                game.toggle_flag(x, y)
                await self._update_game_display(game)

                if (x, y) in game.flagged:
                    action = "Flag placed"
                elif (x, y) in game.questioned:
                    action = "Question mark placed"
                else:
                    action = "Mark removed"

                await ctx.send(f"🚩 {action}! Check the game board above.", delete_after=3)

            except Exception as e:
                logger.error(f"Error in minflag: {e}")
                await ctx.send("❌ Error toggling flag.")

        @commands.command()
        async def mingame(self, ctx):
            """Show current game with error handling"""
            try:
                if ctx.author.id not in self.active_games:
                    await ctx.send("❌ You don't have an active Minesweeper game!")
                    return

                game = self.active_games[ctx.author.id]
                if not game.is_active:
                    del self.active_games[ctx.author.id]
                    await ctx.send("❌ Your game is no longer active.")
                    return

                await self._update_game_display(game)
                await ctx.send("🔄 Game board refreshed! Use reactions to play.", delete_after=3)

            except Exception as e:
                logger.error(f"Error in mingame: {e}")
                await ctx.send("❌ Error displaying game.")

        # Cleanup command for emergencies
        @commands.command(aliases=["mines-cleanup", "mines-reset"])
        @commands.cooldown(1, 60, commands.BucketType.user)
        async def mines_emergency_cleanup(self, ctx):
            """Emergency cleanup for stuck games"""
            try:
                if ctx.author.id in self.active_games:
                    game = self.active_games[ctx.author.id]
                    game.cleanup()
                    del self.active_games[ctx.author.id]
                    await ctx.send("🧹 Emergency cleanup completed! You can start a new game now.")
                else:
                    await ctx.send("❌ No active game found to clean up.")

            except Exception as e:
                logger.error(f"Error in emergency cleanup: {e}")
                # Force cleanup
                try:
                    if ctx.author.id in self.active_games:
                        del self.active_games[ctx.author.id]
                    await ctx.send("🧹 Force cleanup completed!")
                except:
                    await ctx.send("❌ Cleanup failed. Contact an admin if issues persist.")

async def setup(bot):
    await bot.add_cog(ClassicGames(bot))