"""
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
