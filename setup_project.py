#!/usr/bin/env python3
import os
from pathlib import Path

def create_file(path_str, content):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ Criado: {path}")

# Diretório base
base = Path("/Users/pedromagalhaes/Projects/Labs/FlightTicker")

# 1. requirements.txt
create_file(base / "requirements.txt", """httpx==0.27.0
pydantic==2.9.2
python-dotenv==1.0.1
rich==13.9.2
numpy==1.26.4""")

# 2. .env.example
create_file(base / ".env.example", """# Copie para .env e preencha com suas chaves reais:
TEQUILA_API_KEY=coloque_sua_chave_tequila_aqui

AMADEUS_CLIENT_ID=coloque_seu_client_id_aqui
AMADEUS_CLIENT_SECRET=coloque_seu_client_secret_aqui

# Preferências
DEFAULT_CURRENCY=EUR
DEFAULT_LOCALE=pt-PT""")

# 3. .gitignore
create_file(base / ".gitignore", """.env
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db""")

# 4. Estrutura de pacotes
create_file(base / "src" / "__init__.py", "")
create_file(base / "src" / "flight_ticker" / "__init__.py", "")

# 5. Domain Models
create_file(base / "src" / "flight_ticker" / "domain" / "__init__.py", "")
create_file(base / "src" / "flight_ticker" / "domain" / "models.py", '''"""
Domain Models - Entidades de negócio puras
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FlightSegment(BaseModel):
    """Segmento de voo individual"""
    origin: str = Field(..., description="IATA código origem")
    destination: str = Field(..., description="IATA código destino")
    departure: str = Field(..., description="ISO datetime partida")
    arrival: str = Field(..., description="ISO datetime chegada")
    marketing_carrier: Optional[str] = None
    flight_number: Optional[str] = None
    duration_minutes: Optional[int] = None


class FlightOffer(BaseModel):
    """Oferta de voo completa"""
    provider: str
    price_total: float
    currency: str
    baggage_included: bool = False
    cabin_class: Optional[str] = None
    segments: List[FlightSegment]
    booking_link: Optional[str] = None
    refundable: Optional[bool] = None
    changeable: Optional[bool] = None
    notes: Optional[str] = None
    ai_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    
    @property
    def total_stops(self) -> int:
        """Número total de paradas"""
        return max(0, len(self.segments) - 1)
    
    @property
    def route_summary(self) -> str:
        """Resumo da rota"""
        if not self.segments:
            return ""
        origins = [self.segments[0].origin]
        destinations = [seg.destination for seg in self.segments]
        return " → ".join(origins + destinations)


class SearchCriteria(BaseModel):
    """Critérios de busca"""
    origin: str
    destination: str
    depart_dates: List[str]  # "YYYY-MM-DD"
    return_dates: Optional[List[str]] = None
    adults: int = 1
    cabin_class: Optional[str] = None
    max_stops: Optional[int] = None
    preferred_currency: Optional[str] = None
    locale: Optional[str] = None
    carry_on_only: bool = False
    checked_bag: bool = False
    max_price: Optional[float] = None
    
    def is_round_trip(self) -> bool:
        """Verifica se é ida e volta"""
        return self.return_dates is not None and len(self.return_dates) > 0


class SearchResult(BaseModel):
    """Resultado de uma busca"""
    offers: List[FlightOffer]
    search_criteria: SearchCriteria
    search_timestamp: datetime
    total_found: int
    
    @property
    def best_offer(self) -> Optional[FlightOffer]:
        """Melhor oferta por score de IA ou preço"""
        if not self.offers:
            return None
        return max(self.offers, key=lambda x: x.ai_score or 0.0)
    
    @property
    def cheapest_offer(self) -> Optional[FlightOffer]:
        """Oferta mais barata"""
        if not self.offers:
            return None
        return min(self.offers, key=lambda x: x.price_total)
''')

# 6. Application Layer
create_file(base / "src" / "flight_ticker" / "application" / "__init__.py", "")
create_file(base / "src" / "flight_ticker" / "application" / "interfaces.py", '''"""
Interfaces/Contratos para Application Layer
"""
from abc import ABC, abstractmethod
from typing import List, Protocol
from ..domain.models import SearchCriteria, FlightOffer


class FlightProviderInterface(Protocol):
    """Interface para provedores de voo"""
    name: str
    
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca ofertas de voo"""
        ...


class ScoringServiceInterface(ABC):
    """Interface para serviço de pontuação de ofertas"""
    
    @abstractmethod
    def score_offers(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Pontua e ordena ofertas por valor"""
        pass


class SearchStrategyInterface(ABC):
    """Interface para estratégias de busca"""
    
    @abstractmethod
    async def execute(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Executa a estratégia de busca"""
        pass
''')

