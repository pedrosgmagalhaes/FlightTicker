"""
Flight Search Service - Orquestrador principal de busca
"""
import asyncio
from typing import List, Set, Tuple
from ...domain.interfaces.services import IFlightSearchService, IAIRankingService, IFlightStrategyService
from ...domain.entities import FlightOffer, SearchCriteria
from ...infrastructure.providers.factory import FlightProviderFactory


class FlightSearchService(IFlightSearchService):
    """Serviço principal de busca de voos"""
    
    def __init__(
        self,
        ai_ranking_service: IAIRankingService,
        strategy_service: IFlightStrategyService
    ):
        self.ai_ranking_service = ai_ranking_service
        self.strategy_service = strategy_service
        self.provider_factory = FlightProviderFactory()
    
    async def search_best_offers(
        self, 
        criteria: SearchCriteria,
        use_ai_ranking: bool = True,
        limit: int = 100
    ) -> List[FlightOffer]:
        """Busca as melhores ofertas usando múltiplas estratégias"""
        
        all_offers = []
        
        # 1. Busca direta
        direct_offers = await self._search_direct(criteria)
        all_offers.extend(direct_offers)
        
        # 2. Busca com datas flexíveis
        flexible_offers = await self._search_flexible_dates(criteria)
        all_offers.extend(flexible_offers)
        
        # 3. Busca com aeroportos alternativos
        alternative_offers = await self._search_alternative_airports(criteria)
        all_offers.extend(alternative_offers)
        
        # 4. Busca com trechos separados (split tickets)
        split_offers = await self._search_split_tickets(criteria)
        all_offers.extend(split_offers)
        
        # Remove duplicatas
        unique_offers = self._remove_duplicates(all_offers)
        
        # Aplica filtros finais
        filtered_offers = self._apply_filters(unique_offers, criteria)
        
        # Ranqueia usando IA ou preço
        if use_ai_ranking:
            ranked_offers = self.ai_ranking_service.rank_offers(filtered_offers)
        else:
            ranked_offers = sorted(filtered_offers, key=lambda x: x.price_total)
        
        return ranked_offers[:limit]
    
    async def _search_direct(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca direta nos provedores"""
        providers = self.provider_factory.create_all_available()
        
        tasks = []
        for provider in providers:
            tasks.append(self._search_with_provider(provider, criteria))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        offers = []
        for result in results:
            if isinstance(result, list):
                offers.extend(result)
        
        return offers
    
    async def _search_flexible_dates(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca com datas flexíveis"""
        if len(criteria.depart_dates) <= 1:
            return []
        
        offers = []
        
        # Busca para cada data alternativa
        for date in criteria.depart_dates[1:]:  # Pula a primeira (já buscada)
            flexible_criteria = criteria.model_copy(update={"depart_dates": [date]})
            date_offers = await self._search_direct(flexible_criteria)
            offers.extend(date_offers)
        
        return offers
    
    async def _search_alternative_airports(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca com aeroportos alternativos"""
        origin_airports = self.strategy_service.get_nearby_airports(criteria.origin)
        dest_airports = self.strategy_service.get_nearby_airports(criteria.destination)
        
        offers = []
        tasks = []
        
        for origin in origin_airports:
            for destination in dest_airports:
                # Pula combinação original
                if origin == criteria.origin and destination == criteria.destination:
                    continue
                
                alt_criteria = criteria.model_copy(update={
                    "origin": origin,
                    "destination": destination
                })
                tasks.append(self._search_direct(alt_criteria))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    offers.extend(result)
        
        return offers
    
    async def _search_split_tickets(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca com trechos separados via hubs"""
        combinations = self.strategy_service.get_hub_combinations(
            criteria.origin, 
            criteria.destination
        )
        
        # Filtra combinações eficientes
        efficient_combinations = self.strategy_service.filter_efficient_combinations(
            combinations, 
            min_efficiency=0.7
        )
        
        offers = []
        
        # Limita para evitar muitas requisições
        for origin, hub, destination in efficient_combinations[:20]:
            try:
                # Busca primeiro trecho
                first_leg = criteria.model_copy(update={
                    "origin": origin,
                    "destination": hub,
                    "return_dates": None  # Remove retorno para trechos separados
                })
                
                # Busca segundo trecho
                second_leg = criteria.model_copy(update={
                    "origin": hub,
                    "destination": destination,
                    "return_dates": None
                })
                
                first_offers, second_offers = await asyncio.gather(
                    self._search_direct(first_leg),
                    self._search_direct(second_leg),
                    return_exceptions=True
                )
                
                if isinstance(first_offers, list) and isinstance(second_offers, list):
                    combined_offers = self._combine_split_tickets(
                        first_offers, second_offers, criteria
                    )
                    offers.extend(combined_offers)
                    
            except Exception:
                continue
        
        return offers
    
    def _combine_split_tickets(
        self, 
        first_offers: List[FlightOffer],
        second_offers: List[FlightOffer],
        original_criteria: SearchCriteria
    ) -> List[FlightOffer]:
        """Combina ofertas de trechos separados"""
        if not first_offers or not second_offers:
            return []
        
        # Pega as melhores ofertas de cada trecho
        best_first = sorted(first_offers, key=lambda x: x.price_total)[0]
        best_second = sorted(second_offers, key=lambda x: x.price_total)[0]
        
        # Verifica se o preço combinado não excede o máximo
        total_price = best_first.price_total + best_second.price_total
        if original_criteria.max_price and total_price > original_criteria.max_price:
            return []
        
        # Cria oferta combinada
        combined_offer = FlightOffer(
            provider="SplitTickets",
            price_total=total_price,
            currency=best_first.currency,
            baggage_included=best_first.baggage_included and best_second.baggage_included,
            cabin_class=original_criteria.cabin_class,
            segments=best_first.segments + best_second.segments,
            booking_link=None,
            notes="⚠️ Bilhetes separados: Verifique tempo de conexão e políticas de bagagem"
        )
        
        return [combined_offer]
    
    async def _search_with_provider(self, provider, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca com um provedor específico usando context manager"""
        try:
            async with provider:
                return await provider.search(criteria)
        except Exception:
            return []
    
    def _remove_duplicates(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Remove ofertas duplicadas"""
        seen = set()
        unique = []
        
        for offer in offers:
            # Cria assinatura única baseada em rota e preço
            signature = (
                offer.provider,
                offer.route_summary,
                round(offer.price_total, 2),
                offer.currency
            )
            
            if signature not in seen:
                seen.add(signature)
                unique.append(offer)
        
        return unique
    
    def _apply_filters(
        self, 
        offers: List[FlightOffer], 
        criteria: SearchCriteria
    ) -> List[FlightOffer]:
        """Aplica filtros finais"""
        filtered = []
        
        for offer in offers:
            # Filtro de paradas máximas
            if criteria.max_stops is not None and offer.total_stops > criteria.max_stops:
                continue
            
            # Filtro de preço máximo
            if criteria.max_price and offer.price_total > criteria.max_price:
                continue
            
            filtered.append(offer)
        
        return filtered