"""
Provedor Kiwi/Tequila API
"""
import httpx
from typing import List, Optional
from ...domain.models import SearchCriteria, FlightOffer, FlightSegment
from ...application.interfaces import FlightProviderInterface
from ..config import Config


class KiwiTequilaProvider:
    """Provedor de voos via Kiwi/Tequila API"""
    
    name = "Kiwi/Tequila"
    
    def __init__(self, config: Config = Config()):
        self._config = config
        self._base_url = "https://api.tequila.kiwi.com/v2"
    
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca ofertas via Kiwi API"""
        if not self._config.is_tequila_configured():
            return []
        
        offers: List[FlightOffer] = []
        
        async with httpx.AsyncClient(timeout=self._config.REQUEST_TIMEOUT) as client:
            for depart_date in criteria.depart_dates:
                params = self._build_search_params(criteria, depart_date)
                headers = {"apikey": self._config.TEQUILA_API_KEY}
                
                try:
                    response = await client.get(
                        f"{self._base_url}/search",
                        params=params,
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    offers.extend(self._parse_response(data, criteria))
                    
                except Exception as e:
                    # Log error in production
                    continue
        
        return offers
    
    def _build_search_params(self, criteria: SearchCriteria, depart_date: str) -> dict:
        """Constrói parâmetros da requisição"""
        params = {
            "fly_from": criteria.origin,
            "fly_to": criteria.destination,
            "date_from": depart_date,
            "date_to": depart_date,
            "curr": criteria.preferred_currency or self._config.DEFAULT_CURRENCY,
            "locale": criteria.locale or self._config.DEFAULT_LOCALE,
            "adults": criteria.adults,
            "selected_cabins": self._map_cabin_class(criteria.cabin_class),
            "max_stopovers": criteria.max_stops if criteria.max_stops is not None else 10,
            "carry_on": 1 if criteria.carry_on_only else 0,
            "hold_bag": 1 if criteria.checked_bag else 0,
            "limit": 50,
            "sort": "price",
        }
        
        if criteria.return_dates:
            params["return_from"] = criteria.return_dates[0]
            params["return_to"] = criteria.return_dates[0]
        
        return params
    
    def _map_cabin_class(self, cabin_class: Optional[str]) -> str:
        """Mapeia classe de cabine para formato Kiwi"""
        mapping = {
            "ECONOMY": "M",
            "PREMIUM_ECONOMY": "W", 
            "BUSINESS": "C",
            "FIRST": "F"
        }
        return mapping.get(cabin_class or "ECONOMY", "M")
    
    def _parse_response(self, data: dict, criteria: SearchCriteria) -> List[FlightOffer]:
        """Converte resposta da API em ofertas"""
        offers = []
        
        for item in data.get("data", []):
            try:
                price = float(item.get("price", 0.0))
                
                if criteria.max_price and price > criteria.max_price:
                    continue
                
                segments = []
                for route in item.get("route", []):
                    segments.append(FlightSegment(
                        origin=route.get("flyFrom"),
                        destination=route.get("flyTo"),
                        departure=route.get("local_departure"),
                        arrival=route.get("local_arrival"),
                        marketing_carrier=route.get("operating_carrier") or route.get("airline"),
                        flight_number=route.get("operating_flight_no") or route.get("flight_no"),
                    ))
                
                offers.append(FlightOffer(
                    provider=self.name,
                    price_total=price,
                    currency=item.get("currency", criteria.preferred_currency or self._config.DEFAULT_CURRENCY),
                    baggage_included=not bool(item.get("bags_price", {})),
                    cabin_class=criteria.cabin_class or "ECONOMY",
                    segments=segments,
                    booking_link=item.get("deep_link"),
                    refundable=item.get("refundable"),
                    changeable=item.get("change_penalty") is not None,
                ))
                
            except Exception:
                continue
        
        return offers
