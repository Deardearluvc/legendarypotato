"""
File Handler Module - Save and manage proxy files
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, List
import logging

from config import Config

logger = logging.getLogger(__name__)

class FileHandler:
    """Handle file operations for proxies"""
    
    @staticmethod
    def save_scraped_proxies(proxies: Set[str], user_id: int) -> Path:
        """Save scraped proxies to file with minimal naming"""
        timestamp = datetime.now().strftime('%Y%m%d')
        filename = f"scraped_{timestamp}.txt"
        filepath = Config.OUTPUT_DIR / filename
        
        try:
            with filepath.open('w', encoding='utf-8') as f:
                f.write(f"# Scraped Proxies\n")
                f.write(f"# Total: {len(proxies)}\n")
                f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for proxy in sorted(proxies):
                    f.write(f"{proxy}\n")
            
            logger.info(f"Saved {len(proxies)} scraped proxies to {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving scraped proxies: {e}")
            raise
    
    @staticmethod
    def save_checked_results(results: Dict, user_id: int) -> Dict[str, Path]:
        """Save checked proxy results categorized by type"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_files = {}
        
        categories = {
            'all_working': '✅ All Working Proxies',
            'http': '🌐 HTTP Proxies',
            'https': '🔒 HTTPS Proxies',
            'socks4': '🧦 SOCKS4 Proxies',
            'socks5': '🧦 SOCKS5 Proxies',
            'elite': '⭐ Elite Anonymous Proxies',
            'anonymous': '🎭 Anonymous Proxies',
            'transparent': '👁️ Transparent Proxies'
        }
        
        for category, proxies_list in results.items():
            if not proxies_list:
                continue
            
            try:
                filename = f"{category}_{user_id}_{timestamp}.txt"
                filepath = Config.OUTPUT_DIR / filename
                
                with filepath.open('w', encoding='utf-8') as f:
                    # Header
                    f.write(f"# {categories.get(category, category)}\n")
                    f.write(f"# Total: {len(proxies_list)}\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# User ID: {user_id}\n")
                    f.write("#" + "="*58 + "\n\n")
                    
                    # Sort by response time
                    sorted_proxies = sorted(
                        proxies_list,
                        key=lambda x: x.get('response_time', 999)
                    )
                    
                    # Write proxies with details
                    for result in sorted_proxies:
                        proxy = result['proxy']
                        protocols = ','.join(result['protocols'])
                        anonymity = result['anonymity']
                        response_time = result.get('response_time', 0)
                        
                        # Simple format: just proxy
                        f.write(f"{proxy}\n")
                        
                        # Detailed format in comments (optional)
                        f.write(
                            f"# Protocols: {protocols} | "
                            f"Anonymity: {anonymity} | "
                            f"Speed: {response_time:.3f}s\n"
                        )
                
                saved_files[category] = filepath
                logger.info(f"Saved {len(proxies_list)} {category} proxies to {filename}")
                
            except Exception as e:
                logger.error(f"Error saving {category} proxies: {e}")
        
        # Save JSON summary
        try:
            summary_filename = f"summary_{user_id}_{timestamp}.json"
            summary_path = Config.OUTPUT_DIR / summary_filename
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'total_working': len(results['all_working']),
                'categories': {
                    cat: {
                        'count': len(proxies_list),
                        'file': str(saved_files.get(cat, ''))
                    }
                    for cat, proxies_list in results.items()
                    if proxies_list
                }
            }
            
            with summary_path.open('w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            saved_files['summary'] = summary_path
            logger.info(f"Saved summary to {summary_filename}")
            
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
        
        return saved_files
    
    @staticmethod
    def load_proxies_from_file(filepath: Path) -> Set[str]:
        """Load proxies from file"""
        proxies = set()
        
        try:
            with filepath.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        proxies.add(line)
            
            logger.info(f"Loaded {len(proxies)} proxies from {filepath.name}")
            return proxies
            
        except Exception as e:
            logger.error(f"Error loading proxies from file: {e}")
            raise
    
    @staticmethod
    def create_quick_summary(results: Dict) -> str:
        """Create a quick text summary of results"""
        summary_lines = [
            "=" * 50,
            "PROXY CHECKING RESULTS SUMMARY",
            "=" * 50,
            "",
            f"✅ Total Working: {len(results['all_working'])}",
            "",
            "BY PROTOCOL:",
            f"  🌐 HTTP:    {len(results['http'])}",
            f"  🔒 HTTPS:   {len(results['https'])}",
            f"  🧦 SOCKS4:  {len(results['socks4'])}",
            f"  🧦 SOCKS5:  {len(results['socks5'])}",
            "",
            "BY ANONYMITY:",
            f"  ⭐ Elite:        {len(results['elite'])}",
            f"  🎭 Anonymous:    {len(results['anonymous'])}",
            f"  👁️ Transparent:  {len(results['transparent'])}",
            "",
            "=" * 50
        ]
        
        return "\n".join(summary_lines)
    
    @staticmethod
    def cleanup_old_files(user_id: int, keep_recent: int = 5):
        """Clean up old files for a user, keeping only recent ones"""
        try:
            # Get all files for this user
            user_files = list(Config.OUTPUT_DIR.glob(f"*_{user_id}_*.txt"))
            user_files.extend(Config.OUTPUT_DIR.glob(f"*_{user_id}_*.json"))
            
            # Sort by modification time (newest first)
            user_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Delete old files
            deleted_count = 0
            for filepath in user_files[keep_recent:]:
                try:
                    filepath.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Could not delete {filepath}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    @staticmethod
    def get_file_size_mb(filepath: Path) -> float:
        """Get file size in MB"""
        try:
            return filepath.stat().st_size / (1024 * 1024)
        except Exception:
            return 0.0
    
    @staticmethod
    def save_user_sources(user_id: int, sources: List[str]):
        """Save user's web sources permanently"""
        try:
            # Load existing data
            if Config.PERMANENT_SOURCES_FILE.exists():
                with open(Config.PERMANENT_SOURCES_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Update user's sources
            data[str(user_id)] = {
                'sources': sources,
                'updated_at': datetime.now().isoformat()
            }
            
            # Save back
            with open(Config.PERMANENT_SOURCES_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(sources)} sources for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving user sources: {e}")
    
    @staticmethod
    def load_user_sources(user_id: int) -> List[str]:
        """Load user's web sources"""
        try:
            if not Config.PERMANENT_SOURCES_FILE.exists():
                return []
            
            with open(Config.PERMANENT_SOURCES_FILE, 'r') as f:
                data = json.load(f)
            
            user_data = data.get(str(user_id), {})
            sources = user_data.get('sources', [])
            
            logger.info(f"Loaded {len(sources)} sources for user {user_id}")
            return sources
            
        except Exception as e:
            logger.error(f"Error loading user sources: {e}")
            return []
