import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения."""
    
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    
    # Google Sheets
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    SHEET_NAME = os.getenv("SHEET_NAME", "Feedback")
    
    # Настройки
    MAX_FEEDBACK_LENGTH = 10000
    FEEDBACK_COOLDOWN = 30  # сек


config = Config()