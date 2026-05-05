import logging
import meilisearch
from typing import Dict, Any, List

logger = logging.getLogger("search_service")

# Configuração do Meilisearch
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env do root (backend/.env)
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

MEILI_URL = os.getenv("MEILI_URL", "http://meilisearch:7700")
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "664fe24934636943211567b84d631a2e")
INDEX_NAME = "ads"

logger.info(f"Conectando ao Meilisearch em: {MEILI_URL}")
client = meilisearch.Client(MEILI_URL, MEILI_MASTER_KEY)

def init_meilisearch_index():
    """Configura o índice do Meilisearch com os parâmetros otimizados."""
    try:
        # Se não existe o index, ele cria ao configurar
        client.create_index(INDEX_NAME, {'primaryKey': 'id'})
        
        index = client.index(INDEX_NAME)
        
        # Atributos Pesquisáveis
        index.update_searchable_attributes([
            'title',
            'vehicle_brand',
            'vehicle_model',
            'category_name',
            'shop_name',
            'description'
        ])
        
        # Atributos Filtráveis
        index.update_filterable_attributes([
            'category_id',
            'vehicle_brand',
            'vehicle_model',
            'year_min',
            'year_max',
            'price',
            'city',
            'state',
            'shop_id',
            'status'
        ])
        
        # Atributos Ordenáveis
        index.update_sortable_attributes([
            'price',
            'created_at',
            'views_count'
        ])
        
        # Regras de Ranking Otimizadas para E-commerce de Peças
        index.update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ])

        # Configurar Sinônimos Automotivos
        synonyms = {
            "bomba dagua": ["bomba d'agua", "bomba de agua", "water pump"],
            "bomba d'agua": ["bomba dagua", "bomba de agua", "water pump"],
            "bomba de agua": ["bomba dagua", "bomba d'agua", "water pump"],
            "alternador": ["gerador"],
            "gerador": ["alternador"],
            "pastilha": ["pastilha de freio"],
            "pastilha de freio": ["pastilha"],
            "vela": ["vela de ignição"],
            "vela de ignição": ["vela"],
            "amortecedor": ["suspensão"],
            "suspensão": ["amortecedor"],
            "pneu": ["pneus", "roda"],
            "roda": ["aro"],
            "bateria": ["acumulador"],
            "escapamento": ["escape", "silencioso", "descarga"],
            "farol": ["lanterna", "farolete", "iluminação"],
            "lanterna": ["farol", "sinaleira"],
            "embreagem": ["kit embreagem", "platô", "disco"],
            "correia": ["correia dentada", "tensor"],
            "oleo": ["óleo", "lubrificante", "fluido"],
            "óleo": ["oleo", "lubrificante", "fluido"],
            "filtro de ar": ["elemento filtrante"],
            "radiador": ["arrefecimento"],
            "parabrisa": ["para-brisa", "vidro"],
            "parachoque": ["para-choque"],
            "retrovisor": ["espelho"],
            "buzina": ["alarme sonora"],
            "palheta": ["limpador", "espanador"],
            "ignição": ["ignicao", "partida"],
            "freio": ["breque", "disco de freio"]
        }
        index.update_synonyms(synonyms)
        
        logger.info("Índice do Meilisearch 'ads' configurado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao inicializar Meilisearch: {e}")

def index_ad(ad: Dict[str, Any]):
    """Adiciona ou substitui um anúncio no índice."""
    try:
        index = client.index(INDEX_NAME)
        index.add_documents([ad])
        logger.info(f"Anúncio {ad.get('id')} indexado no Meilisearch.")
    except Exception as e:
        logger.error(f"Erro ao indexar anúncio no Meilisearch: {e}")

def update_ad_index(ad_id: str, data: Dict[str, Any]):
    """Atualiza parcialmente um anúncio no índice."""
    try:
        data['id'] = ad_id
        index = client.index(INDEX_NAME)
        index.update_documents([data])
        logger.info(f"Anúncio {ad_id} atualizado no Meilisearch.")
    except Exception as e:
        logger.error(f"Erro ao atualizar anúncio no Meilisearch: {e}")

def delete_ad_index(ad_id: str):
    """Remove um anúncio do índice."""
    try:
        index = client.index(INDEX_NAME)
        index.delete_document(ad_id)
        logger.info(f"Anúncio {ad_id} removido do Meilisearch.")
    except Exception as e:
        logger.error(f"Erro ao remover anúncio do Meilisearch: {e}")

def search_ads(query: str, filters: str = None, sort: List[str] = None, page: int = 1, limit: int = 50):
    """Busca anúncios usando o Meilisearch."""
    try:
        index = client.index(INDEX_NAME)
        search_params = {
            'offset': (page - 1) * limit,
            'limit': limit,
        }
        
        if filters:
            search_params['filter'] = filters
            
        if sort:
            search_params['sort'] = sort
            
        result = index.search(query, search_params)
        
        return {
            "hits": result.get('hits', []),
            "total": result.get('estimatedTotalHits', 0),
            "processing_time_ms": result.get('processingTimeMs', 0)
        }
    except Exception as e:
        logger.error(f"Erro na busca do Meilisearch: {e}")
        raise e
