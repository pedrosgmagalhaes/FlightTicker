"""
Kiwi/Tequila Provider Implementation
"""
from typing import List, Dict, Any
from ...domain.entities import FlightOffer, FlightSegment, SearchCriteria
from ..config.settings import settings
from .base import BaseFlightProvider


class KiwiTequilaProvider(BaseFlightProvider):
    """Implementação do provedor Kiwi/Tequila"""
    
    @property
    def name(self) -> str:
        return "Kiwi/Tequila"
    
    def is_available(self) -> bool:
        return settings.has_tequila_credentials
    
    def _build_search_params(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Constrói parâmetros para API Tequila"""
        params = {
            "fly_from": criteria.origin,
            "fly_to": criteria.destination,
            "date_from": criteria.depart_dates[0],
            "date_to": criteria.depart_dates[0],
            "curr": criteria.preferred_currency or settings.default_currency,
            "locale": criteria.locale or settings.default_locale,
            "adults": criteria.adults,
            "selected_cabins": self._map_cabin_class(criteria.cabin_class),
            "max_stopovers": criteria.max_stops if criteria.max_stops is not None else 10,
            "carry_on": 1 if criteria.carry_on_only else 0,
            "hold_bag": 1 if criteria.checked_bag else 0,
            "limit": 50,
            "sort": "price",
        }
        
        # Round-trip support
        if criteria.return_dates:
            params["return_from"] = criteria.return_dates[0]
            params["return_to"] = criteria.return_dates[0]
        
        return params
    
    def _build_headers(self) -> Dict[str, str]:
        """Constrói headers para API Tequila"""
        return {"apikey": settings.tequila_api_key}
    
    async def _make_request(
        self, 
        params: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Faz requisição para API Tequila"""
        response = await self.client.get(
            "https://api.tequila.kiwi.com/v2/search",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def _parse_response(
        self, 
        raw_data: Dict[str, Any], 
        criteria: SearchCriteria
    ) -> List[FlightOffer]:
        """Parseia resposta da API Tequila"""
        offers = []
        
        for item in raw_data.get("data", []):
            price_total = float(item.get("price", 0.0))
            
            # Filtro de preço máximo
            if criteria.max_price and price_total > criteria.max_price:
                continue
            
            # Parseia segmentos
            segments = []
            for route in item.get("route", []):
                segments.append(
                    FlightSegment(
                        origin=route.get("flyFrom"),
                        destination=route.get("flyTo"),
                        departure=route.get("local_departure"),
                        arrival=route.get("local_arrival"),
                        marketing_carrier=route.get("operating_carrier") or route.get("airline"),
                        flight_number=route.get("operating_flight_no") or route.get("flight_no"),
                    )
                )
            
            offers.append(
                FlightOffer(
                    provider=self.name,
                    price_total=price_total,
                    currency=item.get("currency", criteria.preferred_currency or settings.default_currency),
                    baggage_included=not bool(item.get("bags_price", {})),
                    cabin_class=criteria.cabin_class or "ECONOMY",
                    segments=segments,
                    booking_link=item.get("deep_link"),
                    refundable=item.get("refundable"),
                    changeable=item.get("change_penalty") is not None,
                )
            )
        
        return offers
    
    def _map_cabin_class(self, cabin_class: str = None) -> str:
        """Mapeia classe de cabine para formato Tequila"""
        mapping = {
            "ECONOMY": "M",
            "PREMIUM_ECONOMY": "W", 
            "BUSINESS": "C",
            "FIRST": "F"
        }
        return mapping.get(cabin_class or "ECONOMY", "M")