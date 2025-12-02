"""
Dear X Proxy Bot - Main Bot Handler with Full Integration
Telegram bot for proxy scraping and checking
"""
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

from telegram import Update, Message, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from telegram.constants import ParseMode, ChatAction

from config import Config, Emoji
from messages import Messages
from keyboards import Keyboards
from proxy_scraper import ProxyScraper

# Try to import fast checker, fallback to regular if not available
try:
    from proxy_checker_fast import FastProxyChecker as ProxyChecker
    FAST_CHECKER_AVAILABLE = True
    logger.info("✅ Using FastProxyChecker (100+ proxies/sec)")
except ImportError:
    from proxy_checker import ProxyChecker
    FAST_CHECKER_AVAILABLE = False
    logger.warning("⚠️ FastProxyChecker not available, using standard checker")
    logger.warning("Install: pip install uvloop aiodns cchardet")

from file_handler import FileHandler
from utils import ProgressTracker, parse_amount_input, create_stats_message
from database import db

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_WEBS_FILE = 1
WAITING_FOR_SCRAPE_AMOUNT = 2
WAITING_FOR_CHECK_FILE = 3

class ProxyBot:
    """Main bot class with integrated proxy functionality"""
    
    def __init__(self):
        self.app = None
        self.user_data = {}  # Store user-specific data
        self.file_handler = FileHandler()
    
    async def send_sticker(self, message, sticker_key: str):
        """Send sticker before operation for premium feel"""
        sticker_path = Config.STICKER_PATHS.get(sticker_key)
        
        if sticker_path and sticker_path.exists():
            try:
                with open(sticker_path, 'rb') as sticker_file:
                    await message.reply_sticker(sticker=sticker_file)
                await asyncio.sleep(0.3)  # Small delay for effect
            except Exception as e:
                logger.debug(f"Could not send sticker {sticker_key}: {e}")
        else:
            logger.warning(f"Sticker not found: {sticker_path}")
        
    def get_user_scraper(self, user_id: int) -> ProxyScraper:
        """Get or create scraper for user with auto-load of saved sources"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        
        if 'scraper' not in self.user_data[user_id]:
            scraper = ProxyScraper()
            
            # Auto-load saved sources
            saved_sources = self.file_handler.load_user_sources(user_id)
            if saved_sources:
                scraper.add_sources(saved_sources)
                logger.info(f"Auto-loaded {len(saved_sources)} sources for user {user_id}")
            
            self.user_data[user_id]['scraper'] = scraper
        
        return self.user_data[user_id]['scraper']
    
    def get_user_checker(self, user_id: int) -> ProxyChecker:
        """Get or create ultra-fast checker for user"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        
        if 'checker' not in self.user_data[user_id]:
            checker = ProxyChecker()
            
            # Configure for speed if using fast checker
            if FAST_CHECKER_AVAILABLE:
                checker.TIMEOUT = Config.DEFAULT_TIMEOUT
                checker.MAX_CONCURRENT = Config.MAX_CONCURRENT
                checker.BATCH_SIZE = Config.BATCH_SIZE
                checker.FAST_MODE = Config.FAST_MODE
                logger.info(f"⚡ Fast checker configured: {Config.MAX_CONCURRENT} concurrent, {Config.DEFAULT_TIMEOUT}s timeout")
            
            self.user_data[user_id]['checker'] = checker
        
        return self.user_data[user_id]['checker']
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_name = user.first_name or user.username or "there"
        
        # Add user to database
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        db.update_user_activity(user.id)
        
        message_text = Messages.start_message(user_name)
        
        # Send video with caption if video exists
        if Config.START_VIDEO_PATH.exists():
            try:
                await update.message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
                
                with open(Config.START_VIDEO_PATH, 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=message_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=Keyboards.start_keyboard()
                    )
                return
            except Exception as e:
                logger.error(f"Error sending video: {e}")
        
        # Fallback: Send as text
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.start_keyboard(),
            disable_web_page_preview=True
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        # Send sticker first
        await self.send_sticker(update.message, 'help')
        
        await update.message.reply_text(
            Messages.help_message(),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.help_keyboard()
        )
    
    async def webs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /webs command"""
        # Send sticker first
        await self.send_sticker(update.message, 'web')
        
        await update.message.reply_text(
            Messages.webs_prompt(),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.cancel_keyboard()
        )
        return WAITING_FOR_WEBS_FILE
    
    async def handle_webs_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded web sources file with permanent storage"""
        document = update.message.document
        
        if not document:
            await update.message.reply_text(Messages.invalid_file_error(), parse_mode=ParseMode.HTML)
            return WAITING_FOR_WEBS_FILE
        
        # Validate file
        file_size_mb = document.file_size / (1024 * 1024)
        max_size_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
        
        if document.file_size > Config.MAX_FILE_SIZE:
            await update.message.reply_text(
                Messages.file_too_large_error(file_size_mb, max_size_mb),
                parse_mode=ParseMode.HTML
            )
            return WAITING_FOR_WEBS_FILE
        
        file_ext = Path(document.file_name).suffix.lower()
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            await update.message.reply_text(Messages.invalid_file_error(), parse_mode=ParseMode.HTML)
            return WAITING_FOR_WEBS_FILE
        
        processing_msg = await update.message.reply_text(Messages.processing_file(), parse_mode=ParseMode.HTML)
        
        try:
            # Download file
            file = await document.get_file()
            file_path = Config.TEMP_DIR / f"webs_{update.effective_user.id}_{document.file_name}"
            await file.download_to_drive(file_path)
            
            # Load sources into scraper
            user_id = update.effective_user.id
            scraper = self.get_user_scraper(user_id)
            sources_count = scraper.load_sources_from_file(str(file_path))
            
            # Save sources permanently
            sources_list = scraper.web_sources
            self.file_handler.save_user_sources(user_id, sources_list)
            
            # Store file path
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['webs_file'] = str(file_path)
            
            await processing_msg.edit_text(
                Messages.webs_loaded(sources_count),
                parse_mode=ParseMode.HTML
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            await processing_msg.edit_text(Messages.error_message(str(e)), parse_mode=ParseMode.HTML)
            return ConversationHandler.END
    
    async def scrape_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scrape command"""
        user_id = update.effective_user.id
        scraper = self.get_user_scraper(user_id)
        
        if not scraper.web_sources:
            await update.message.reply_text(
                Messages.no_sources_error(),
                parse_mode=ParseMode.HTML,
                reply_markup=Keyboards.command_button('webs', f"{Emoji.UPLOAD} Upload Web Sources")
            )
            return
        
        # Send sticker first
        await self.send_sticker(update.message, 'scrape')
        
        await update.message.reply_text(
            Messages.scrape_prompt(),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.scrape_options_keyboard()
        )
    
    async def perform_scraping(self, query_or_message, user_id: int, max_proxies: Optional[int]):
        """Perform the actual scraping with progress updates"""
        scraper = self.get_user_scraper(user_id)
        
        # Send initial message
        progress_msg = await query_or_message.reply_text(
            Messages.scrape_started(max_proxies),
            parse_mode=ParseMode.HTML
        )
        
        start_time = time.time()
        last_update = 0
        
        # Progress callback
        async def update_progress(scraped, sources_done, total_sources, speed):
            nonlocal last_update
            current_time = time.time()
            
            # Update every 3 seconds
            if current_time - last_update >= Config.PROGRESS_UPDATE_INTERVAL:
                last_update = current_time
                try:
                    await progress_msg.edit_text(
                        Messages.scrape_progress(scraped, max_proxies or 999999, sources_done, speed),
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.debug(f"Could not update progress: {e}")
        
        # Set progress callback
        scraper.progress_callback = update_progress
        
        # Scrape
        try:
            proxies = await scraper.scrape_all(max_proxies)
            elapsed = time.time() - start_time
            
            # Save to file
            filepath = self.file_handler.save_scraped_proxies(proxies, user_id)
            
            # Record in database
            db.add_scrape_history(
                user_id=user_id,
                sources_count=len(scraper.web_sources),
                proxies_scraped=len(proxies),
                duration=elapsed,
                max_proxies=max_proxies,
                output_file=str(filepath)
            )
            
            # Send completion message
            await progress_msg.edit_text(
                Messages.scrape_complete(len(proxies), elapsed, filepath.name),
                parse_mode=ParseMode.HTML
            )
            
            # Send file
            await query_or_message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
            await query_or_message.reply_document(
                document=open(filepath, 'rb'),
                filename=filepath.name,
                caption=f"{Emoji.FILE} Scraped proxies file",
                reply_markup=Keyboards.command_button('check', f"{Emoji.CHECK} Check These Proxies")
            )
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            await progress_msg.edit_text(
                Messages.error_message(f"Scraping failed: {str(e)}"),
                parse_mode=ParseMode.HTML
            )
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command"""
        # Send sticker first
        await self.send_sticker(update.message, 'check')
        
        await update.message.reply_text(
            Messages.check_options_prompt(),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.check_options_keyboard()
        )
    
    async def perform_checking(self, query_or_message, user_id: int, proxies: set):
        """Perform the actual checking with progress updates"""
        checker = self.get_user_checker(user_id)
        
        # Send initial message
        progress_msg = await query_or_message.reply_text(
            Messages.check_started(len(proxies)),
            parse_mode=ParseMode.HTML
        )
        
        start_time = time.time()
        last_update = 0
        
        # Progress callback
        async def update_progress(checked, total, working, speed):
            nonlocal last_update
            current_time = time.time()
            
            # Update every 3 seconds
            if current_time - last_update >= Config.PROGRESS_UPDATE_INTERVAL:
                last_update = current_time
                try:
                    await progress_msg.edit_text(
                        Messages.check_progress(checked, total, working, speed),
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.debug(f"Could not update progress: {e}")
        
        # Set progress callback
        checker.progress_callback = update_progress
        
        # Check proxies
        try:
            results = await checker.check_all(proxies)
            elapsed = time.time() - start_time
            
            # Store results in user data for export
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['last_check_results'] = results
            
            # Record in database
            db.add_check_history(user_id, results, elapsed)
            
            # Cache working proxies
            for proxy_result in results.get('all_working', []):
                db.cache_working_proxy(
                    proxy=proxy_result['proxy'],
                    protocols=proxy_result['protocols'],
                    anonymity=proxy_result['anonymity'],
                    response_time=proxy_result.get('response_time', 0)
                )
            
            # Send completion message
            await progress_msg.edit_text(
                Messages.check_complete(results, elapsed),
                parse_mode=ParseMode.HTML
            )
            
            # Send stats with export options
            stats_msg = create_stats_message(results)
            await query_or_message.reply_text(
                stats_msg + f"\n\n{Emoji.INFO} Use Export Options to download specific proxy types!",
                parse_mode=ParseMode.HTML,
                reply_markup=Keyboards.results_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Checking error: {e}")
            await progress_msg.edit_text(
                Messages.error_message(f"Checking failed: {str(e)}"),
                parse_mode=ParseMode.HTML
            )
    
    async def auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /auto command"""
        user_id = update.effective_user.id
        scraper = self.get_user_scraper(user_id)
        
        if not scraper.web_sources:
            await update.message.reply_text(
                Messages.no_sources_error(),
                parse_mode=ParseMode.HTML,
                reply_markup=Keyboards.command_button('webs', f"{Emoji.UPLOAD} Upload Web Sources")
            )
            return
        
        # Send sticker first
        await self.send_sticker(update.message, 'auto')
        
        await update.message.reply_text(
            Messages.auto_started(),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.auto_confirm_keyboard()
        )
    
    async def perform_auto(self, query_or_message, user_id: int):
        """Perform complete automation"""
        try:
            # Step 1: Scrape
            await query_or_message.reply_text(
                f"{Emoji.SEARCH} <b>STEP 1/2: SCRAPING</b>",
                parse_mode=ParseMode.HTML
            )
            await self.perform_scraping(query_or_message, user_id, max_proxies=1000)
            
            # Step 2: Check
            scraper = self.get_user_scraper(user_id)
            proxies = scraper.get_scraped_proxies()
            
            if not proxies:
                await query_or_message.reply_text(
                    Messages.error_message("No proxies were scraped!"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            await query_or_message.reply_text(
                f"{Emoji.CHECK} <b>STEP 2/2: CHECKING</b>",
                parse_mode=ParseMode.HTML
            )
            await self.perform_checking(query_or_message, user_id, proxies)
            
        except Exception as e:
            logger.error(f"Auto mode error: {e}")
            await query_or_message.reply_text(
                Messages.error_message(f"Automation failed: {str(e)}"),
                parse_mode=ParseMode.HTML
            )
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        # Send sticker first
        await self.send_sticker(update.message, 'cancel')
        
        await update.message.reply_text(
            Messages.operation_cancelled(),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.help_keyboard()
        )
        return ConversationHandler.END
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show user statistics"""
        user_id = update.effective_user.id
        
        # Send sticker first
        await self.send_sticker(update.message, 'stats')
        
        # Get user stats
        user_stats = db.get_user_stats(user_id)
        
        if not user_stats:
            await update.message.reply_text(
                f"{Emoji.INFO} No statistics available yet. Start using the bot!",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Get recent history
        scrape_history = db.get_scrape_history(user_id, limit=5)
        check_history = db.get_check_history(user_id, limit=5)
        
        # Build stats message
        stats_text = f"""
{Emoji.CHART} <b>YOUR STATISTICS</b>

<b>Overall:</b>
├ Total Scrapes: <b>{user_stats['total_scrapes']}</b>
├ Total Checks: <b>{user_stats['total_checks']}</b>
├ Proxies Scraped: <b>{user_stats['total_proxies_scraped']:,}</b>
├ Proxies Checked: <b>{user_stats['total_proxies_checked']:,}</b>
└ Working Found: <b>{user_stats['total_working_found']:,}</b>

<b>Member Since:</b> {user_stats['member_since'][:10]}
"""
        
        if scrape_history:
            stats_text += f"\n<b>Recent Scrapes:</b>\n"
            for scrape in scrape_history[:3]:
                stats_text += f"├ {scrape['proxies_scraped']} proxies ({scrape['duration_seconds']:.1f}s)\n"
        
        if check_history:
            stats_text += f"\n<b>Recent Checks:</b>\n"
            for check in check_history[:3]:
                success_rate = check['success_rate']
                stats_text += f"├ {check['total_working']}/{check['total_checked']} ({success_rate:.1f}%)\n"
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.help_keyboard()
        )
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command - export all checked proxies with pre-check"""
        user_id = update.effective_user.id
        
        # Send sticker first
        await self.send_sticker(update.message, 'export')
        
        # Check if user has recent results
        if user_id not in self.user_data or 'last_check_results' not in self.user_data[user_id]:
            await update.message.reply_text(
                "⚠️ No checked proxies found.\n\nRun /check first to validate proxies.",
                parse_mode=ParseMode.HTML
            )
            return
        
        results = self.user_data[user_id]['last_check_results']
        
        if not results.get('all_working'):
            await update.message.reply_text(
                "⚠️ No working proxies to export.\n\nCheck some proxies first.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Show export options
        await update.message.reply_text(
            Messages.export_prompt(results),
            parse_mode=ParseMode.HTML,
            reply_markup=Keyboards.export_options_keyboard()
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        callback_data = query.data
        
        # Help button
        if callback_data == "help":
            try:
                await query.edit_message_text(
                    Messages.help_message(),
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.help_keyboard()
                )
            except Exception as e:
                # If edit fails (e.g., message is video), send new message
                logger.debug(f"Could not edit message: {e}")
                await query.message.reply_text(
                    Messages.help_message(),
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.help_keyboard()
                )
        
        # Back to start
        elif callback_data == "back_to_start":
            user = update.effective_user
            user_name = user.first_name or user.username or "there"
            
            await query.edit_message_text(
                Messages.start_message(user_name),
                parse_mode=ParseMode.HTML,
                reply_markup=Keyboards.start_keyboard()
            )
        
        # Command shortcuts
        elif callback_data.startswith("cmd_"):
            command = callback_data.replace("cmd_", "")
            
            if command == "webs":
                await query.message.reply_text(
                    Messages.webs_prompt(),
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.cancel_keyboard()
                )
            
            elif command == "scrape":
                scraper = self.get_user_scraper(user_id)
                if not scraper.web_sources:
                    await query.message.reply_text(Messages.no_sources_error(), parse_mode=ParseMode.HTML)
                else:
                    await query.message.reply_text(
                        Messages.scrape_prompt(),
                        parse_mode=ParseMode.HTML,
                        reply_markup=Keyboards.scrape_options_keyboard()
                    )
            
            elif command == "check":
                await query.message.reply_text(
                    f"{Emoji.CHECK} <b>CHECK PROXIES</b>\n\nChoose an option:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.check_options_keyboard()
                )
            
            elif command == "auto":
                await query.message.reply_text(
                    Messages.auto_started(),
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.auto_confirm_keyboard()
                )
        
        # Scrape options
        elif callback_data.startswith("scrape_"):
            amount = callback_data.replace("scrape_", "")
            
            if amount == "custom":
                await query.message.reply_text(
                    f"{Emoji.INFO} Please send the number of proxies to scrape:",
                    parse_mode=ParseMode.HTML
                )
                return WAITING_FOR_SCRAPE_AMOUNT
            
            elif amount == "all":
                await self.perform_scraping(query.message, user_id, None)
            
            else:
                max_proxies = int(amount)
                await self.perform_scraping(query.message, user_id, max_proxies)
        
        # Check options
        elif callback_data == "check_scraped":
            scraper = self.get_user_scraper(user_id)
            proxies = scraper.get_scraped_proxies()
            
            if not proxies:
                await query.message.reply_text(Messages.no_proxies_error(), parse_mode=ParseMode.HTML)
            else:
                await self.perform_checking(query.message, user_id, proxies)
        
        elif callback_data == "check_upload":
            await query.message.reply_text(
                f"{Emoji.UPLOAD} <b>UPLOAD PROXY FILE</b>\n\n"
                f"Please upload a file containing proxies (one per line).\n\n"
                f"{Emoji.INFO} Supported formats: .txt, .csv",
                parse_mode=ParseMode.HTML,
                reply_markup=Keyboards.cancel_keyboard()
            )
            return WAITING_FOR_CHECK_FILE
        
        # Auto confirm
        elif callback_data == "auto_confirm":
            await self.perform_auto(query.message, user_id)
        
        # Export menu
        elif callback_data == "export_menu":
            # Check if user has recent results
            if user_id not in self.user_data or 'last_check_results' not in self.user_data[user_id]:
                await query.message.reply_text(
                    f"{Emoji.WARNING} No recent check results found.\n\nPlease run /check first!",
                    parse_mode=ParseMode.HTML
                )
                return
            
            results = self.user_data[user_id]['last_check_results']
            
            # Show export options
            export_text = Messages.export_prompt(results)
            
            try:
                await query.edit_message_text(
                    export_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.export_options_keyboard()
                )
            except:
                await query.message.reply_text(
                    export_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=Keyboards.export_options_keyboard()
                )
        
        # Export handlers
        elif callback_data.startswith("export_"):
            # Check if user has results
            if user_id not in self.user_data or 'last_check_results' not in self.user_data[user_id]:
                await query.message.reply_text(
                    f"{Emoji.WARNING} No recent check results found.\n\nPlease run /check first!",
                    parse_mode=ParseMode.HTML
                )
                return
            
            results = self.user_data[user_id]['last_check_results']
            export_type = callback_data.replace("export_", "")
            
            # Send appropriate sticker based on export type
            sticker_map = {
                'http': 'export_http',
                'https': 'export_https',
                'socks4': 'export_socks4',
                'socks5': 'export_socks5',
                'elite': 'export_elite',
                'anonymous': 'export_anonymous',
                'transparent': 'export_transparent',
                'all_categories': 'export_all',
                'all_working': 'export_all'
            }
            
            if export_type in sticker_map:
                await self.send_sticker(query.message, sticker_map[export_type])
            
            # Handle different export types
            if export_type == "all_categories":
                # Export all categories
                await query.message.reply_text(
                    f"{Emoji.HOURGLASS} Preparing all files...",
                    parse_mode=ParseMode.HTML
                )
                
                saved_files = self.file_handler.save_checked_results(results, user_id)
                
                await query.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
                
                for category, filepath in saved_files.items():
                    if category == 'summary':
                        continue
                    
                    try:
                        with open(filepath, 'rb') as f:
                            await query.message.reply_document(
                                document=f,
                                filename=filepath.name,
                                caption=f"{Emoji.FILE} {category.replace('_', ' ').title()} ({len(results.get(category, []))} proxies)"
                            )
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error sending file: {e}")
            
            else:
                # Export specific category
                category_proxies = results.get(export_type, [])
                
                if not category_proxies:
                    await query.message.reply_text(
                        f"{Emoji.WARNING} No {export_type} proxies found!",
                        parse_mode=ParseMode.HTML
                    )
                    return
                
                await query.message.reply_text(
                    f"{Emoji.HOURGLASS} Preparing {export_type} file with {len(category_proxies)} proxies...",
                    parse_mode=ParseMode.HTML
                )
                
                # Create single category results
                single_category_results = {export_type: category_proxies}
                saved_files = self.file_handler.save_checked_results(single_category_results, user_id)
                
                # Send the file
                if export_type in saved_files:
                    filepath = saved_files[export_type]
                    
                    await query.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
                    
                    try:
                        with open(filepath, 'rb') as f:
                            await query.message.reply_document(
                                document=f,
                                filename=filepath.name,
                                caption=f"{Emoji.FILE} {export_type.replace('_', ' ').title()} - {len(category_proxies)} proxies",
                                reply_markup=Keyboards.export_options_keyboard()
                            )
                    except Exception as e:
                        logger.error(f"Error sending file: {e}")
                        await query.message.reply_text(
                            Messages.error_message(f"Failed to send file: {str(e)}"),
                            parse_mode=ParseMode.HTML
                        )
        
        # Cancel
        elif callback_data == "cancel":
            await query.edit_message_text(Messages.operation_cancelled(), parse_mode=ParseMode.HTML)
            return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                Messages.error_message("An unexpected error occurred. Please try again."),
                parse_mode=ParseMode.HTML
            )
    
    def run(self):
        """Run the bot"""
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        
        # Conversation handlers
        webs_conv = ConversationHandler(
            entry_points=[CommandHandler('webs', self.webs_command)],
            states={
                WAITING_FOR_WEBS_FILE: [MessageHandler(filters.Document.ALL, self.handle_webs_file)]
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)]
        )
        
        # Add handlers
        self.app.add_handler(CommandHandler('start', self.start_command))
        self.app.add_handler(CommandHandler('help', self.help_command))
        self.app.add_handler(webs_conv)
        self.app.add_handler(CommandHandler('scrape', self.scrape_command))
        self.app.add_handler(CommandHandler('check', self.check_command))
        self.app.add_handler(CommandHandler('auto', self.auto_command))
        self.app.add_handler(CommandHandler('export', self.export_command))
        self.app.add_handler(CommandHandler('stats', self.stats_command))
        self.app.add_handler(CommandHandler('cancel', self.cancel_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_error_handler(self.error_handler)
        
        logger.info("=" * 60)
        logger.info("🚀 Dear X Proxy Bot Started Successfully!")
        logger.info(f"📱 Bot username: @{Config.BOT_USERNAME}")
        logger.info(f"🔗 Bot link: {Config.BOT_LINK}")
        logger.info(f"⚡ Fast checker: {'ENABLED' if FAST_CHECKER_AVAILABLE else 'DISABLED'}")
        if FAST_CHECKER_AVAILABLE:
            logger.info(f"⚙️ Speed settings: {Config.MAX_CONCURRENT} concurrent, {Config.DEFAULT_TIMEOUT}s timeout")
            logger.info(f"🎯 Expected speed: 100-150 proxies/sec")
        logger.info("=" * 60)
        
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main entry point"""
    bot = ProxyBot()
    bot.run()

if __name__ == '__main__':
    main()
