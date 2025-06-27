"""
Enhanced cog loading system
"""

import os
import logging
import importlib
import sys
from pathlib import Path
from typing import List, Set
from discord.ext import commands

logger = logging.getLogger(__name__)


class CogLoader:
    """Manages loading and reloading of cogs"""

    def __init__(self, bot: commands.Bot, cogs_to_load: str = "all"):
        self.bot = bot
        self.cogs_to_load_arg = cogs_to_load
        self.loaded_cogs: Set[str] = set()

    def get_cog_list(self) -> List[str]:
        """Get list of cogs to load based on argument"""
        all_cogs = self._discover_cogs()

        if self.cogs_to_load_arg == "all":
            return all_cogs

        # Parse cog arguments (e.g., "admin,utility,!entertainment")
        include_cogs = []
        exclude_cogs = []

        for cog in self.cogs_to_load_arg.split(","):
            cog = cog.strip()
            if cog.startswith("!"):
                exclude_cogs.append(cog[1:])
            else:
                include_cogs.append(cog)

        if include_cogs:
            # Include specific cogs/categories
            result_cogs = []
            for include in include_cogs:
                result_cogs.extend([cog for cog in all_cogs if include in cog])
        else:
            # Start with all cogs
            result_cogs = all_cogs.copy()

        # Exclude specified cogs/categories
        for exclude in exclude_cogs:
            result_cogs = [cog for cog in result_cogs if exclude not in cog]

        return result_cogs

    def _discover_cogs(self) -> List[str]:
        """Discover all available cogs"""
        cogs = []
        cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            # Fallback to old structure
            old_cogs_dir = Path("Cogs")
            if old_cogs_dir.exists():
                for file in old_cogs_dir.glob("*.py"):
                    if file.name != "__init__.py":
                        cogs.append(f"Cogs.{file.stem}")
                return cogs

        # New structure: discover cogs in subdirectories
        for category_dir in cogs_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("_"):
                for file in category_dir.glob("*.py"):
                    if file.name != "__init__.py":
                        cogs.append(f"cogs.{category_dir.name}.{file.stem}")

        return cogs

    async def load_cog(self, cog_name: str) -> bool:
        """Load a single cog"""
        try:
            await self.bot.load_extension(cog_name)
            self.loaded_cogs.add(cog_name)
            logger.info(f"Loaded cog: {cog_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load cog {cog_name}: {e}")
            return False

    async def unload_cog(self, cog_name: str) -> bool:
        """Unload a single cog"""
        try:
            await self.bot.unload_extension(cog_name)
            self.loaded_cogs.discard(cog_name)
            logger.info(f"Unloaded cog: {cog_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload cog {cog_name}: {e}")
            return False

    async def reload_cog(self, cog_name: str) -> bool:
        """Reload a single cog with proper module invalidation"""
        try:
            # Step 1: Unload the extension first
            if cog_name in self.bot.extensions:
                await self.bot.unload_extension(cog_name)

            # Step 2: Force reload the Python module
            module_name = cog_name
            if module_name in sys.modules:
                # Get the module
                module = sys.modules[module_name]

                # Reload the module to pick up file changes
                importlib.reload(module)
                logger.info(f"Reloaded Python module: {module_name}")

            # Step 3: Load the extension again
            await self.bot.load_extension(cog_name)

            # Ensure it's in our loaded set
            self.loaded_cogs.add(cog_name)

            logger.info(f"Successfully reloaded cog: {cog_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to reload cog {cog_name}: {e}")

            # Try to reload it anyway to prevent broken state
            try:
                await self.bot.load_extension(cog_name)
                self.loaded_cogs.add(cog_name)
                logger.info(f"Recovered cog after failed reload: {cog_name}")
                return False  # Still return False since the reload failed
            except:
                logger.error(f"Could not recover cog {cog_name}")
                return False

    async def load_all_cogs(self) -> None:
        """Load all specified cogs"""
        cogs_to_load = self.get_cog_list()
        loaded_count = 0
        failed_count = 0

        for cog_name in cogs_to_load:
            success = await self.load_cog(cog_name)
            if success:
                loaded_count += 1
            else:
                failed_count += 1

        logger.info(f"Cog loading complete: {loaded_count} loaded, {failed_count} failed")

    async def reload_all_cogs(self) -> None:
        """Reload all currently loaded cogs with proper module invalidation"""
        cogs_to_reload = list(self.loaded_cogs)
        reloaded_count = 0
        failed_count = 0

        # Clear Python module cache for cog modules
        cog_modules = [name for name in sys.modules.keys() if name.startswith('cogs.')]

        logger.info(f"Clearing {len(cog_modules)} cog modules from cache...")
        for module_name in cog_modules:
            if module_name in sys.modules:
                try:
                    importlib.reload(sys.modules[module_name])
                except Exception as e:
                    logger.warning(f"Could not reload module {module_name}: {e}")

        # Now reload each cog
        for cog_name in cogs_to_reload:
            success = await self.reload_cog(cog_name)
            if success:
                reloaded_count += 1
            else:
                failed_count += 1

        logger.info(f"Cog reloading complete: {reloaded_count} reloaded, {failed_count} failed")