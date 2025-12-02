"""
Proxy Scraper Module - Async web scraping for proxies
"""
import asyncio
import aiohttp
import re
import time
from typing import Set, List, Callable, Optional
from urllib.parse import urlparse
import logging

from config import Config

logger = logging.getLogger(__name__)

class ProxyScraper:
    """Asynchronous proxy scraper"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.proxy_pattern = re.compile(
            r'(?:^|\D)((?:\d{1,3}\.){3}\d{1,3}):(\d{2,5})(?:\D|$)'
        )
        self.protocol_pattern = re.compile(
            r'(https?|socks[45])://(?:[\w]+:[\w]+@)?((?:\d{1,3}\.){3}\d{1,3}):(\d{2,5})'
        )
        self.scraped_proxies = set()
        self.web_sources = []
        self.progress_callback = progress_callback
        self.scraped_count = 0
        self.sources_completed = 0
        self.start_time = None
        
    def load_sources_from_file(self, filepath: str) -> int:
        """Load web sources from file"""
        self.web_sources = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.web_sources.append(line)
            logger.info(f"Loaded {len(self.web_sources)} web sources")
            return len(self.web_sources)
        except Exception as e:
            logger.error(f"Error loading sources: {e}")
            return 0
    
    def add_sources(self, sources: List[str]):
        """Add web sources from list"""
        self.web_sources.extend(sources)
        logger.info(f"Added {len(sources)} sources")
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, TypeError):
            return False
    
    def _is_valid_port(self, port: str) -> bool:
        """Validate port number"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    async def _scrape_from_url(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Scrape proxies from a single URL"""
        proxies = set()
        domain = urlparse(url).netloc or url[:30]
        
        try:
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=30),
                ssl=False
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # Try protocol-aware pattern first
                    protocol_matches = self.protocol_pattern.findall(text)
                    for protocol, ip, port in protocol_matches:
                        if self._is_valid_ip(ip) and self._is_valid_port(port):
                            proxies.add(f"{protocol}://{ip}:{port}")
                    
                    # Then try basic IP:PORT pattern
                    basic_matches = self.proxy_pattern.findall(text)
                    for ip, port in basic_matches:
                        if self._is_valid_ip(ip) and self._is_valid_port(port):
                            proxies.add(f"{ip}:{port}")
                    
                    logger.info(f"Scraped {len(proxies)} proxies from {domain}")
                else:
                    logger.warning(f"Failed to scrape {domain}: HTTP {response.status}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping {domain}")
        except Exception as e:
            logger.error(f"Error scraping {domain}: {str(e)}")
        
        return proxies
    
    async def _scrape_with_progress(self, session: aiohttp.ClientSession, url: str, 
                                     max_proxies: Optional[int]) -> Set[str]:
        """Scrape from URL with progress updates"""
        proxies = await self._scrape_from_url(session, url)
        
        self.scraped_proxies.update(proxies)
        self.sources_completed += 1
        self.scraped_count = len(self.scraped_proxies)
        
        # Calculate speed
        elapsed = time.time() - self.start_time
        speed = self.scraped_count / elapsed if elapsed > 0 else 0
        
        # Send progress update
        if self.progress_callback:
            await self.progress_callback(
                scraped=self.scraped_count,
                sources_done=self.sources_completed,
                total_sources=len(self.web_sources),
                speed=speed
            )
        
        # Check if we've reached the limit
        if max_proxies and self.scraped_count >= max_proxies:
            return proxies
            
        return proxies
    
    async def scrape_all(self, max_proxies: Optional[int] = None) -> Set[str]:
        """Scrape proxies from all sources with progress tracking"""
        if not self.web_sources:
            logger.warning("No web sources loaded")
            return set()
        
        self.scraped_proxies.clear()
        self.scraped_count = 0
        self.sources_completed = 0
        self.start_time = time.time()
        
        logger.info(f"Starting scraping from {len(self.web_sources)} sources...")
        
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            for url in self.web_sources:
                task = self._scrape_with_progress(session, url, max_proxies)
                tasks.append(task)
                
                # Don't create all tasks at once if we have many sources
                if len(tasks) >= 10:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks.clear()
                    
                    # Check if we've reached limit
                    if max_proxies and self.scraped_count >= max_proxies:
                        break
            
            # Process remaining tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Limit to max_proxies if specified
        if max_proxies and len(self.scraped_proxies) > max_proxies:
            self.scraped_proxies = set(list(self.scraped_proxies)[:max_proxies])
            self.scraped_count = len(self.scraped_proxies)
        
        elapsed = time.time() - self.start_time
        logger.info(f"Scraping completed: {self.scraped_count} proxies in {elapsed:.2f}s")
        
        return self.scraped_proxies
    
    def get_scraped_proxies(self) -> Set[str]:
        """Get all scraped proxies"""
        return self.scraped_proxies
    
    def clear(self):
        """Clear scraped proxies"""
        self.scraped_proxies.clear()
        self.scraped_count = 0
        self.sources_completed = 0
