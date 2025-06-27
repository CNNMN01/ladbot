"""
Bot Configuration Settings - Environment Variables
"""
import os
from pathlib import Path
from typing import List

class Settings:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self.BOT_PREFIX = os.getenv("BOT_PREFIX", "l.")
        self.ADMIN_IDS = []
        admin_str = os.getenv("ADMIN_IDS", "")
        if admin_str:
            try:
                self.ADMIN_IDS = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
            except ValueError:
                pass
        
        self.admin_ids = self.ADMIN_IDS
        self.prefix = self.BOT_PREFIX
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent
        self.LOGS_DIR = self.PROJECT_ROOT / "logs" 
        self.DATA_DIR = self.PROJECT_ROOT / "data"
        
        self.validate()
    
    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)

settings = Settings()
