"""
Amadeus Provider Implementation
"""
from typing import List, Dict, Any, Optional
from ...domain.entities import FlightOffer, FlightSegment, SearchCriteria
from ..config.settings import settings
from .base import BaseFlightProvider


class AmadeusProvider(BaseFlightProvider):
    """Implementação do provedor Amadeus"""
    
    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
    
    @property
    def name(self) -> str:
        return "Amadeus"
    
    def is_available(self) -> bool:
        return settings.has_amadeus_credentials
    
    async def _get_access_token(self) -> Optional[str]:
        """Obtém token de acesso OAuth2"""
        if self._access_token:
            return self._access_token
        
        try:
            response = await self.client.post(
                "https://test.api.amadeus.com/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.amadeus_client_id,
                    "client_secret": settings.amadeus_client_secret,
                },
            )
            response.raise_for_status()
            self._access_token = response.json().get("access_token")
            return self._access_token
        except Exception:
            return None
    
    def _build_search_params(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Constrói parâmetros para API Amadeus"""
        params = {
            "originLocationCode": criteria.origin,
            "destinationLocationCode": criteria.destination,
            "departureDate": criteria.depart_dates[0],
            "adults": criteria.adults,
            "nonStop": criteria.max_stops == 0 if criteria.max_stops is not None else False,
            "currencyCode": criteria.preferred_currency or settings.default_currency,
        }
        
        if criteria.return_dates:
            params["returnDate"] = criteria.return_dates[0]
        
        if criteria.cabin_class:
            params["travelClass"] = criteria.cabin_class
        
        return params
    
    def _build_headers(self) -> Dict[str, str]:
        """Headers serão construídos após obter token"""
        return {}
    
    async def _make_request(
        self, 
        params: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Faz requisição para API Amadeus"""
        token = await self._get_access_token()
        if not token:
            raise Exception("Failed to get Amadeus access token")
        
        headers["Authorization"] = f"Bearer {token}"
        
        response = await self.client.get(
            "https://test.api.amadeus.com/v2/shopping/flight-offers",
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
        """Parseia resposta da API Amadeus"""
        offers = []
        
        for offer in raw_data.get("data", []):
            price_info = offer.get("price", {})
            total = float(price_info.get("grandTotal", price_info.get("total", 0.0)))
            
            # Filtro de preço máximo
            if criteria.max_price and total > criteria.max_price:
                continue
            
            # Parseia segmentos
            segments = []
            try:
                for itinerary in offer.get("itineraries", []):
                    for segment in itinerary.get("segments", []):
                        segments.append(
                            FlightSegment(
                                origin=segment["departure"]["iataCode"],
                                destination=segment["arrival"]["iataCode"],
                                departure=segment["departure"]["at"],
                                arrival=segment["arrival"]["at"],
                                marketing_carrier=segment.get("carrierCode"),
                                flight_number=segment.get("number"),
                            )
                        )
            except Exception:
                continue
            
            offers.append(
                FlightOffer(
                    provider=self.name,
                    price_total=total,
                    currency=price_info.get("currency", criteria.preferred_currency or settings.default_currency),
                    baggage_included=False,  # Pode ser determinado via travelerPricings
                    cabin_class=criteria.cabin_class,
                    segments=segments,
                    booking_link=None,  # Amadeus não fornece link direto
                    refundable=None,
                    changeable=None,
                )
            )
        
        return offers