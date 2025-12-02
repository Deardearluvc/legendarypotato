"""
Configuration module for Dear X Proxy Bot
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Bot configuration"""
    
    # Telegram Bot Settings
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'Dearproxybot')
    
    # Links
    CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/Dear_WhyMe')
    SUPPORT_URL = os.getenv('SUPPORT_URL', 'https://t.me/DearMe_Chat')
    BOT_LINK = f"https://t.me/{BOT_USERNAME}"
    
    # Directories
    BASE_DIR = Path(__file__).parent
    TEMP_DIR = Path(os.getenv('TEMP_DIR', './temp'))
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', './output'))
    ASSETS_DIR = Path(os.getenv('ASSETS_DIR', './assets'))
    
    # Create directories if they don't exist
    TEMP_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    
    # Proxy Settings
    MAX_CONCURRENT = int(os.getenv('MAX_CONCURRENT', 500))  # Increased from 200
    DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', 5))  # Reduced from 15
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 500))  # Increased from 100
    
    # Fast Mode (for speed optimization)
    FAST_MODE = True  # Only check HTTP by default (99% accurate, 50% faster)
    
    # Progress Settings
    PROGRESS_UPDATE_INTERVAL = int(os.getenv('PROGRESS_UPDATE_INTERVAL', 3))
    
    # File Settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['.txt', '.csv']
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
    
    # Start Video
    START_VIDEO_PATH = ASSETS_DIR / 'start_video.mp4'
    START_VIDEO_URL = None  # Set this to a direct video URL if not using local file
    
    # Sticker Paths for Premium Feel
    STICKER_PATHS = {
        'web': ASSETS_DIR / 'web.webm',
        'scrape': ASSETS_DIR / 'sc.webp',
        'check': ASSETS_DIR / 'chk.webp',
        'auto': ASSETS_DIR / 'auto.webm',
        'help': ASSETS_DIR / 'help.webm',
        'stats': ASSETS_DIR / 'stat.webp',
        'export': ASSETS_DIR / 'exp.webp',
        'cancel': ASSETS_DIR / 'cnn.webp',
        'export_http': ASSETS_DIR / 'http.webp',
        'export_https': ASSETS_DIR / 'https.webp',
        'export_socks4': ASSETS_DIR / 'socks.webp',
        'export_socks5': ASSETS_DIR / 'socks2.webp',
        'export_elite': ASSETS_DIR / 'elite.webp',
        'export_anonymous': ASSETS_DIR / 'spy.webm',
        'export_transparent': ASSETS_DIR / '2.webp',
        'export_all': ASSETS_DIR / '7.webp'
    }
    
    # Permanent Storage
    PERMANENT_SOURCES_FILE = BASE_DIR / 'user_sources.json'
    
    # Test URLs for proxy checking
    TEST_URLS = {
        'http': 'http://httpbin.org/ip',
        'https': 'https://httpbin.org/ip',
        'socks4': 'http://httpbin.org/ip',
        'socks5': 'http://httpbin.org/ip',
    }
    
    # Proxy Categories
    PROXY_CATEGORIES = [
        'http', 'https', 'socks4', 'socks5',
        'elite', 'anonymous', 'transparent', 'all_working'
    ]
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in environment variables!")
        return True

# Emoji Constants
class Emoji:
    """Emoji constants for better readability"""
    ROBOT = "🤖"
    GLOBE = "🌐"
    SEARCH = "🔍"
    CHECK = "✅"
    CROSS = "❌"
    FIRE = "🔥"
    ROCKET = "🚀"
    CHART = "📊"
    FILE = "📁"
    DOWNLOAD = "⬇️"
    UPLOAD = "⬆️"
    CLOCK = "⏱️"
    LIGHTNING = "⚡"
    PACKAGE = "📦"
    BOOK = "📚"
    MEGAPHONE = "📢"
    CHAT = "💬"
    WRENCH = "🔧"
    GEAR = "⚙️"
    PROGRESS = "━"
    HOURGLASS = "⏳"
    SPARKLES = "✨"
    WARNING = "⚠️"
    INFO = "ℹ️"
    ARROW_RIGHT = "➻"
    BULLET = "๏"

# Validate config on import
Config.validate()
