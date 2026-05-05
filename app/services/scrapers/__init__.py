from .base_scraper import BaseScraper, ScrapingResult
from .mercadolivre_scraper import MercadoLivreScraper
from .olx_scraper import OlxScraper
from .shopee_scraper import ShopeeScraper
from .generic_scraper import GenericScraper

__all__ = [
    "BaseScraper",
    "ScrapingResult",
    "MercadoLivreScraper",
    "OlxScraper",
    "ShopeeScraper",
    "GenericScraper"
]
