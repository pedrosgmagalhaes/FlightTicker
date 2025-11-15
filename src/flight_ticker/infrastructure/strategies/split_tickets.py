"""
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
