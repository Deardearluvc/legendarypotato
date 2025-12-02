"""
Proxy Checker Module - Multi-protocol async checking
"""
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import time
from typing import Dict, Set, List, Optional, Callable, Tuple
import logging

from config import Config

logger = logging.getLogger(__name__)

class ProxyChecker:
    """Asynchronous multi-protocol proxy checker"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.results = {
            'http': [],
            'https': [],
            'socks4': [],
            'socks5': [],
            'elite': [],
            'anonymous': [],
            'transparent': [],
            'all_working': []
        }
        self.progress_callback = progress_callback
        self.checked_count = 0
        self.total_count = 0
        self.working_count = 0
        self.start_time = None
        self.real_ip = None
        
    async def _get_real_ip(self) -> str:
        """Get real IP address for anonymity detection"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('http://httpbin.org/ip') as response:
                    if response.status == 200:
                        data = await response.json()
                        ip = data.get('origin', '').split(',')[0].strip()
                        logger.info(f"Real IP detected: {ip}")
                        return ip
        except Exception as e:
            logger.warning(f"Could not detect real IP: {e}")
        return ''
    
    def _parse_proxy(self, proxy: str) -> Tuple[str, str, str, int]:
        """Parse proxy string and return (url, protocol, host, port)"""
        proxy = proxy.strip()
        
        # Check if protocol is specified
        if '://' in proxy:
            parts = proxy.split('://', 1)
            protocol = parts[0].lower()
            host_port = parts[1]
        else:
            # Default to http for basic IP:PORT format
            protocol = 'http'
            host_port = proxy
        
        # Extract host and port
        if ':' in host_port:
            host, port_str = host_port.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 8080
        else:
            host = host_port
            port = 8080
        
        # Build proxy URL
        proxy_url = f"{protocol}://{host}:{port}"
        
        return proxy_url, protocol, host, port
    
    def _detect_anonymity(self, headers: Dict, response_text: str) -> str:
        """Detect proxy anonymity level"""
        # Convert all values to lowercase string for checking
        header_str = ' '.join(str(v).lower() for v in headers.values())
        response_lower = response_text.lower()
        
        # Check if real IP is exposed
        if self.real_ip and self.real_ip.lower() in response_lower:
            return 'transparent'
        
        if self.real_ip and self.real_ip.lower() in header_str:
            return 'transparent'
        
        # Check for proxy-related headers
        proxy_headers = [
            'via', 'x-forwarded-for', 'forwarded-for', 'x-forwarded',
            'client-ip', 'forwarded', 'proxy-connection'
        ]
        
        has_proxy_headers = any(
            header in header_str for header in proxy_headers
        )
        
        if has_proxy_headers:
            return 'anonymous'
        
        # If no proxy indicators found, it's elite
        return 'elite'
    
    async def _check_proxy(self, proxy: str) -> Optional[Dict]:
        """Check a single proxy for all protocols"""
        proxy_url, detected_protocol, host, port = self._parse_proxy(proxy)
        
        result = {
            'proxy': f"{host}:{port}",
            'working': False,
            'protocols': [],
            'anonymity': 'unknown',
            'response_time': None
        }
        
        # Determine which protocols to test
        if detected_protocol in ['socks4', 'socks5']:
            protocols_to_test = [detected_protocol]
        elif detected_protocol == 'https':
            protocols_to_test = ['https', 'http']
        else:
            protocols_to_test = ['http', 'https']
        
        # Test each protocol
        for protocol in protocols_to_test:
            try:
                start_time = time.time()
                
                # Create appropriate connector
                if protocol in ['socks4', 'socks5']:
                    proxy_type = 'socks4' if protocol == 'socks4' else 'socks5'
                    connector = ProxyConnector.from_url(f"{proxy_type}://{host}:{port}")
                else:
                    connector = aiohttp.TCPConnector(ssl=False)
                
                timeout = aiohttp.ClientTimeout(total=Config.DEFAULT_TIMEOUT)
                
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                ) as session:
                    
                    # Use proxy for HTTP/HTTPS
                    proxy_param = f"http://{host}:{port}" if protocol in ['http', 'https'] else None
                    
                    test_url = Config.TEST_URLS.get(protocol, 'http://httpbin.org/ip')
                    
                    async with session.get(
                        test_url,
                        proxy=proxy_param
                    ) as response:
                        
                        if response.status == 200:
                            elapsed = time.time() - start_time
                            response_text = await response.text()
                            
                            result['working'] = True
                            result['protocols'].append(protocol)
                            result['response_time'] = round(elapsed, 3)
                            
                            # Detect anonymity (only for first successful protocol)
                            if result['anonymity'] == 'unknown':
                                result['anonymity'] = self._detect_anonymity(
                                    dict(response.headers),
                                    response_text
                                )
                            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Error testing {proxy} with {protocol}: {str(e)}")
                continue
        
        return result if result['working'] else None
    
    async def _check_with_progress(self, proxy: str) -> Optional[Dict]:
        """Check proxy with progress updates"""
        result = await self._check_proxy(proxy)
        
        self.checked_count += 1
        
        if result:
            self.working_count += 1
            self._categorize_result(result)
        
        # Calculate speed
        elapsed = time.time() - self.start_time if self.start_time else 1
        speed = self.checked_count / elapsed if elapsed > 0 else 0
        
        # Send progress update
        if self.progress_callback and self.checked_count % 10 == 0:
            await self.progress_callback(
                checked=self.checked_count,
                total=self.total_count,
                working=self.working_count,
                speed=speed
            )
        
        return result
    
    def _categorize_result(self, result: Dict):
        """Categorize working proxy into result lists"""
        # Add to all working
        self.results['all_working'].append(result)
        
        # Add to protocol categories
        for protocol in result['protocols']:
            if protocol in self.results:
                self.results[protocol].append(result)
        
        # Add to anonymity categories
        anonymity = result['anonymity']
        if anonymity in self.results:
            self.results[anonymity].append(result)
    
    async def check_all(self, proxies: Set[str]) -> Dict:
        """Check all proxies with progress tracking"""
        if not proxies:
            logger.warning("No proxies to check")
            return self.results
        
        # Reset counters
        self.checked_count = 0
        self.working_count = 0
        self.total_count = len(proxies)
        self.start_time = time.time()
        
        # Clear previous results
        for key in self.results:
            self.results[key].clear()
        
        # Get real IP for anonymity detection
        self.real_ip = await self._get_real_ip()
        
        logger.info(f"Starting to check {self.total_count} proxies...")
        
        # Create tasks in batches
        proxy_list = list(proxies)
        
        for i in range(0, len(proxy_list), Config.BATCH_SIZE):
            batch = proxy_list[i:i + Config.BATCH_SIZE]
            
            tasks = [self._check_with_progress(proxy) for proxy in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches to avoid overwhelming
            await asyncio.sleep(0.1)
        
        # Final progress update
        if self.progress_callback:
            elapsed = time.time() - self.start_time
            speed = self.checked_count / elapsed if elapsed > 0 else 0
            await self.progress_callback(
                checked=self.checked_count,
                total=self.total_count,
                working=self.working_count,
                speed=speed
            )
        
        elapsed = time.time() - self.start_time
        logger.info(
            f"Checking completed: {self.working_count}/{self.total_count} "
            f"working proxies in {elapsed:.2f}s"
        )
        
        return self.results
    
    def get_results(self) -> Dict:
        """Get checking results"""
        return self.results
    
    def clear(self):
        """Clear results"""
        for key in self.results:
            self.results[key].clear()
        self.checked_count = 0
        self.working_count = 0
        self.total_count = 0
