import time
import httpx
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, ScrapingResult
import asyncio

class MercadoLivreScraper(BaseScraper):
    async def check_availability(self, url: str) -> ScrapingResult:
        await self._wait_random_delay()
        
        start_time = time.time()
        result = ScrapingResult(is_available=True)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.get_headers())
                result.http_status = response.status_code
                result.duration_ms = int((time.time() - start_time) * 1000)
                
                # Sinais básicos
                if response.status_code in (404, 410):
                    result.is_available = False
                    result.signals['http_404'] = True
                    return result
                
                if response.status_code >= 500:
                    result.error = f"Server error {response.status_code}"
                    return result
                    
                # Checar URL final para redirects suspeitos (home do ML)
                final_url = str(response.url)
                if final_url == "https://www.mercadolivre.com.br/" or "error" in final_url:
                    result.signals['redirect_home'] = True
                
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = soup.get_text().lower()
                
                # Checar seletor de preço
                price_el = soup.select_one('.andes-money-amount__fraction')
                if price_el:
                    try:
                        price_str = price_el.text.replace('.', '').replace(',', '.')
                        result.price = float(price_str)
                    except ValueError:
                        pass
                else:
                    result.signals['price_missing'] = True
                
                # Checar botão comprar
                buy_btn = soup.select_one('.ui-pdp-action--primary')
                if not buy_btn:
                    result.signals['buy_button_missing'] = True
                    
                # Checar textos de esgotado/pausado
                out_of_stock_texts = [
                    "este produto não está disponível",
                    "publicação pausada",
                    "anúncio pausado"
                ]
                
                for text in out_of_stock_texts:
                    if text in text_content:
                        result.signals['out_of_stock_text'] = True
                        break
                        
        except httpx.TimeoutException:
            result.error = "Timeout"
            result.signals['timeout'] = True
        except Exception as e:
            result.error = str(e)
            
        return result
