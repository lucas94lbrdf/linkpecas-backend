import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, ScrapingResult

class ShopeeScraper(BaseScraper):
    async def check_availability(self, url: str) -> ScrapingResult:
        await self._wait_random_delay()
        
        start_time = time.time()
        result = ScrapingResult(is_available=True)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.get_random_user_agent(),
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                    result.http_status = response.status if response else None
                    result.duration_ms = int((time.time() - start_time) * 1000)
                    
                    if result.http_status in (404, 410):
                        result.signals['http_404'] = True
                        return result
                    
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    text_content = soup.get_text().lower()
                    
                    # Checar botão comprar desabilitado ou 'esgotado'
                    if "esgotado" in text_content or "sold out" in text_content:
                        result.signals['out_of_stock_text'] = True
                    
                    # Botão desabilitado na shopee geralmente tem atributos específicos ou classes,
                    # mas o texto é a forma mais segura.
                    
                    price_el = soup.find(class_=lambda x: x and 'price' in x.lower())
                    if price_el:
                        try:
                            # Limpar
                            price_str = ''.join(c for c in price_el.text if c.isdigit() or c == ',')
                            if price_str:
                                result.price = float(price_str.replace(',', '.'))
                        except ValueError:
                            pass
                    else:
                        result.signals['price_missing'] = True
                        
                except PlaywrightTimeoutError:
                    result.error = "Timeout"
                    result.signals['timeout'] = True
                finally:
                    await browser.close()
                    
        except Exception as e:
            result.error = str(e)
            
        return result