create_file(base / "src" / "flight_ticker" / "application" / "services.py", '''"""
Application Services - Casos de uso principais
"""
import asyncio
from typing import List
from datetime import datetime

from ..domain.models import SearchCriteria, FlightOffer, SearchResult
from .interfaces import FlightProviderInterface, ScoringServiceInterface, SearchStrategyInterface


class FlightSearchService:
    """Serviço principal de busca de voos"""
    
    def __init__(
        self,
        providers: List[FlightProviderInterface],
        scoring_service: ScoringServiceInterface,
        strategies: List[SearchStrategyInterface]
    ):
        self._providers = providers
        self._scoring_service = scoring_service
        self._strategies = strategies
    
    async def search(self, criteria: SearchCriteria) -> SearchResult:
        """Executa busca completa com todas as estratégias"""
        all_offers: List[FlightOffer] = []
        
        # Executa todas as estratégias em paralelo
        strategy_tasks = [strategy.execute(criteria) for strategy in self._strategies]
        strategy_results = await asyncio.gather(*strategy_tasks, return_exceptions=True)
        
        # Coleta resultados válidos
        for result in strategy_results:
            if isinstance(result, list):
                all_offers.extend(result)
        
        # Remove duplicatas
        unique_offers = self._deduplicate_offers(all_offers)
        
        # Aplica filtros finais
        filtered_offers = self._apply_filters(unique_offers, criteria)
        
        # Pontua e ordena
        scored_offers = self._scoring_service.score_offers(filtered_offers)
        
        return SearchResult(
            offers=scored_offers,
            search_criteria=criteria,
            search_timestamp=datetime.now(),
            total_found=len(scored_offers)
        )
    
    def _deduplicate_offers(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Remove ofertas duplicadas"""
        seen = set()
        unique = []
        
        for offer in offers:
            # Cria assinatura única baseada em rota e preço
            signature = (
                offer.provider,
                offer.route_summary,
                round(offer.price_total, 2)
            )
            
            if signature not in seen:
                seen.add(signature)
                unique.append(offer)
        
        return unique
    
    def _apply_filters(self, offers: List[FlightOffer], criteria: SearchCriteria) -> List[FlightOffer]:
        """Aplica filtros baseados nos critérios"""
        filtered = offers
        
        if criteria.max_price:
            filtered = [o for o in filtered if o.price_total <= criteria.max_price]
        
        if criteria.max_stops is not None:
            filtered = [o for o in filtered if o.total_stops <= criteria.max_stops]
        
        return filtered
''')

# 7. Infrastructure
create_file(base / "src" / "flight_ticker" / "infrastructure" / "__init__.py", "")
create_file(base / "src" / "flight_ticker" / "infrastructure" / "config.py", '''"""
Configuração da aplicação
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuração centralizada"""
    
    # API Keys
    TEQUILA_API_KEY = os.getenv("TEQUILA_API_KEY", "")
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
    
    # Defaults
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
    DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "pt-PT")
    
    # Limites
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    @classmethod
    def is_tequila_configured(cls) -> bool:
        return bool(cls.TEQUILA_API_KEY)
    
    @classmethod
    def is_amadeus_configured(cls) -> bool:
        return bool(cls.AMADEUS_CLIENT_ID and cls.AMADEUS_CLIENT_SECRET)
''')

# 8. Providers
create_file(base / "src" / "flight_ticker" / "infrastructure" / "providers" / "__init__.py", "")
create_file(base / "src" / "flight_ticker" / "infrastructure" / "providers" / "kiwi_provider.py", '''"""
Provedor Kiwi/Tequila API
"""
import httpx
from typing import List
from ...domain.models import SearchCriteria, FlightOffer, FlightSegment
from ...application.interfaces import FlightProviderInterface
from ..config import Config


class KiwiTequilaProvider:
    """Provedor de voos via Kiwi/Tequila API"""
    
    name = "Kiwi/Tequila"
    
    def __init__(self, config: Config = Config()):
        self._config = config
        self._base_url = "https://api.tequila.kiwi.com/v2"
    
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca ofertas via Kiwi API"""
        if not self._config.is_tequila_configured():
            return []
        
        offers: List[FlightOffer] = []
        
        async with httpx.AsyncClient(timeout=self._config.REQUEST_TIMEOUT) as client:
            for depart_date in criteria.depart_dates:
                params = self._build_search_params(criteria, depart_date)
                headers = {"apikey": self._config.TEQUILA_API_KEY}
                
                try:
                    response = await client.get(
                        f"{self._base_url}/search",
                        params=params,
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    offers.extend(self._parse_response(data, criteria))
                    
                except Exception as e:
                    # Log error in production
                    continue
        
        return offers
    
    def _build_search_