import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, ScrapingResult

class OlxScraper(BaseScraper):
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
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                    result.http_status = response.status if response else None
                    result.duration_ms = int((time.time() - start_time) * 1000)
                    
                    if result.http_status in (404, 410):
                        result.signals['http_404'] = True
                        return result
                    
                    # Espera um pouco pro JS renderizar
                    await page.wait_for_timeout(2000)
                    
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    text_content = soup.get_text().lower()
                    
                    # Checar textos de erro
                    if "anúncio não encontrado" in text_content or "anúncio encerrado" in text_content:
                        result.signals['out_of_stock_text'] = True
                    
                    # Checar preço (seletor pode variar na OLX, usando algo genérico)
                    price_el = soup.find(class_=lambda x: x and 'price' in x.lower())
                    if price_el:
                        try:
                            # Limpar e extrair
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
