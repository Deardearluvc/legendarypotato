"""
Database Module - SQLite database for user data and proxy history
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging

from config import Config

logger = logging.getLogger(__name__)

class Database:
    """SQLite database manager for the bot"""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            db_path = Config.BASE_DIR / "proxy_bot.db"
        
        self.db_path = Path(db_path)
        self.conn = None
        self._initialize_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Return dict-like rows
        return self.conn
    
    def _initialize_db(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_scrapes INTEGER DEFAULT 0,
                total_checks INTEGER DEFAULT 0,
                total_proxies_scraped INTEGER DEFAULT 0,
                total_proxies_checked INTEGER DEFAULT 0,
                total_working_found INTEGER DEFAULT 0
            )
        ''')
        
        # Scrape history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrape_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sources_count INTEGER,
                proxies_scraped INTEGER,
                duration_seconds REAL,
                max_proxies INTEGER,
                output_file TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Check history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_checked INTEGER,
                total_working INTEGER,
                duration_seconds REAL,
                http_count INTEGER DEFAULT 0,
                https_count INTEGER DEFAULT 0,
                socks4_count INTEGER DEFAULT 0,
                socks5_count INTEGER DEFAULT 0,
                elite_count INTEGER DEFAULT 0,
                anonymous_count INTEGER DEFAULT 0,
                transparent_count INTEGER DEFAULT 0,
                average_response_time REAL,
                success_rate REAL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Web sources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS web_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                times_used INTEGER DEFAULT 0,
                last_proxy_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Proxy cache table (optional - for caching working proxies)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy TEXT UNIQUE NOT NULL,
                protocols TEXT,
                anonymity TEXT,
                response_time REAL,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                check_count INTEGER DEFAULT 1,
                success_count INTEGER DEFAULT 1,
                country TEXT,
                is_working BOOLEAN DEFAULT 1
            )
        ''')
        
        # Statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_scrapes INTEGER DEFAULT 0,
                total_checks INTEGER DEFAULT 0,
                total_proxies_scraped INTEGER DEFAULT 0,
                total_proxies_checked INTEGER DEFAULT 0,
                total_working_found INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    
    # ==================== USER OPERATIONS ====================
    
    def add_user(self, user_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None):
        """Add or update user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_active = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name, last_name))
            
            conn.commit()
            logger.info(f"User {user_id} added/updated")
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            conn.rollback()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def update_user_activity(self, user_id: int):
        """Update user's last active timestamp"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET last_active = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        user = self.get_user(user_id)
        if not user:
            return {}
        
        return {
            'total_scrapes': user['total_scrapes'],
            'total_checks': user['total_checks'],
            'total_proxies_scraped': user['total_proxies_scraped'],
            'total_proxies_checked': user['total_proxies_checked'],
            'total_working_found': user['total_working_found'],
            'member_since': user['created_at']
        }
    
    # ==================== SCRAPE HISTORY ====================
    
    def add_scrape_history(self, user_id: int, sources_count: int, 
                          proxies_scraped: int, duration: float,
                          max_proxies: int = None, output_file: str = None):
        """Record scrape operation"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Insert scrape record
            cursor.execute('''
                INSERT INTO scrape_history 
                (user_id, sources_count, proxies_scraped, duration_seconds, max_proxies, output_file)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, sources_count, proxies_scraped, duration, max_proxies, output_file))
            
            # Update user stats
            cursor.execute('''
                UPDATE users 
                SET total_scrapes = total_scrapes + 1,
                    total_proxies_scraped = total_proxies_scraped + ?
                WHERE user_id = ?
            ''', (proxies_scraped, user_id))
            
            conn.commit()
            logger.info(f"Scrape history recorded for user {user_id}")
        except Exception as e:
            logger.error(f"Error recording scrape history: {e}")
            conn.rollback()
    
    def get_scrape_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's scrape history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scrape_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== CHECK HISTORY ====================
    
    def add_check_history(self, user_id: int, results: Dict, duration: float):
        """Record check operation"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            total_checked = len(results.get('all_working', [])) + \
                          (results.get('total_checked', 0) - len(results.get('all_working', [])))
            total_working = len(results.get('all_working', []))
            
            # Calculate average response time
            all_working = results.get('all_working', [])
            avg_response_time = 0
            if all_working:
                response_times = [p.get('response_time', 0) for p in all_working]
                avg_response_time = sum(response_times) / len(response_times)
            
            success_rate = (total_working / total_checked * 100) if total_checked > 0 else 0
            
            # Insert check record
            cursor.execute('''
                INSERT INTO check_history 
                (user_id, total_checked, total_working, duration_seconds,
                 http_count, https_count, socks4_count, socks5_count,
                 elite_count, anonymous_count, transparent_count,
                 average_response_time, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, total_checked, total_working, duration,
                len(results.get('http', [])),
                len(results.get('https', [])),
                len(results.get('socks4', [])),
                len(results.get('socks5', [])),
                len(results.get('elite', [])),
                len(results.get('anonymous', [])),
                len(results.get('transparent', [])),
                avg_response_time,
                success_rate
            ))
            
            # Update user stats
            cursor.execute('''
                UPDATE users 
                SET total_checks = total_checks + 1,
                    total_proxies_checked = total_proxies_checked + ?,
                    total_working_found = total_working_found + ?
                WHERE user_id = ?
            ''', (total_checked, total_working, user_id))
            
            conn.commit()
            logger.info(f"Check history recorded for user {user_id}")
        except Exception as e:
            logger.error(f"Error recording check history: {e}")
            conn.rollback()
    
    def get_check_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's check history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM check_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== WEB SOURCES ====================
    
    def add_web_source(self, user_id: int, url: str):
        """Add web source for user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO web_sources (user_id, url)
                VALUES (?, ?)
                ON CONFLICT DO NOTHING
            ''', (user_id, url))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error adding web source: {e}")
            conn.rollback()
    
    def update_web_source_usage(self, user_id: int, url: str, proxy_count: int):
        """Update web source usage stats"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE web_sources 
                SET last_used = CURRENT_TIMESTAMP,
                    times_used = times_used + 1,
                    last_proxy_count = ?
                WHERE user_id = ? AND url = ?
            ''', (proxy_count, user_id, url))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating web source: {e}")
            conn.rollback()
    
    def get_user_web_sources(self, user_id: int) -> List[Dict]:
        """Get user's web sources"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM web_sources 
            WHERE user_id = ? AND is_active = 1
            ORDER BY times_used DESC
        ''', (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== PROXY CACHE ====================
    
    def cache_working_proxy(self, proxy: str, protocols: List[str], 
                           anonymity: str, response_time: float):
        """Cache a working proxy"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            protocols_str = ','.join(protocols)
            
            cursor.execute('''
                INSERT INTO proxy_cache 
                (proxy, protocols, anonymity, response_time)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(proxy) DO UPDATE SET
                    protocols = excluded.protocols,
                    anonymity = excluded.anonymity,
                    response_time = excluded.response_time,
                    last_checked = CURRENT_TIMESTAMP,
                    check_count = check_count + 1,
                    success_count = success_count + 1,
                    is_working = 1
            ''', (proxy, protocols_str, anonymity, response_time))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error caching proxy: {e}")
            conn.rollback()
    
    def get_cached_proxies(self, protocol: str = None, anonymity: str = None,
                          max_age_hours: int = 24) -> List[Dict]:
        """Get cached working proxies"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        query = '''
            SELECT * FROM proxy_cache 
            WHERE is_working = 1 
            AND last_checked > ?
        '''
        params = [cutoff_time.isoformat()]
        
        if protocol:
            query += " AND protocols LIKE ?"
            params.append(f"%{protocol}%")
        
        if anonymity:
            query += " AND anonymity = ?"
            params.append(anonymity)
        
        query += " ORDER BY response_time ASC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_proxy_dead(self, proxy: str):
        """Mark a proxy as not working"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE proxy_cache 
                SET is_working = 0,
                    last_checked = CURRENT_TIMESTAMP,
                    check_count = check_count + 1
                WHERE proxy = ?
            ''', (proxy,))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error marking proxy dead: {e}")
            conn.rollback()
    
    def cleanup_old_cached_proxies(self, days: int = 7):
        """Remove old cached proxies"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            cursor.execute('''
                DELETE FROM proxy_cache 
                WHERE last_checked < ?
            ''', (cutoff_time.isoformat(),))
            
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} old cached proxies")
        except Exception as e:
            logger.error(f"Error cleaning cached proxies: {e}")
            conn.rollback()
    
    # ==================== BOT STATISTICS ====================
    
    def update_daily_stats(self):
        """Update daily statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        try:
            # Get today's stats
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE DATE(last_active) = DATE('now')
            ''')
            active_users = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*), 
                       COALESCE(SUM(proxies_scraped), 0)
                FROM scrape_history 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            scrapes_today, proxies_scraped = cursor.fetchone()
            
            cursor.execute('''
                SELECT COUNT(*),
                       COALESCE(SUM(total_checked), 0),
                       COALESCE(SUM(total_working), 0)
                FROM check_history 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            checks_today, proxies_checked, working_found = cursor.fetchone()
            
            # Update or insert
            cursor.execute('''
                INSERT INTO bot_statistics 
                (date, total_users, active_users, total_scrapes, total_checks,
                 total_proxies_scraped, total_proxies_checked, total_working_found)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_users = excluded.total_users,
                    active_users = excluded.active_users,
                    total_scrapes = excluded.total_scrapes,
                    total_checks = excluded.total_checks,
                    total_proxies_scraped = excluded.total_proxies_scraped,
                    total_proxies_checked = excluded.total_proxies_checked,
                    total_working_found = excluded.total_working_found
            ''', (today, total_users, active_users, scrapes_today, checks_today,
                  proxies_scraped or 0, proxies_checked or 0, working_found or 0))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating daily stats: {e}")
            conn.rollback()
    
    def get_bot_statistics(self, days: int = 7) -> Dict:
        """Get bot statistics for last N days"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now().date() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM bot_statistics 
            WHERE date >= ? 
            ORDER BY date DESC
        ''', (cutoff_date,))
        
        daily_stats = [dict(row) for row in cursor.fetchall()]
        
        # Get overall stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_scrapes), SUM(total_checks) FROM users')
        total_scrapes, total_checks = cursor.fetchone()
        
        return {
            'total_users': total_users,
            'total_scrapes': total_scrapes or 0,
            'total_checks': total_checks or 0,
            'daily_stats': daily_stats
        }
    
    # ==================== UTILITY ====================
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()

# Create global database instance
db = Database()
