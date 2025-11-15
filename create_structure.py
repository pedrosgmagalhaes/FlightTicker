#!/usr/bin/env python3
"""
Script para criar toda a estrutura do projeto FlightTicker
com design patterns e clean code
"""
import os
from pathlib import Path

def create_file(path: str, content: str):
    """Cria um arquivo com o conteúdo especificado"""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ Criado: {path}")

def main():
    base_dir = Path(__file__).parent
    
    # 1. Arquivos de configuração raiz
    create_file(base_dir / "requirements.txt", """httpx==0.27.0
pydantic==2.9.2
python-dotenv==1.0.1
rich==13.9.2
numpy==1.26.4""")

    create_file(base_dir / ".env.example", """# Copie para .env e preencha com suas chaves reais:
TEQUILA_API_KEY=coloque_sua_chave_tequila_aqui

AMADEUS_CLIENT_ID=coloque_seu_client_id_aqui
AMADEUS_CLIENT_SECRET=coloque_seu_client_secret_aqui

# Preferências
DEFAULT_CURRENCY=EUR
DEFAULT_LOCALE=pt-PT""")

    create_file(base_dir / ".gitignore", """.env
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

    # 2. Estrutura de pacotes
    create_file(base_dir / "src" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "__init__.py", "")
    
    # 3. Core - Domain Models (Clean Architecture)
    create_file(base_dir / "src" / "flight_ticker" / "domain" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "domain" / "models.py", '''"""
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

    # 4. Application Services (Use Cases)
    create_file(base_dir / "src" / "flight_ticker" / "application" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "application" / "interfaces.py", '''"""
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

    create_file(base_dir / "src" / "flight_ticker" / "application" / "services.py", '''"""
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

    # 5. Infrastructure - Providers
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "config.py", '''"""
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

    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "providers" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "providers" / "kiwi_provider.py", '''"""
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
    
    def _build_search_params(self, criteria: SearchCriteria, depart_date: str) -> dict:
        """Constrói parâmetros da requisição"""
        params = {
            "fly_from": criteria.origin,
            "fly_to": criteria.destination,
            "date_from": depart_date,
            "date_to": depart_date,
            "curr": criteria.preferred_currency or self._config.DEFAULT_CURRENCY,
            "locale": criteria.locale or self._config.DEFAULT_LOCALE,
            "adults": criteria.adults,
            "selected_cabins": self._map_cabin_class(criteria.cabin_class),
            "max_stopovers": criteria.max_stops if criteria.max_stops is not None else 10,
            "carry_on": 1 if criteria.carry_on_only else 0,
            "hold_bag": 1 if criteria.checked_bag else 0,
            "limit": 50,
            "sort": "price",
        }
        
        if criteria.return_dates:
            params["return_from"] = criteria.return_dates[0]
            params["return_to"] = criteria.return_dates[0]
        
        return params
    
    def _map_cabin_class(self, cabin_class: str | None) -> str:
        """Mapeia classe de cabine para formato Kiwi"""
        mapping = {
            "ECONOMY": "M",
            "PREMIUM_ECONOMY": "W", 
            "BUSINESS": "C",
            "FIRST": "F"
        }
        return mapping.get(cabin_class or "ECONOMY", "M")
    
    def _parse_response(self, data: dict, criteria: SearchCriteria) -> List[FlightOffer]:
        """Converte resposta da API em ofertas"""
        offers = []
        
        for item in data.get("data", []):
            try:
                price = float(item.get("price", 0.0))
                
                if criteria.max_price and price > criteria.max_price:
                    continue
                
                segments = []
                for route in item.get("route", []):
                    segments.append(FlightSegment(
                        origin=route.get("flyFrom"),
                        destination=route.get("flyTo"),
                        departure=route.get("local_departure"),
                        arrival=route.get("local_arrival"),
                        marketing_carrier=route.get("operating_carrier") or route.get("airline"),
                        flight_number=route.get("operating_flight_no") or route.get("flight_no"),
                    ))
                
                offers.append(FlightOffer(
                    provider=self.name,
                    price_total=price,
                    currency=item.get("currency", criteria.preferred_currency or self._config.DEFAULT_CURRENCY),
                    baggage_included=not bool(item.get("bags_price", {})),
                    cabin_class=criteria.cabin_class or "ECONOMY",
                    segments=segments,
                    booking_link=item.get("deep_link"),
                    refundable=item.get("refundable"),
                    changeable=item.get("change_penalty") is not None,
                ))
                
            except Exception:
                continue
        
        return offers
''')

    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "providers" / "amadeus_provider.py", '''"""
Provedor Amadeus API
"""
import httpx
from typing import List, Optional
from ...domain.models import SearchCriteria, FlightOffer, FlightSegment
from ...application.interfaces import FlightProviderInterface
from ..config import Config


class AmadeusProvider:
    """Provedor de voos via Amadeus API"""
    
    name = "Amadeus"
    
    def __init__(self, config: Config = Config()):
        self._config = config
        self._base_url = "https://test.api.amadeus.com"
        self._token_cache: Optional[str] = None
    
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca ofertas via Amadeus API"""
        if not self._config.is_amadeus_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        # Simplificação: usa apenas primeira data
        depart_date = criteria.depart_dates[0]
        return_date = criteria.return_dates[0] if criteria.return_dates else None
        
        params = self._build_search_params(criteria, depart_date, return_date)
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=self._config.REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(
                    f"{self._base_url}/v2/shopping/flight-offers",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data, criteria)
                
            except Exception:
                return []
    
    async def _get_access_token(self) -> Optional[str]:
        """Obtém token de acesso OAuth2"""
        if self._token_cache:
            return self._token_cache
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._config.AMADEUS_CLIENT_ID,
                        "client_secret": self._config.AMADEUS_CLIENT_SECRET,
                    }
                )
                response.raise_for_status()
                token = response.json().get("access_token")
                self._token_cache = token
                return token
                
            except Exception:
                return None
    
    def _build_search_params(self, criteria: SearchCriteria, depart_date: str, return_date: Optional[str]) -> dict:
        """Constrói parâmetros da requisição"""
        params = {
            "originLocationCode": criteria.origin,
            "destinationLocationCode": criteria.destination,
            "departureDate": depart_date,
            "adults": criteria.adults,
            "nonStop": criteria.max_stops == 0 if criteria.max_stops is not None else False,
            "currencyCode": criteria.preferred_currency or self._config.DEFAULT_CURRENCY,
        }
        
        if return_date:
            params["returnDate"] = return_date
        
        if criteria.cabin_class:
            params["travelClass"] = criteria.cabin_class
        
        return params
    
    def _parse_response(self, data: dict, criteria: SearchCriteria) -> List[FlightOffer]:
        """Converte resposta da API em ofertas"""
        offers = []
        
        for offer_data in data.get("data", []):
            try:
                price_info = offer_data.get("price", {})
                price = float(price_info.get("grandTotal", price_info.get("total", 0.0)))
                
                if criteria.max_price and price > criteria.max_price:
                    continue
                
                segments = []
                for itinerary in offer_data.get("itineraries", []):
                    for segment_data in itinerary.get("segments", []):
                        segments.append(FlightSegment(
                            origin=segment_data["departure"]["iataCode"],
                            destination=segment_data["arrival"]["iataCode"],
                            departure=segment_data["departure"]["at"],
                            arrival=segment_data["arrival"]["at"],
                            marketing_carrier=segment_data.get("carrierCode"),
                            flight_number=segment_data.get("number"),
                        ))
                
                offers.append(FlightOffer(
                    provider=self.name,
                    price_total=price,
                    currency=price_info.get("currency", criteria.preferred_currency or self._config.DEFAULT_CURRENCY),
                    baggage_included=False,  # Seria necessário analisar travelerPricings
                    cabin_class=criteria.cabin_class,
                    segments=segments,
                    booking_link=None,  # Amadeus não fornece link direto
                ))
                
            except Exception:
                continue
        
        return offers
''')

    # 6. AI/Scoring Service
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "ai" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "ai" / "scoring_service.py", '''"""
Serviço de pontuação inteligente de ofertas
"""
import numpy as np
from typing import List, Tuple
from ...domain.models import FlightOffer
from ...application.interfaces import ScoringServiceInterface


class AIFlightScoringService(ScoringServiceInterface):
    """Serviço de pontuação usando heurísticas inteligentes"""
    
    def score_offers(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Pontua e ordena ofertas por valor geral"""
        if not offers:
            return offers
        
        # Calcula preço de referência (mediana)
        prices = [o.price_total for o in offers]
        reference_price = float(np.median(prices))
        
        # Pontua cada oferta
        scored_offers = []
        for offer in offers:
            score, explanation = self._calculate_score(offer, reference_price)
            offer.ai_score = score
            offer.ai_explanation = explanation
            scored_offers.append(offer)
        
        # Ordena por score (maior primeiro) e desempata por preço (menor primeiro)
        return sorted(
            scored_offers,
            key=lambda x: (-x.ai_score if x.ai_score else 0.0, x.price_total)
        )
    
    def _calculate_score(self, offer: FlightOffer, reference_price: float) -> Tuple[float, str]:
        """Calcula score individual da oferta"""
        
        # 1. Fator preço (melhor se menor que referência)
        price_factor = reference_price / max(offer.price_total, 1e-6)
        price_factor = min(price_factor, 2.0)  # Cap em 2x
        
        # 2. Penalidade por paradas
        stops_penalty = 1.0 / (1.0 + 0.4 * offer.total_stops)
        
        # 3. Bônus bagagem incluída
        baggage_bonus = 1.1 if offer.baggage_included else 1.0
        
        # 4. Fator classe de cabine
        cabin_factor = self._get_cabin_factor(offer.cabin_class)
        
        # 5. Penalidade por muitos segmentos (complexidade)
        complexity_penalty = 1.0 / (1.0 + 0.1 * max(0, len(offer.segments) - 2))
        
        # Score final
        raw_score = (
            price_factor * 
            stops_penalty * 
            baggage_bonus * 
            cabin_factor * 
            complexity_penalty
        )
        
        # Normaliza para 0-100
        score = float(np.clip(raw_score * 35.0, 0.0, 100.0))
        
        # Explicação
        explanation = self._build_explanation(offer, score)
        
        return score, explanation
    
    def _get_cabin_factor(self, cabin_class: str | None) -> float:
        """Fator baseado na classe de cabine"""
        if not cabin_class:
            return 1.0
        
        factors = {
            "ECONOMY": 1.05,        # Leve bônus para economia
            "PREMIUM_ECONOMY": 0.98, # Leve penalidade (mais caro)
            "BUSINESS": 0.90,       # Penalidade maior
            "FIRST": 0.85,          # Maior penalidade
        }
        
        return factors.get(cabin_class.upper(), 1.0)
    
    def _build_explanation(self, offer: FlightOffer, score: float) -> str:
        """Constrói explicação do score"""
        parts = [
            f"Preço: {offer.currency} {offer.price_total:.2f}",
            f"Paradas: {offer.total_stops}",
            f"Bagagem: {'incluída' if offer.baggage_included else 'não incluída'}",
            f"Classe: {offer.cabin_class or 'ECONOMY'}",
            f"Score: {score:.1f}/100"
        ]
        
        return " | ".join(parts)
''')

    # 7. Strategies
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "strategies" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "strategies" / "flexible_dates.py", '''"""
Estratégia de datas flexíveis
"""
from typing import List, Set
from datetime import datetime, timedelta
from ...domain.models import SearchCriteria, FlightOffer
from ...application.interfaces import SearchStrategyInterface, FlightProviderInterface


class FlexibleDatesStrategy(SearchStrategyInterface):
    """Estratégia que expande datas para encontrar melhores preços"""
    
    def __init__(self, providers: List[FlightProviderInterface], days_range: int = 3):
        self._providers = providers
        self._days_range = days_range
    
    async def execute(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Executa busca com datas flexíveis"""
        # Expande datas
        expanded_criteria = criteria.model_copy()
        expanded_criteria.depart_dates = self._expand_dates(criteria.depart_dates[0])
        
        if criteria.return_dates:
            expanded_criteria.return_dates = self._expand_dates(criteria.return_dates[0])
        
        # Busca em todos os provedores
        all_offers = []
        for provider in self._providers:
            offers = await provider.search(expanded_criteria)
            all_offers.extend(offers)
        
        return all_offers
    
    def _expand_dates(self, base_date: str) -> List[str]:
        """Expande uma data base em um range"""
        dt = datetime.strptime(base_date, "%Y-%m-%d")
        dates = []
        
        for delta in range(-self._days_range, self._days_range + 1):
            new_date = dt + timedelta(days=delta)
            dates.append(new_date.strftime("%Y-%m-%d"))
        
        return sorted(set(dates))
''')

    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "strategies" / "alternative_airports.py", '''"""
Estratégia de aeroportos alternativos
"""
import asyncio
from typing import List, Set, Dict
from ...domain.models import SearchCriteria, FlightOffer
from ...application.interfaces import SearchStrategyInterface, FlightProviderInterface


class AlternativeAirportsStrategy(SearchStrategyInterface):
    """Estratégia que busca em aeroportos alternativos"""
    
    # Mapeamento de grupos de aeroportos
    AIRPORT_GROUPS: Dict[str, Set[str]] = {
        "SAO": {"GRU", "CGH", "VCP"},  # São Paulo
        "RIO": {"GIG", "SDU"},         # Rio de Janeiro
        "LON": {"LHR", "LGW", "STN", "LTN", "LCY", "SEN"},  # Londres
        "PAR": {"CDG", "ORY", "BVA"},  # Paris
        "NYC": {"JFK", "EWR", "LGA"},  # Nova York
        "MIL": {"MXP", "LIN", "BGY"},  # Milão
        "ROM": {"FCO", "CIA"},         # Roma
        "BER": {"BER", "SXF", "TXL"},  # Berlim
    }
    
    def __init__(self, providers: List[FlightProviderInterface]):
        self._providers = providers
    
    async def execute(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Executa busca com aeroportos alternativos"""
        origin_airports = self._get_alternative_airports(criteria.origin)
        destination_airports = self._get_alternative_airports(criteria.destination)
        
        # Cria combinações de busca
        search_tasks = []
        for origin in origin_airports:
            for destination in destination_airports:
                # Pula combinação original (já será buscada por outra estratégia)
                if origin == criteria.origin and destination == criteria.destination:
                    continue
                
                alt_criteria = criteria.model_copy()
                alt_criteria.origin = origin
                alt_criteria.destination = destination
                
                for provider in self._providers:
                    search_tasks.append(provider.search(alt_criteria))
        
        # Executa buscas em paralelo
        if not search_tasks:
            return []
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Coleta ofertas válidas
        all_offers = []
        for result in results:
            if isinstance(result, list):
                all_offers.extend(result)
        
        return all_offers
    
    def _get_alternative_airports(self, airport_code: str) -> Set[str]:
        """Obtém aeroportos alternativos para um código"""
        # Verifica se é um grupo conhecido
        if airport_code in self.AIRPORT_GROUPS:
            return self.AIRPORT_GROUPS[airport_code]
        
        # Verifica se o código está em algum grupo
        for group_code, airports in self.AIRPORT_GROUPS.items():
            if airport_code in airports:
                return airports
        
        # Se não encontrou, retorna apenas o próprio aeroporto
        return {airport_code}
''')

    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "strategies" / "split_tickets.py", '''"""
Estratégia de bilhetes separados via hubs
"""
import asyncio
from typing import List, Set, Tuple
from ...domain.models import SearchCriteria, FlightOffer, FlightSegment
from ...application.interfaces import SearchStrategyInterface, FlightProviderInterface


class SplitTicketsStrategy(SearchStrategyInterface):
    """Estratégia que busca bilhetes separados via hubs principais"""
    
    # Principais hubs internacionais
    MAJOR_HUBS = {
        "LIS", "MAD", "IST", "CDG", "FRA", "LHR", "AMS", 
        "DOH", "DXB", "MUC", "ZRH", "BCN", "FCO", "ATH",
        "VIE", "CPH", "ARN", "HEL", "WAW"
    }
    
    def __init__(self, providers: List[FlightProviderInterface], max_combinations: int = 20):
        self._providers = providers
        self._max_combinations = max_combinations
    
    async def execute(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Executa busca com bilhetes separados"""
        if criteria.is_round_trip():
            # Para ida e volta, a lógica seria mais complexa
            return []
        
        # Gera combinações de hub
        hub_combinations = self._generate_hub_combinations(criteria.origin, criteria.destination)
        
        # Limita combinações para evitar explosão
        limited_combinations = list(hub_combinations)[:self._max_combinations]
        
        # Busca cada combinação
        split_offers = []
        for origin, hub, destination in limited_combinations:
            offers = await self._search_split_route(criteria, origin, hub, destination)
            split_offers.extend(offers)
        
        return split_offers
    
    def _generate_hub_combinations(self, origin: str, destination: str) -> Set[Tuple[str, str, str]]:
        """Gera combinações de origem -> hub -> destino"""
        combinations = set()
        
        for hub in self.MAJOR_HUBS:
            if hub != origin and hub != destination:
                combinations.add((origin, hub, destination))
        
        return combinations
    
    async def _search_split_route(
        self, 
        original_criteria: SearchCriteria, 
        origin: str, 
        hub: str, 
        destination: str
    ) -> List[FlightOffer]:
        """Busca uma rota específica dividida em dois trechos"""
        
        # Usa apenas a primeira data para simplificar
        depart_date = original_criteria.depart_dates[0]
        
        # Critérios para primeiro trecho (origem -> hub)
        first_leg_criteria = original_criteria.model_copy()
        first_leg_criteria.origin = origin
        first_leg_criteria.destination = hub
        first_leg_criteria.depart_dates = [depart_date]
        first_leg_criteria.return_dates = None
        
        # Critérios para segundo trecho (hub -> destino)
        second_leg_criteria = original_criteria.model_copy()
        second_leg_criteria.origin = hub
        second_leg_criteria.destination = destination
        second_leg_criteria.depart_dates = [depart_date]  # Simplificação: mesma data
        second_leg_criteria.return_dates = None
        
        # Busca ambos os trechos em paralelo
        first_leg_tasks = [provider.search(first_leg_criteria) for provider in self._providers]
        second_leg_tasks = [provider.search(second_leg_criteria) for provider in self._providers]
        
        all_tasks = first_leg_tasks + second_leg_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Separa resultados
        first_leg_results = results[:len(first_leg_tasks)]
        second_leg_results = results[len(first_leg_tasks):]
        
        # Coleta ofertas válidas
        first_leg_offers = []
        for result in first_leg_results:
            if isinstance(result, list):
                first_leg_offers.extend(result)
        
        second_leg_offers = []
        for result in second_leg_results:
            if isinstance(result, list):
                second_leg_offers.extend(result)
        
        # Combina melhores ofertas de cada trecho
        return self._combine_legs(first_leg_offers, second_leg_offers, original_criteria)
    
    def _combine_legs(
        self, 
        first_leg: List[FlightOffer], 
        second_leg: List[FlightOffer],
        original_criteria: SearchCriteria
    ) -> List[FlightOffer]:
        """Combina ofertas de dois trechos em ofertas split"""
        if not first_leg or not second_leg:
            return []
        
        # Pega as melhores ofertas de cada trecho (por preço)
        best_first = min(first_leg, key=lambda x: x.price_total)
        best_second = min(second_leg, key=lambda x: x.price_total)
        
        # Calcula preço total
        total_price = best_first.price_total + best_second.price_total
        
        # Verifica se está dentro do limite de preço
        if original_criteria.max_price and total_price > original_criteria.max_price:
            return []
        
        # Combina segmentos
        combined_segments = best_first.segments + best_second.segments
        
        # Cria oferta combinada
        combined_offer = FlightOffer(
            provider="SplitTickets",
            price_total=total_price,
            currency=best_first.currency,
            baggage_included=best_first.baggage_included and best_second.baggage_included,
            cabin_class=original_criteria.cabin_class,
            segments=combined_segments,
            booking_link=None,
            notes="⚠️ BILHETES SEPARADOS: Verifique tempo de conexão e regras de bagagem. Risco de perda de conexão.",
        )
        
        return [combined_offer]
''')

    # 8. Factory para criar o serviço
    create_file(base_dir / "src" / "flight_ticker" / "infrastructure" / "factory.py", '''"""
Factory para criar instâncias configuradas dos serviços
"""
from typing import List
from .config import Config
from .providers.kiwi_provider import KiwiTequilaProvider
from .providers.amadeus_provider import AmadeusProvider
from .ai.scoring_service import AIFlightScoringService
from .strategies.flexible_dates import FlexibleDatesStrategy
from .strategies.alternative_airports import AlternativeAirportsStrategy
from .strategies.split_tickets import SplitTicketsStrategy
from ..application.services import FlightSearchService
from ..application.interfaces import FlightProviderInterface, ScoringServiceInterface, SearchStrategyInterface


class FlightSearchServiceFactory:
    """Factory para criar o serviço de busca configurado"""
    
    @staticmethod
    def create(config: Config = None) -> FlightSearchService:
        """Cria uma instância completa do serviço de busca"""
        if config is None:
            config = Config()
        
        # Cria provedores
        providers = FlightSearchServiceFactory._create_providers(config)
        
        # Cria serviço de pontuação
        scoring_service = FlightSearchServiceFactory._create_scoring_service()
        
        # Cria estratégias
        strategies = FlightSearchServiceFactory._create_strategies(providers)
        
        return FlightSearchService(
            providers=providers,
            scoring_service=scoring_service,
            strategies=strategies
        )
    
    @staticmethod
    def _create_providers(config: Config) -> List[FlightProviderInterface]:
        """Cria lista de provedores disponíveis"""
        providers = []
        
        if config.is_tequila_configured():
            providers.append(KiwiTequilaProvider(config))
        
        if config.is_amadeus_configured():
            providers.append(AmadeusProvider(config))
        
        return providers
    
    @staticmethod
    def _create_scoring_service() -> ScoringServiceInterface:
        """Cria serviço de pontuação"""
        return AIFlightScoringService()
    
    @staticmethod
    def _create_strategies(providers: List[FlightProviderInterface]) -> List[SearchStrategyInterface]:
        """Cria lista de estratégias de busca"""
        if not providers:
            return []
        
        return [
            FlexibleDatesStrategy(providers, days_range=3),
            AlternativeAirportsStrategy(providers),
            SplitTicketsStrategy(providers, max_combinations=15),
        ]
''')

    # 9. Interface CLI atualizada
    create_file(base_dir / "src" / "flight_ticker" / "presentation" / "__init__.py", "")
    create_file(base_dir / "src" / "flight_ticker" / "presentation" / "cli.py", '''"""
Interface de linha de comando
"""
import asyncio
import argparse
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..domain.models import SearchCriteria
from ..infrastructure.factory import FlightSearchServiceFactory


class FlightTickerCLI:
    """Interface CLI para o FlightTicker"""
    
    def __init__(self):
        self.console = Console()
        self.search_service = FlightSearchServiceFactory.create()
    
    def run(self):
        """Executa a interface CLI"""
        args = self._parse_arguments()
        
        # Cria critérios de busca
        criteria = self._build_search_criteria(args)
        
        # Executa busca com progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Buscando melhores ofertas...", total=None)
            
            result = asyncio.run(self.search_service.search(criteria))
            
            progress.update(task, description="Busca concluída!")
        
        # Exibe resultados
        self._display_results(result, args.no_ai)
    
    def _parse_arguments(self) -> argparse.Namespace:
        """Configura e processa argumentos da linha de comando"""
        parser = argparse.ArgumentParser(
            description="FlightTicker - Busca inteligente de passagens aéreas",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos de uso:
  python -m src.main --origin SAO --destination NYC --depart 2025-02-15
  python -m src.main --origin LON --destination PAR --depart 2025-01-10 --return 2025-01-15 --carry-on-only
  python -m src.main --origin RIO --destination LIS --depart 2025-03-20 --max-price 2000 --no-ai
            """
        )
        
        # Argumentos obrigatórios
        parser.add_argument("--origin", required=True, 
                          help="Código IATA origem ou grupo (ex: SAO, RIO, LON)")
        parser.add_argument("--destination", required=True,
                          help="Código IATA destino ou grupo (ex: PAR, NYC)")
        parser.add_argument("--depart", required=True,
                          help="Data partida YYYY-MM-DD")
        
        # Argumentos opcionais
        parser.add_argument("--return", dest="return_date",
                          help="Data retorno YYYY-MM-DD (para ida e volta)")
        parser.add_argument("--adults", type=int, default=1,
                          help="Número de adultos (padrão: 1)")
        parser.add_argument("--cabin", 
                          choices=["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                          help="Classe de cabine")
        parser.add_argument("--max-stops", type=int,
                          help="Número máximo de paradas")
        parser.add_argument("--carry-on-only", action="store_true",
                          help="Apenas bagagem de mão")
        parser.add_argument("--checked-bag", action="store_true",
                          help="Incluir bagagem despachada")
        parser.add_argument("--max-price", type=float,
                          help="Preço máximo")
        parser.add_argument("--currency", 
                          help="Moeda preferida (ex: EUR, USD, BRL)")
        parser.add_argument("--locale",
                          help="Locale (ex: pt-PT, en-US)")
        parser.add_argument("--no-ai", action="store_true",
                          help="Desativa ranqueamento por IA (ordena apenas por preço)")
        parser.add_argument("--limit", type=int, default=20,
                          help="Limite de ofertas exibidas (padrão: 20)")
        
        return parser.parse_args()
    
    def _build_search_criteria(self, args: argparse.Namespace) -> SearchCriteria:
        """Constrói critérios de busca a partir dos argumentos"""
        return SearchCriteria(
            origin=args.origin.upper(),
            destination=args.destination.upper(),
            depart_dates=[args.depart],
            return_dates=[args.return_date] if args.return_date else None,
            adults=args.adults,
            cabin_class=args.cabin,
            max_stops=args.max_stops,
            preferred_currency=args.currency,
            locale=args.locale,
            carry_on_only=args.carry_on_only,
            checked_bag=args.checked_bag,
            max_price=args.max_price,
        )
    
    def _display_results(self, result, no_ai: bool):
        """Exibe resultados da busca"""
        if not result.offers:
            self.console.print(
                Panel.fit(
                    "[yellow]Nenhuma oferta encontrada dentro dos critérios especificados.[/yellow]\\n"
                    "Tente ajustar os filtros ou verificar se as chaves de API estão configuradas.",
                    title="Sem Resultados",
                    border_style="yellow"
                )
            )
            return
        
        # Limita resultados exibidos
        limited_offers = result.offers[:20]  # Máximo 20 para não poluir
        
        # Cria tabela
        table = Table(show_lines=True, title=f"🛫 Melhores Ofertas Encontradas ({len(limited_offers)} de {result.total_found})")
        
        table.add_column("Provedor", style="bold cyan", width=12)
        table.add_column("Preço", style="bold green", justify="right", width=10)
        table.add_column("Rota", style="yellow", width=20)
        table.add_column("Paradas", justify="center", width=8)
        table.add_column("Classe", width=10)
        
        if not no_ai:
            table.add_column("Score IA", justify="center", width=8)
        
        table.add_column("Observações", width=30)
        
        # Adiciona linhas
        for offer in limited_offers:
            row = [
                offer.provider,
                f"{offer.currency} {offer.price_total:.2f}",
                offer.route_summary,
                str(offer.total_stops),
                offer.cabin_class or "ECONOMY",
            ]
            
            if not no_ai:
                score_text = f"{offer.ai_score:.1f}/100" if offer.ai_score else "N/A"
                row.append(score_text)
            
            # Observações
            notes = []
            if offer.baggage_included:
                notes.append("✅ Bagagem")
            if offer.booking_link:
                notes.append("🔗 Link")
            if offer.notes:
                notes.append(offer.notes[:25] + "..." if len(offer.notes) > 25 else offer.notes)
            
            row.append(" | ".join(notes) if notes else "-")
            
            table.add_row(*row)
        
        self.console.print(table)
        
        # Estatísticas
        if result.best_offer and result.cheapest_offer:
            stats_text = f"""
📊 **Estatísticas da Busca:**
• Total encontrado: {result.total_found} ofertas
• Melhor por IA: {result.best_offer.currency} {result.best_offer.price_total:.2f} ({result.best_offer.provider})
• Mais barato: {result.cheapest_offer.currency} {result.cheapest_offer.price_total:.2f} ({result.cheapest_offer.provider})
• Busca realizada: {result.search_timestamp.strftime('%d/%m/%Y %H:%M')}
            """
            
            self.console.print(Panel.fit(stats_text.strip(), title="Resumo", border_style="blue"))


def main():
    """Função principal"""
    cli = FlightTickerCLI()
    cli.run()


if __name__ == "__main__":
    main()
''')

    # 10. Atualiza main.py
    create_file(base_dir / "src" / "main.py", '''"""
Ponto de entrada principal do FlightTicker
"""
from flight_ticker.presentation.cli import main

if __name__ == "__main__":
    main()
''')

    print("\n🎉 Estrutura do projeto criada com sucesso!")
    print("\n📁 Estrutura criada:")
    print("""
FlightTicker/
├── requirements.txt
├── .env.example  
├── .gitignore
└── src/
    ├── main.py
    └── flight_ticker/
        ├── domain/
        │   └── models.py
        ├── application/
        │   ├── interfaces.py
        │   └── services.py
        ├── infrastructure/
        │   ├── config.py
        │   ├── factory.py
        │   ├── providers/
        │   │   ├── kiwi_provider.py
        │   │   └── amadeus_provider.py
        │   ├── ai/
        │   │   └── scoring_service.py
        │   └── strategies/
        │       ├── flexible_dates.py
        │       ├── alternative_airports.py
        │       └── split_tickets.py
        └── presentation/
            └── cli.py
    """)
    
    print("\n🚀 Próximos passos:")
    print("1. pip install -r requirements.txt")
    print("2. cp .env.example .env")
    print("3. Edite .env com suas chaves de API")
    print("4. python -m src.main --origin SAO --destination NYC --depart 2025-02-15")

if __name__ == "__main__":
    main()