"""
Mini-games and interactive entertainment
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import discord
from discord.ext import commands
import random
import asyncio
from typing import Dict, Tuple, Set
from utils.decorators import guild_setting_enabled


class MinesweeperGame:
    """Interactive minesweeper game state"""

    def __init__(self, width: int, height: int, mines: int, player_id: int):
        self.width = width
        self.height = height
        self.mines = mines
        self.player_id = player_id
        self.board = self._generate_board()
        self.revealed: Set[Tuple[int, int]] = set()
        self.flagged: Set[Tuple[int, int]] = set()
        self.game_over = False
        self.won = False
        self.message = None
        self.current_selection = (0, 0)  # Current selected cell

    def _generate_board(self):
        """Generate the internal game board"""
        board = [[0 for _ in range(self.width)] for _ in range(self.height)]

        # Place mines randomly
        mine_positions = set()
        while len(mine_positions) < self.mines:
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            mine_positions.add((x, y))

        # Set mines on board
        for x, y in mine_positions:
            board[y][x] = -1

        # Calculate numbers for non-mine cells
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

        return board

    def reveal(self, x: int, y: int) -> bool:
        """Reveal a cell. Returns True if game continues, False if game over"""
        if (x, y) in self.revealed or (x, y) in self.flagged:
            return True

        self.revealed.add((x, y))

        # Check if hit a mine
        if self.board[y][x] == -1:
            self.game_over = True
            return False

        # Auto-reveal empty areas (flood fill for 0s)
        if self.board[y][x] == 0:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if (nx, ny) not in self.revealed:
                            self.reveal(nx, ny)

        # Check win condition
        safe_cells = self.width * self.height - self.mines
        if len(self.revealed) >= safe_cells:
            self.won = True
            self.game_over = True

        return True

    def toggle_flag(self, x: int, y: int):
        """Toggle flag on a cell"""
        if (x, y) in self.revealed:
            return

        if (x, y) in self.flagged:
            self.flagged.remove((x, y))
        else:
            self.flagged.add((x, y))

    def get_display_board(self) -> str:
        """Get clean board display with cursor"""
        emoji_map = {
            -1: "💣", 0: "⬜", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣",
            5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣"
        }

        result = ""
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) == self.current_selection and (x, y) not in self.revealed:
                    # Show cursor on selected cell
                    if (x, y) in self.flagged:
                        result += "🚩"  # Selected flagged cell
                    else:
                        result += "🟨"  # Selected hidden cell
                elif (x, y) in self.flagged:
                    result += "🚩"
                elif (x, y) in self.revealed:
                    result += emoji_map[self.board[y][x]]
                else:
                    result += "⬛"
            result += "\n"

        return result


class Games(commands.Cog):
    """Mini-games and interactive entertainment"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, MinesweeperGame] = {}

    @commands.command(aliases=["mines", "ms"])
    @guild_setting_enabled("minesweeper")
    async def minesweeper(self, ctx, difficulty: str = None):
        """Start an interactive minesweeper game

        Usage: l.minesweeper [difficulty]
        Difficulties: beginner, easy, medium, hard, expert
        """

        difficulties = {
            "beginner": (6, 6, 6),
            "easy": (8, 8, 10),
            "medium": (10, 10, 18),
            "hard": (12, 12, 25),
            "expert": (14, 14, 35)
        }

        # If no difficulty specified, show the menu
        if difficulty is None:
            embed = discord.Embed(
                title="💣 Minesweeper - Choose Difficulty",
                description="Select a difficulty level to start playing!",
                color=0x00ff00
            )

            for diff, (w, h, m) in difficulties.items():
                ratio = m / (w * h)
                if diff == "beginner":
                    emoji = "🟢"
                    desc = "Perfect for learning!"
                elif diff == "easy":
                    emoji = "🔵"
                    desc = "Nice and relaxed"
                elif diff == "medium":
                    emoji = "🟡"
                    desc = "Good challenge"
                elif diff == "hard":
                    emoji = "🟠"
                    desc = "Getting serious!"
                else:  # expert
                    emoji = "🔴"
                    desc = "For pros only!"

                embed.add_field(
                    name=f"{emoji} {diff.title()} - {w}×{h}",
                    value=f"💣 {m} mines ({ratio:.1%})\n*{desc}*",
                    inline=True
                )

            embed.add_field(
                name="🎮 How to Start",
                value=f"Use: `{self.bot.command_prefix}minesweeper <difficulty>`\n\nExamples:\n`{self.bot.command_prefix}minesweeper beginner`\n`{self.bot.command_prefix}minesweeper expert`",
                inline=False
            )

            embed.set_footer(text="💡 Tip: Start with 'beginner' if you're new to minesweeper!")
            await ctx.send(embed=embed)
            return

        # Check if difficulty is valid
        if difficulty.lower() not in difficulties:
            embed = discord.Embed(
                title="❌ Invalid Difficulty",
                description=f"'{difficulty}' is not a valid difficulty.\n\nUse `{self.bot.command_prefix}minesweeper` to see all options.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        # Check if player already has a game
        if ctx.author.id in self.active_games:
            embed = discord.Embed(
                title="⚠️ Game Already Active",
                description="You already have an active minesweeper game!",
                color=0xffaa00
            )
            embed.add_field(
                name="Options",
                value=f"`{self.bot.command_prefix}mingame` - Continue current game\n`{self.bot.command_prefix}minquit` - Quit current game\n\nThen start a new one!",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        width, height, mines = difficulties[difficulty.lower()]

        # Create new game
        game = MinesweeperGame(width, height, mines, ctx.author.id)
        self.active_games[ctx.author.id] = game

        # Determine difficulty emoji
        diff_emojis = {
            "beginner": "🟢", "easy": "🔵", "medium": "🟡",
            "hard": "🟠", "expert": "🔴"
        }

        embed = discord.Embed(
            title=f"💣 Minesweeper - {diff_emojis[difficulty.lower()]} {difficulty.title()} Started!",
            description=game.get_display_board(),
            color=0x00ff00
        )

        embed.add_field(
            name="📊 Game Info",
            value=f"Size: {width}×{height}\nMines: {mines}\nDifficulty: {difficulty.title()}",
            inline=True
        )

        embed.add_field(
            name="🎮 Controls",
            value="⬅️➡️⬆️⬇️ Move cursor\n💥 Reveal selected cell\n🚩 Flag selected cell\n❌ Quit game",
            inline=True
        )

        embed.add_field(
            name="🗺️ Legend",
            value="🟨 Selected cell\n⬛ Hidden cell\n🚩 Flagged cell\n⬜ Empty cell\n1️⃣-8️⃣ Numbers",
            inline=False
        )

        embed.set_footer(text=f"Good luck, {ctx.author.display_name}! Use arrow reactions to move and 💥 to reveal!")

        # Send the message
        message = await ctx.send(embed=embed)
        game.message = message

        # Add simple navigation reactions (REMOVED 🔄)
        reactions = ["⬅️", "➡️", "⬆️", "⬇️", "💥", "🚩", "❌"]
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Start listening for reactions
        self.bot.loop.create_task(self._handle_reactions(ctx, game))

    async def _handle_reactions(self, ctx, game):
        """Handle reaction-based gameplay"""

        def check(reaction, user):
            return (
                    user.id == game.player_id and
                    reaction.message.id == game.message.id and
                    not user.bot
            )

        while not game.game_over:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
                emoji = str(reaction.emoji)

                # Remove user's reaction
                try:
                    await reaction.remove(user)
                except:
                    pass

                if emoji == "❌":  # Quit game
                    del self.active_games[user.id]
                    embed = discord.Embed(
                        description="✅ Minesweeper game ended. Thanks for playing!",
                        color=0x00ff00
                    )
                    await game.message.edit(embed=embed)
                    await game.message.clear_reactions()
                    return

                # REMOVED: elif emoji == "🔄": refresh functionality

                elif emoji == "⬅️":  # Move left
                    game.current_selection = (max(0, game.current_selection[0] - 1), game.current_selection[1])
                    await self._update_game_display(game)

                elif emoji == "➡️":  # Move right
                    game.current_selection = (min(game.width - 1, game.current_selection[0] + 1),
                                              game.current_selection[1])
                    await self._update_game_display(game)

                elif emoji == "⬆️":  # Move up
                    game.current_selection = (game.current_selection[0], max(0, game.current_selection[1] - 1))
                    await self._update_game_display(game)

                elif emoji == "⬇️":  # Move down
                    game.current_selection = (game.current_selection[0],
                                              min(game.height - 1, game.current_selection[1] + 1))
                    await self._update_game_display(game)

                elif emoji == "💥":  # Reveal selected cell
                    x, y = game.current_selection
                    continue_game = game.reveal(x, y)

                    if game.won or not continue_game:
                        await self._handle_game_end(game)
                        return
                    else:
                        await self._update_game_display(game)

                elif emoji == "🚩":  # Flag selected cell
                    x, y = game.current_selection
                    game.toggle_flag(x, y)
                    await self._update_game_display(game)

            except asyncio.TimeoutError:
                # Game timed out
                embed = discord.Embed(
                    description="⏰ Minesweeper game timed out due to inactivity.",
                    color=0xffaa00
                )
                await game.message.edit(embed=embed)
                await game.message.clear_reactions()
                if game.player_id in self.active_games:
                    del self.active_games[game.player_id]
                return

    async def _update_game_display(self, game):
        """Update the game display with new board state"""
        embed = discord.Embed(
            title="💣 Minesweeper",
            description=game.get_display_board(),
            color=0x00ff00
        )

        safe_remaining = (game.width * game.height - game.mines) - len(game.revealed)
        embed.add_field(
            name="📊 Progress",
            value=f"Safe cells remaining: {safe_remaining}\nFlags placed: {len(game.flagged)}\nSelected: ({game.current_selection[0] + 1}, {game.current_selection[1] + 1})",
            inline=True
        )

        embed.add_field(
            name="🎮 Controls",
            value="⬅️➡️⬆️⬇️ Move\n💥 Reveal\n🚩 Flag\n❌ Quit",  # REMOVED: 🔄 Refresh
            inline=True
        )

        # Update message
        await game.message.edit(embed=embed)

    async def _handle_game_end(self, game):
        """Handle game win/loss"""
        if game.won:
            embed = discord.Embed(
                title="🎉 Congratulations! You Won!",
                description=game.get_display_board(),
                color=0x00ff00
            )
            embed.add_field(
                name="🏆 Victory!",
                value=f"You successfully avoided all {game.mines} mines!\nCells revealed: {len(game.revealed)}",
                inline=False
            )
        else:
            # Reveal all mines for game over
            for y in range(game.height):
                for x in range(game.width):
                    if game.board[y][x] == -1:
                        game.revealed.add((x, y))

            embed = discord.Embed(
                title="💥 GAME OVER!",
                description=game.get_display_board(),
                color=0xff0000
            )
            embed.add_field(
                name="💣 You hit a mine!",
                value=f"Better luck next time!\nCells revealed: {len(game.revealed) - game.mines}/{game.width * game.height - game.mines}",
                inline=False
            )

        embed.add_field(
            name="🔄 Play Again?",
            value=f"Use `l.minesweeper` to start a new game!",
            inline=False
        )

        await game.message.edit(embed=embed)
        await game.message.clear_reactions()

        if game.player_id in self.active_games:
            del self.active_games[game.player_id]

    # Keep existing text commands for backup
    @commands.command()
    async def minreveal(self, ctx, x: int = None, y: int = None):
        """Reveal a cell in your minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active minesweeper game! Use `l.minesweeper` to start one.")
            return

        if x is None or y is None:
            await ctx.send(f"❌ Please specify coordinates! Usage: `{self.bot.command_prefix}minreveal <x> <y>`")
            return

        game = self.active_games[ctx.author.id]

        # Convert to 0-based coordinates
        x -= 1
        y -= 1

        if not (0 <= x < game.width and 0 <= y < game.height):
            await ctx.send(f"❌ Invalid coordinates! Use 1-{game.width} for x and 1-{game.height} for y.")
            return

        if game.game_over:
            await ctx.send("❌ Game is already over! Use `l.minesweeper` to start a new game.")
            return

        # Reveal the cell
        continue_game = game.reveal(x, y)

        if game.won or not continue_game:
            await self._handle_game_end(game)
        else:
            await self._update_game_display(game)
            await ctx.send("✅ Cell revealed! Check the game board above.", delete_after=3)

    @commands.command()
    async def minflag(self, ctx, x: int = None, y: int = None):
        """Toggle a flag on a cell"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active minesweeper game!")
            return

        if x is None or y is None:
            await ctx.send(f"❌ Please specify coordinates! Usage: `{self.bot.command_prefix}minflag <x> <y>`")
            return

        game = self.active_games[ctx.author.id]
        x -= 1
        y -= 1

        if not (0 <= x < game.width and 0 <= y < game.height):
            await ctx.send(f"❌ Invalid coordinates! Use 1-{game.width} for x and 1-{game.height} for y.")
            return

        if game.game_over:
            await ctx.send("❌ Game is already over!")
            return

        game.toggle_flag(x, y)
        await self._update_game_display(game)

        action = "placed" if (x, y) in game.flagged else "removed"
        await ctx.send(f"🚩 Flag {action}! Check the game board above.", delete_after=3)

    @commands.command()
    async def mingame(self, ctx):
        """Show your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active minesweeper game!")
            return

        game = self.active_games[ctx.author.id]
        await self._update_game_display(game)
        await ctx.send("🔄 Game board refreshed! Use reactions to play.", delete_after=3)

    @commands.command()
    async def minquit(self, ctx):
        """Quit your current minesweeper game"""
        if ctx.author.id not in self.active_games:
            await ctx.send("❌ You don't have an active minesweeper game!")
            return

        game = self.active_games[ctx.author.id]
        if game.message:
            await game.message.clear_reactions()

        del self.active_games[ctx.author.id]
        embed = discord.Embed(
            description="✅ Minesweeper game ended. Thanks for playing!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["minhelp"])
    async def minehelp(self, ctx):
        """Get help with minesweeper commands"""
        embed = discord.Embed(
            title="💣 Minesweeper Help",
            description="Complete guide to playing minesweeper!",
            color=0x00ff00
        )

        embed.add_field(
            name="🎮 Reaction Controls",
            value="⬅️➡️⬆️⬇️ Move cursor around\n💥 Reveal selected cell\n🚩 Flag/unflag selected cell\n❌ Quit game",
            inline=False
        )

        embed.add_field(
            name="🗺️ Reading the Board",
            value="🟨 Your current selection\n⬛ Hidden cell\n🚩 Flagged cell (suspected mine)\n⬜ Empty safe cell\n1️⃣-8️⃣ Number of adjacent mines\n💣 Mine (game over!)",
            inline=True
        )

        embed.add_field(
            name="🏆 How to Win",
            value="Reveal all safe cells without hitting any mines! Use the numbers to figure out where mines are.",
            inline=False
        )

        embed.add_field(
            name="💡 Pro Tips",
            value="• Move with arrow reactions, reveal with 💥\n• Flag suspected mines to avoid accidentally revealing them\n• Numbers tell you how many mines are adjacent\n• Start with corners and edges - they're usually safer",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["rps"])
    @guild_setting_enabled("games")
    async def rockpaperscissors(self, ctx, choice: str = None):
        """Play rock, paper, scissors"""
        if not choice:
            embed = discord.Embed(
                title="✂️ Rock Paper Scissors",
                description=f"Choose your weapon!\n\nUsage: `{self.bot.command_prefix}rps <rock/paper/scissors>`",
                color=0x00ff00
            )
            embed.add_field(name="Options", value="🪨 rock\n📄 paper\n✂️ scissors", inline=False)
            await ctx.send(embed=embed)
            return

        choice = choice.lower()
        if choice not in ["rock", "paper", "scissors"]:
            await ctx.send("❌ Invalid choice! Use rock, paper, or scissors.")
            return

        bot_choice = random.choice(["rock", "paper", "scissors"])

        if choice == bot_choice:
            result = "It's a tie!"
            color = 0xFFD700
            emoji = "🤝"
        elif (choice == "rock" and bot_choice == "scissors") or \
                (choice == "paper" and bot_choice == "rock") or \
                (choice == "scissors" and bot_choice == "paper"):
            result = "You win!"
            color = 0x00ff00
            emoji = "🎉"
        else:
            result = "I win!"
            color = 0xff0000
            emoji = "🤖"

        choice_emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

        embed = discord.Embed(title=f"{emoji} {result}", color=color)
        embed.add_field(name="Your Choice", value=f"{choice_emojis[choice]} {choice.title()}", inline=True)
        embed.add_field(name="My Choice", value=f"{choice_emojis[bot_choice]} {bot_choice.title()}", inline=True)

        await ctx.send(embed=embed)

    @commands.command()
    @guild_setting_enabled("games")
    async def coinflip(self, ctx):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙" if result == "Heads" else "🥈"

        embed = discord.Embed(
            title=f"{emoji} Coin Flip",
            description=f"**{result}!**",
            color=0xFFD700
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Games(bot))