"""
Factory para criar instâncias configuradas dos serviços
"""
from typing import List
from .config import Config
from .providers.kiwi_provider import KiwiTequilaProvider
from .providers.amadeus_provider import AmadeusProvider
from .ai.scoring_service import AIFlightScoringService
from .strategies.flexible_dates import FlexibleDatesStrategy
from .strategies.alternative_airports import AlternativeAirportsStrategy
from .strategies.split_tickets import SplitTicketsStrategy
from ..application.services import FlightSearchService
from ..application.interfaces import FlightProviderInterface, ScoringServiceInterface, SearchStrategyInterface


class FlightSearchServiceFactory:
    """Factory para criar o serviço de busca configurado"""
    
    @staticmethod
    def create(config: Config = None) -> FlightSearchService:
        """Cria uma instância completa do serviço de busca"""
        if config is None:
            config = Config()
        
        # Cria provedores
        providers = FlightSearchServiceFactory._create_providers(config)
        
        # Cria serviço de pontuação
        scoring_service = FlightSearchServiceFactory._create_scoring_service()
        
        # Cria estratégias
        strategies = FlightSearchServiceFactory._create_strategies(providers)
        
        return FlightSearchService(
            providers=providers,
            scoring_service=scoring_service,
            strategies=strategies
        )
    
    @staticmethod
    def _create_providers(config: Config) -> List[FlightProviderInterface]:
        """Cria lista de provedores disponíveis"""
        providers = []
        
        if config.is_tequila_configured():
            providers.append(KiwiTequilaProvider(config))
        
        if config.is_amadeus_configured():
            providers.append(AmadeusProvider(config))
        
        return providers
    
    @staticmethod
    def _create_scoring_service() -> ScoringServiceInterface:
        """Cria serviço de pontuação"""
        return AIFlightScoringService()
    
    @staticmethod
    def _create_strategies(providers: List[FlightProviderInterface]) -> List[SearchStrategyInterface]:
        """Cria lista de estratégias de busca"""
        if not providers:
            return []
        
        return [
            FlexibleDatesStrategy(providers, days_range=3),
            AlternativeAirportsStrategy(providers),
            SplitTicketsStrategy(providers, max_combinations=15),
        ]
