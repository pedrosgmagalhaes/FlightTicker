"""
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
