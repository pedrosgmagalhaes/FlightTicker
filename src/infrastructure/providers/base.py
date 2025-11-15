"""
Base Provider - Template Method Pattern
"""
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ...domain.interfaces.repositories import IFlightProvider
from ...domain.entities import FlightOffer, SearchCriteria
from ..config.settings import settings


class BaseFlightProvider(IFlightProvider, ABC):
    """Classe base para provedores de voo usando Template Method Pattern"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Template method para busca de voos"""
        if not self.is_available():
            return []
        
        try:
            # Template method steps
            params = self._build_search_params(criteria)
            headers = self._build_headers()
            raw_data = await self._make_request(params, headers)
            return self._parse_response(raw_data, criteria)
        except Exception as e:
            if settings.debug:
                print(f"Error in {self.name}: {e}")
            return []
    
    @abstractmethod
    def _build_search_params(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Constrói parâmetros específicos do provedor"""
        pass
    
    @abstractmethod
    def _build_headers(self) -> Dict[str, str]:
        """Constrói headers específicos do provedor"""
        pass
    
    @abstractmethod
    async def _make_request(
        self, 
        params: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Faz a requisição HTTP"""
        pass
    
    @abstractmethod
    def _parse_response(
        self, 
        raw_data: Dict[str, Any], 
        criteria: SearchCriteria
    ) -> List[FlightOffer]:
        """Parseia a resposta para FlightOffer"""
        pass
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Getter para o cliente HTTP"""
        if self._client is None:
            raise RuntimeError("Provider not initialized. Use async context manager.")
        return self._client