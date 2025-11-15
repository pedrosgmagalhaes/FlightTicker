"""
Repository Interfaces - Contratos para acesso a dados
"""
from abc import ABC, abstractmethod
from typing import List
from ..entities import FlightOffer, SearchCriteria


class IFlightRepository(ABC):
    """Interface para repositório de voos"""
    
    @abstractmethod
    async def search_flights(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca voos baseado nos critérios"""
        pass


class IFlightProvider(ABC):
    """Interface para provedores de voos"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do provedor"""
        pass
    
    @abstractmethod
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca voos no provedor específico"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provedor está disponível"""
        pass