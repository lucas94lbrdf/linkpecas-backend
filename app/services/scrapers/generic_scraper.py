import time
import httpx
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, ScrapingResult

class GenericScraper(BaseScraper):
    async def check_availability(self, url: str) -> ScrapingResult:
        await self._wait_random_delay()
        
        start_time = time.time()
        result = ScrapingResult(is_available=True)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.get_headers())
                result.http_status = response.status_code
                result.duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code in (404, 410):
                    result.signals['http_404'] = True
                    return result
                    
                if response.status_code >= 500:
                    result.error = f"Server error {response.status_code}"
                    return result
                
                # Checar redirect
                if str(response.url) != url and str(response.url).count('/') <= 3:
                    result.signals['redirect_home'] = True
                
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = soup.get_text().lower()
                
                # Regex patterns for out of stock
                oos_patterns = [
                    r'esgotado',
                    r'sold.?out',
                    r'indisponível',
                    r'fora de estoque',
                    r'encerrado'
                ]
                
                for pattern in oos_patterns:
                    if re.search(pattern, text_content):
                        result.signals['out_of_stock_text'] = True
                        break
                        
        except httpx.TimeoutException:
            result.error = "Timeout"
            result.signals['timeout'] = True
        except Exception as e:
            result.error = str(e)
            
        return result
