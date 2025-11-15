"""
Service Interfaces - Contratos para serviços de domínio
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from ..entities import FlightOffer, SearchCriteria


class IFlightSearchService(ABC):
    """Interface para serviço de busca de voos"""
    
    @abstractmethod
    async def search_best_offers(
        self, 
        criteria: SearchCriteria,
        use_ai_ranking: bool = True,
        limit: int = 100
    ) -> List[FlightOffer]:
        """Busca as melhores ofertas de voo"""
        pass


class IAIRankingService(ABC):
    """Interface para serviço de ranqueamento por IA"""
    
    @abstractmethod
    def rank_offers(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Ranqueia ofertas usando IA"""
        pass
    
    @abstractmethod
    def score_offer(
        self, 
        offer: FlightOffer, 
        reference_price: float = None
    ) -> Tuple[float, str]:
        """Calcula score e explicação para uma oferta"""
        pass


class IFlightStrategyService(ABC):
    """Interface para estratégias de busca"""
    
    @abstractmethod
    def expand_flexible_dates(
        self, 
        base_date: str, 
        days_before: int = 3, 
        days_after: int = 3
    ) -> List[str]:
        """Expande datas flexíveis"""
        pass
    
    @abstractmethod
    def get_nearby_airports(self, iata: str) -> List[str]:
        """Obtém aeroportos próximos"""
        pass
    
    @abstractmethod
    def get_hub_combinations(
        self, 
        origin: str, 
        destination: str
    ) -> List[Tuple[str, str, str]]:
        """Obtém combinações via hubs"""
        pass