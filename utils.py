"""
Utility Functions for Proxy Bot
"""
import asyncio
import time
from typing import Callable, Any
from pathlib import Path
import logging

from config import Config, Emoji

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Track and format progress for Telegram messages"""
    
    def __init__(self, message, total: int):
        self.message = message
        self.total = total
        self.last_update = 0
        self.update_interval = Config.PROGRESS_UPDATE_INTERVAL
    
    def should_update(self) -> bool:
        """Check if enough time has passed for an update"""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            return True
        return False
    
    @staticmethod
    def create_progress_bar(percentage: float, length: int = 10) -> str:
        """Create a visual progress bar"""
        filled = int(percentage / 100 * length)
        bar = Emoji.PROGRESS * filled + "░" * (length - filled)
        return bar
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds into readable time"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def format_number(num: int) -> str:
        """Format number with thousand separators"""
        return f"{num:,}"

class AsyncQueue:
    """Async task queue for managing operations"""
    
    def __init__(self, max_concurrent: int = 5):
        self.queue = asyncio.Queue()
        self.max_concurrent = max_concurrent
        self.active_tasks = 0
    
    async def add_task(self, coro):
        """Add a task to the queue"""
        await self.queue.put(coro)
    
    async def process_queue(self):
        """Process all tasks in the queue"""
        while not self.queue.empty():
            if self.active_tasks < self.max_concurrent:
                coro = await self.queue.get()
                self.active_tasks += 1
                
                asyncio.create_task(self._execute_task(coro))
    
    async def _execute_task(self, coro):
        """Execute a single task"""
        try:
            await coro
        except Exception as e:
            logger.error(f"Task error: {e}")
        finally:
            self.active_tasks -= 1
            self.queue.task_done()

def validate_proxy_format(proxy: str) -> bool:
    """Validate basic proxy format"""
    import re
    
    # Pattern for IP:PORT or protocol://IP:PORT
    patterns = [
        r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}$',  # IP:PORT
        r'^(https?|socks[45])://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}$'  # protocol://IP:PORT
    ]
    
    return any(re.match(pattern, proxy.strip()) for pattern in patterns)

def parse_amount_input(text: str) -> int:
    """Parse user input for proxy amount"""
    text = text.strip().lower()
    
    # Handle special cases
    if text in ['all', 'unlimited', 'max']:
        return None  # No limit
    
    # Remove common text
    text = text.replace('proxies', '').replace('proxy', '').strip()
    
    # Try to extract number
    try:
        # Handle K suffix (e.g., "5k" = 5000)
        if 'k' in text:
            number = float(text.replace('k', ''))
            return int(number * 1000)
        
        return int(text)
    except ValueError:
        return None

def estimate_time(count: int, speed: float) -> str:
    """Estimate remaining time based on current speed"""
    if speed <= 0:
        return "calculating..."
    
    remaining_seconds = count / speed
    return ProgressTracker.format_time(remaining_seconds)

def create_stats_message(results: dict) -> str:
    """Create detailed statistics message"""
    total = len(results.get('all_working', []))
    
    if total == 0:
        return f"{Emoji.WARNING} No working proxies found."
    
    # Calculate percentages
    http_pct = len(results.get('http', [])) / total * 100 if total > 0 else 0
    https_pct = len(results.get('https', [])) / total * 100 if total > 0 else 0
    elite_pct = len(results.get('elite', [])) / total * 100 if total > 0 else 0
    
    lines = [
        f"{Emoji.CHART} <b>DETAILED STATISTICS</b>",
        "",
        f"<b>Total Working:</b> {total:,}",
        "",
        f"<b>Protocol Distribution:</b>",
        f"├ HTTP: {len(results.get('http', []))} ({http_pct:.1f}%)",
        f"├ HTTPS: {len(results.get('https', []))} ({https_pct:.1f}%)",
        f"├ SOCKS4: {len(results.get('socks4', []))}",
        f"└ SOCKS5: {len(results.get('socks5', []))}",
        "",
        f"<b>Quality Distribution:</b>",
        f"├ {Emoji.SPARKLES} Elite: {len(results.get('elite', []))} ({elite_pct:.1f}%)",
        f"├ Anonymous: {len(results.get('anonymous', []))}",
        f"└ Transparent: {len(results.get('transparent', []))}"
    ]
    
    # Add speed stats if available
    all_working = results.get('all_working', [])
    if all_working:
        speeds = [p.get('response_time', 999) for p in all_working]
        avg_speed = sum(speeds) / len(speeds)
        fastest = min(speeds)
        
        lines.extend([
            "",
            f"<b>Speed Statistics:</b>",
            f"├ Fastest: {fastest:.3f}s",
            f"└ Average: {avg_speed:.3f}s"
        ])
    
    return "\n".join(lines)

async def send_long_message(message, text: str, parse_mode: str = 'HTML', **kwargs):
    """Send long messages by splitting if necessary"""
    max_length = 4096
    
    if len(text) <= max_length:
        return await message.reply_text(text, parse_mode=parse_mode, **kwargs)
    
    # Split by lines to avoid breaking formatting
    lines = text.split('\n')
    current_chunk = []
    current_length = 0
    
    messages = []
    
    for line in lines:
        line_length = len(line) + 1  # +1 for newline
        
        if current_length + line_length > max_length:
            # Send current chunk
            chunk_text = '\n'.join(current_chunk)
            msg = await message.reply_text(chunk_text, parse_mode=parse_mode, **kwargs)
            messages.append(msg)
            
            # Start new chunk
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length
    
    # Send remaining chunk
    if current_chunk:
        chunk_text = '\n'.join(current_chunk)
        msg = await message.reply_text(chunk_text, parse_mode=parse_mode, **kwargs)
        messages.append(msg)
    
    return messages

def cleanup_temp_files(user_id: int):
    """Clean up temporary files for a user"""
    try:
        temp_files = list(Config.TEMP_DIR.glob(f"*_{user_id}_*"))
        for filepath in temp_files:
            try:
                filepath.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp file {filepath}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")

async def safe_delete_message(message, delay: float = 0):
    """Safely delete a message after optional delay"""
    try:
        if delay > 0:
            await asyncio.sleep(delay)
        await message.delete()
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        
        # Remove old calls outside time window
        self.calls = [t for t in self.calls if current_time - t < self.time_window]
        
        # Wait if we've hit the limit
        if len(self.calls) >= self.max_calls:
            wait_time = self.calls[0] + self.time_window - current_time
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.calls.append(current_time)
