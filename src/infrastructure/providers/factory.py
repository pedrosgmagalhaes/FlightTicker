"""
Provider Factory - Factory Pattern para criação de provedores
"""
from typing import List, Type
from ...domain.interfaces.repositories import IFlightProvider
from .kiwi_provider import KiwiTequilaProvider
from .amadeus_provider import AmadeusProvider


class FlightProviderFactory:
    """Factory para criação de provedores de voo"""
    
    _providers: List[Type[IFlightProvider]] = [
        KiwiTequilaProvider,
        AmadeusProvider,
    ]
    
    @classmethod
    def create_all_available(cls) -> List[IFlightProvider]:
        """Cria todos os provedores disponíveis"""
        providers = []
        for provider_class in cls._providers:
            provider = provider_class()
            if provider.is_available():
                providers.append(provider)
        return providers
    
    @classmethod
    def create_by_name(cls, name: str) -> IFlightProvider:
        """Cria provedor específico por nome"""
        provider_map = {
            "kiwi": KiwiTequilaProvider,
            "tequila": KiwiTequilaProvider,
            "amadeus": AmadeusProvider,
        }
        
        provider_class = provider_map.get(name.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {name}")
        
        provider = provider_class()
        if not provider.is_available():
            raise ValueError(f"Provider {name} is not available (missing credentials)")
        
        return provider
    
    @classmethod
    def register_provider(cls, provider_class: Type[IFlightProvider]):
        """Registra novo provedor"""
        if provider_class not in cls._providers:
            cls._providers.append(provider_class)