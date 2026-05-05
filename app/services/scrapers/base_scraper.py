from dataclasses import dataclass, field
from typing import Dict, Optional, List
import random
import time

@dataclass
class ScrapingResult:
    http_status: Optional[int] = None
    is_available: bool = True
    signals: Dict[str, any] = field(default_factory=dict)
    price: Optional[float] = None
    error: Optional[str] = None
    duration_ms: int = 0

class BaseScraper:
    def __init__(self):
        self.timeout = 15
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        ]

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    async def check_availability(self, url: str) -> ScrapingResult:
        raise NotImplementedError("Subclasses must implement check_availability")

    async def _wait_random_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)  # Use asyncio.sleep if called from async, but actually we use async sleep
        import asyncio
        await asyncio.sleep(delay)
