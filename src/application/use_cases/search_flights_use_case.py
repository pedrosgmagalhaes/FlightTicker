"""
Search Flights Use Case - Caso de uso principal
"""
from typing import List
from ...domain.entities import SearchCriteria, FlightOffer
from ...domain.interfaces.services import IFlightSearchService, IFlightStrategyService


class SearchFlightsUseCase:
    """Caso de uso para busca de voos"""
    
    def __init__(
        self,
        flight_search_service: IFlightSearchService,
        strategy_service: IFlightStrategyService
    ):
        self.flight_search_service = flight_search_service
        self.strategy_service = strategy_service
    
    async def execute(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str = None,
        adults: int = 1,
        cabin_class: str = None,
        max_stops: int = None,
        carry_on_only: bool = False,
        checked_bag: bool = False,
        max_price: float = None,
        currency: str = None,
        locale: str = None,
        use_ai_ranking: bool = True,
        limit: int = 100,
        flexible_dates: bool = True
    ) -> List[FlightOffer]:
        """Executa busca de voos com parâmetros fornecidos"""
        
        # Expande datas se solicitado
        depart_dates = [depart_date]
        return_dates = None
        
        if flexible_dates:
            depart_dates = self.strategy_service.expand_flexible_dates(depart_date)
            if return_date:
                return_dates = self.strategy_service.expand_flexible_dates(return_date)
        elif return_date:
            return_dates = [return_date]
        
        # Cria critérios de busca
        criteria = SearchCriteria(
            origin=origin,
            destination=destination,
            depart_dates=depart_dates,
            return_dates=return_dates,
            adults=adults,
            cabin_class=cabin_class,
            max_stops=max_stops,
            preferred_currency=currency,
            locale=locale,
            carry_on_only=carry_on_only,
            checked_bag=checked_bag,
            max_price=max_price
        )
        
        # Executa busca
        return await self.flight_search_service.search_best_offers(
            criteria=criteria,
            use_ai_ranking=use_ai_ranking,
            limit=limit
        )