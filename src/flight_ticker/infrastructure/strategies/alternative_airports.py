"""
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
