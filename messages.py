"""
Message templates for Dear X Proxy Bot - Compact Premium Version
"""
from config import Config, Emoji

class Messages:
    """Compact message templates"""
    
    @staticmethod
    def start_message(user_name: str) -> str:
        """Welcome message for /start command"""
        return f"""нєу {user_name}

{Emoji.BULLET} ᴛʜɪs ɪs <a href="{Config.BOT_LINK}">˹ᴅᴇᴀʀ ꭙ ᴘʀᴏxʏ˼</a> {Emoji.GLOBE}

{Emoji.ARROW_RIGHT} ᴀ ғᴀsᴛ & ᴘᴏᴡᴇʀғᴜʟ ᴛᴇʟᴇɢʀᴀᴍ ᴛᴏᴏʟ ғᴏʀ ꜱᴄʀᴀᴘɪɴɢ, ꜰɪʟᴛᴇʀɪɴɢ ᴀɴᴅ ᴄʜᴇᴄᴋɪɴɢ ᴘʀᴏxɪᴇꜱ ғᴏʀ ꜱᴘᴇᴇᴅ, ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ & ᴘᴇʀꜰᴏʀᴍᴀɴᴄᴇ.

{Emoji.BULLET} ᴜꜱᴇ ᴍᴇ ᴛᴏ ᴛᴇꜱᴛ ʏᴏᴜʀ ʟɪꜱᴛꜱ, ꜱᴇᴘᴀʀᴀᴛᴇ ᴡᴏʀᴋɪɴɢ ᴘʀᴏxɪᴇꜱ, ᴀɴᴅ ɢᴇᴛ ᴄʟᴇᴀɴ ᴏᴜᴛᴘᴜᴛꜱ ғᴏʀ ʏᴏᴜʀ ᴘʀᴏᴊᴇᴄᴛꜱ.

{Emoji.BULLET} ᴛᴀᴘ <b>ʜᴇʟᴘ</b> ᴛᴏ ᴠɪᴇᴡ ᴍʏ ᴍᴏᴅᴜʟᴇꜱ, ᴄᴏᴍᴍᴀɴᴅꜱ & ғᴇᴀᴛᴜʀᴇꜱ."""

    @staticmethod
    def help_message() -> str:
        """Compact help and commands message"""
        return """📚 COMMANDS MENU

🌐 WEB SOURCES
/webs – Upload URLs file (.txt/.csv)
         One URL per line, supports # comments

🔍 SCRAPING
/scrape <amount> – Scrape proxies
         Quick: 100 / 500 / 1000 / 5000

✅ CHECKING
/check – Validate proxies (HTTP/HTTPS/SOCKS4/5)
         Shows anonymity + speed + success rate

🚀 AUTOMATION
/auto – Auto scrape → check → categorize → export

📊 STATS
/stats – View totals, success rates, performance

📥 EXPORT
/export – Download all checked proxies

⚙️ UTILITY
/start – Restart bot
/help – Show menu
/cancel – Cancel current task

💡 TIPS
• Use good source URLs for best results
• Run /scrape before /check
• "Elite" = best quality"""

    @staticmethod
    def webs_prompt() -> str:
        """Prompt for web sources upload"""
        return """⬆️ Upload Web Sources

Send a .txt or .csv file with one URL per line.
(# for comments)

⏳ Waiting for your file…"""

    @staticmethod
    def webs_loaded(count: int) -> str:
        """Message when web sources are loaded"""
        return f"""✅ Sources Loaded

Total: {count} URLs
Status: Ready

Next: /scrape to collect proxies"""

    @staticmethod
    def scrape_prompt() -> str:
        """Prompt for scraping"""
        return """🔍 Scraping Options

Send a number (e.g., 1000) or choose "All".

Quick picks:
• 100 – Fast
• 500 – Medium
• 1000 – Standard
• 5000 – Large
• All – Unlimited

⚠️ Larger amounts take longer."""

    @staticmethod
    def scrape_started(max_proxies: int = None) -> str:
        """Message when scraping starts"""
        limit_text = f"Limit: {max_proxies:,}" if max_proxies else "Mode: Unlimited"
        return f"""🔄 Scraping Started

{limit_text}
Status: Initializing..."""

    @staticmethod
    def scrape_progress(current: int, total: int, sources: int, speed: float) -> str:
        """Progress message during scraping"""
        percentage = (current / total * 100) if total > 0 else 0
        filled = int(percentage / 10)
        bar = '█' * filled + '░' * (10 - filled)
        
        return f"""🔍 Scraping

{bar} {percentage:.1f}%

Scraped: {current:,}
Sources: {sources}
Speed: {speed:.1f} p/s"""

    @staticmethod
    def scrape_complete(total: int, elapsed: float, filename: str) -> str:
        """Message when scraping is complete"""
        speed = total / elapsed if elapsed > 0 else 0
        # Minimal filename
        short_name = filename.split('_')[-1] if '_' in filename else filename
        
        return f"""✨ Scraping Completed

📊 Results
• Total: {total:,}
• Time: {elapsed:.2f}s
• Speed: {speed:.1f} p/s
• File: {short_name}

Next: run /check to validate your proxies."""

    @staticmethod
    def check_started(total: int) -> str:
        """Message when checking starts"""
        return f"""🔄 Checking Started

Total: {total:,} proxies
Status: Initializing..."""

    @staticmethod
    def check_progress(checked: int, total: int, working: int, speed: float) -> str:
        """Progress message during checking"""
        percentage = (checked / total * 100) if total > 0 else 0
        filled = int(percentage / 10)
        bar = '█' * filled + '░' * (10 - filled)
        success_rate = (working / checked * 100) if checked > 0 else 0
        
        return f"""✅ Checking

{bar} {percentage:.1f}%

Checked: {checked:,}/{total:,}
Working: {working:,} ({success_rate:.1f}%)
Speed: {speed:.1f} c/s"""

    @staticmethod
    def check_complete(results: dict, elapsed: float) -> str:
        """Message when checking is complete"""
        total_working = len(results.get('all_working', []))
        
        # Calculate fastest/average
        all_working = results.get('all_working', [])
        if all_working:
            times = [p.get('response_time', 0) for p in all_working]
            fastest = min(times) if times else 0
            average = sum(times) / len(times) if times else 0
        else:
            fastest = average = 0
        
        return f"""✨ Checking Completed

📊 Statistics

Working: {total_working:,}

Protocols:
• HTTP: {len(results.get('http', []))}
• HTTPS: {len(results.get('https', []))}
• SOCKS4: {len(results.get('socks4', []))}
• SOCKS5: {len(results.get('socks5', []))}

Quality:
• Elite: {len(results.get('elite', []))}
• Anonymous: {len(results.get('anonymous', []))}
• Transparent: {len(results.get('transparent', []))}

Speed:
• Fastest: {fastest:.2f}s
• Average: {average:.2f}s

ℹ️ Use Export Options to download specific types."""

    @staticmethod
    def auto_started() -> str:
        """Message when auto mode starts"""
        return """🚀 Automation Started

Running complete workflow:
1️⃣ Load sources
2️⃣ Scrape proxies
3️⃣ Validate proxies
4️⃣ Export results

⏳ Please wait..."""

    @staticmethod
    def error_message(error: str) -> str:
        """Generic error message"""
        return f"""❌ Error

{error}

Need help? /help"""

    @staticmethod
    def no_sources_error() -> str:
        """Error when no web sources are loaded"""
        return """⚠️ No sources found

Upload your source list first:
/webs → upload .txt/.csv with URLs

Then run /scrape again.
Need help? /help"""

    @staticmethod
    def no_proxies_error() -> str:
        """Error when no proxies are available"""
        return """⚠️ No proxies available

Run /scrape first to collect proxies.
Or upload a proxy file.

Need help? /help"""

    @staticmethod
    def file_too_large_error(size_mb: float, max_mb: float) -> str:
        """Error when file is too large"""
        return f"""⚠️ File Too Large

Your file: {size_mb:.1f}MB
Max allowed: {max_mb:.1f}MB

Please upload a smaller file."""

    @staticmethod
    def invalid_file_error() -> str:
        """Error when file format is invalid"""
        return """⚠️ Invalid File Format

Supported: .txt, .csv

Please convert and try again."""

    @staticmethod
    def operation_cancelled() -> str:
        """Message when operation is cancelled"""
        return """ℹ️ Operation cancelled

Start again:
• /webs – Upload sources
• /scrape – Scrape proxies
• /check – Validate proxies
• /help – Commands"""

    @staticmethod
    def processing_file() -> str:
        """Message when processing uploaded file"""
        return """⏳ Processing file

Please wait..."""
    
    @staticmethod
    def check_options_prompt() -> str:
        """Prompt for check options"""
        return """🔍 Choose how you want to check proxies:"""
    
    @staticmethod
    def export_prompt(results: dict) -> str:
        """Prompt for export options"""
        return f"""📥 Export Options

Select proxy type to download:

All Working: {len(results.get('all_working', []))}
HTTP: {len(results.get('http', []))}
HTTPS: {len(results.get('https', []))}
SOCKS4: {len(results.get('socks4', []))}
SOCKS5: {len(results.get('socks5', []))}
Elite: {len(results.get('elite', []))}
Anonymous: {len(results.get('anonymous', []))}
Transparent: {len(results.get('transparent', []))}"""
