"""
Keyboard layouts for Dear X Proxy Bot
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config, Emoji

class Keyboards:
    """Inline keyboard layouts"""
    
    @staticmethod
    def start_keyboard() -> InlineKeyboardMarkup:
        """
        Start menu keyboard with 3 buttons:
        Row 1: Channel | Support
        Row 2: Help & Commands
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{Emoji.MEGAPHONE} Channel",
                    url=Config.CHANNEL_URL
                ),
                InlineKeyboardButton(
                    f"{Emoji.CHAT} Support",
                    url=Config.SUPPORT_URL
                )
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.BOOK} Help & Commands",
                    callback_data="help"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_keyboard() -> InlineKeyboardMarkup:
        """Help menu keyboard with command shortcuts"""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{Emoji.GLOBE} Web Sources",
                    callback_data="cmd_webs"
                ),
                InlineKeyboardButton(
                    f"{Emoji.SEARCH} Scrape",
                    callback_data="cmd_scrape"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.CHECK} Check",
                    callback_data="cmd_check"
                ),
                InlineKeyboardButton(
                    f"{Emoji.ROCKET} Auto",
                    callback_data="cmd_auto"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.MEGAPHONE} Channel",
                    url=Config.CHANNEL_URL
                ),
                InlineKeyboardButton(
                    f"{Emoji.CHAT} Support",
                    url=Config.SUPPORT_URL
                )
            ],
            [
                InlineKeyboardButton(
                    f"« Back to Start",
                    callback_data="back_to_start"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def scrape_options_keyboard() -> InlineKeyboardMarkup:
        """Scraping options keyboard - 3x2 layout"""
        keyboard = [
            # Row 1: 3 columns
            [
                InlineKeyboardButton("100", callback_data="scrape_100"),
                InlineKeyboardButton("1,000", callback_data="scrape_1000"),
                InlineKeyboardButton("10,000", callback_data="scrape_10000")
            ],
            # Row 2: 2 columns
            [
                InlineKeyboardButton("All", callback_data="scrape_all"),
                InlineKeyboardButton("Custom", callback_data="scrape_custom")
            ],
            # Row 3: Cancel
            [
                InlineKeyboardButton("Cancel", callback_data="cancel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def check_options_keyboard() -> InlineKeyboardMarkup:
        """Checking options keyboard - 2 rows, 1 column each"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Check Scraped Proxies",
                    callback_data="check_scraped"
                )
            ],
            [
                InlineKeyboardButton(
                    "Upload Proxy File",
                    callback_data="check_upload"
                )
            ],
            [
                InlineKeyboardButton(
                    "Cancel",
                    callback_data="cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def cancel_keyboard() -> InlineKeyboardMarkup:
        """Simple cancel button"""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{Emoji.CROSS} Cancel Operation",
                    callback_data="cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_help_keyboard() -> InlineKeyboardMarkup:
        """Back to help button"""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"« Back to Help",
                    callback_data="help"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def results_keyboard(has_files: bool = True) -> InlineKeyboardMarkup:
        """Results display keyboard"""
        keyboard = []
        
        if has_files:
            keyboard.append([
                InlineKeyboardButton(
                    f"{Emoji.DOWNLOAD} Export Options",
                    callback_data="export_menu"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"{Emoji.CHECK} Check More Proxies",
                    callback_data="cmd_check"
                )
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton(
                    f"{Emoji.SEARCH} Scrape Again",
                    callback_data="cmd_scrape"
                ),
                InlineKeyboardButton(
                    f"{Emoji.ROCKET} Auto Mode",
                    callback_data="cmd_auto"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.BOOK} Help",
                    callback_data="help"
                )
            ]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def export_options_keyboard() -> InlineKeyboardMarkup:
        """Export options keyboard - NO EMOJIS on buttons"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "All Working",
                    callback_data="export_all_working"
                )
            ],
            [
                InlineKeyboardButton("HTTP", callback_data="export_http"),
                InlineKeyboardButton("HTTPS", callback_data="export_https")
            ],
            [
                InlineKeyboardButton("SOCKS4", callback_data="export_socks4"),
                InlineKeyboardButton("SOCKS5", callback_data="export_socks5")
            ],
            [
                InlineKeyboardButton("Elite", callback_data="export_elite")
            ],
            [
                InlineKeyboardButton("Anonymous", callback_data="export_anonymous"),
                InlineKeyboardButton("Transparent", callback_data="export_transparent")
            ],
            [
                InlineKeyboardButton("Export All", callback_data="export_all_categories")
            ],
            [
                InlineKeyboardButton("Cancel", callback_data="cancel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def auto_confirm_keyboard() -> InlineKeyboardMarkup:
        """Confirmation keyboard for auto mode"""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{Emoji.ROCKET} Start Automation",
                    callback_data="auto_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    f"« Cancel",
                    callback_data="cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def command_button(command: str, label: str) -> InlineKeyboardMarkup:
        """Generic command button"""
        keyboard = [
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"cmd_{command}"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
