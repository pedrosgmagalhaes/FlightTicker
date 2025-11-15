"""
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
