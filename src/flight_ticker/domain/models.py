"""
Domain Models - Entidades de negócio puras
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FlightSegment(BaseModel):
    """Segmento de voo individual"""
    origin: str = Field(..., description="IATA código origem")
    destination: str = Field(..., description="IATA código destino")
    departure: str = Field(..., description="ISO datetime partida")
    arrival: str = Field(..., description="ISO datetime chegada")
    marketing_carrier: Optional[str] = None
    flight_number: Optional[str] = None
    duration_minutes: Optional[int] = None


class FlightOffer(BaseModel):
    """Oferta de voo completa"""
    provider: str
    price_total: float
    currency: str
    baggage_included: bool = False
    cabin_class: Optional[str] = None
    segments: List[FlightSegment]
    booking_link: Optional[str] = None
    refundable: Optional[bool] = None
    changeable: Optional[bool] = None
    notes: Optional[str] = None
    ai_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    
    @property
    def total_stops(self) -> int:
        """Número total de paradas"""
        return max(0, len(self.segments) - 1)
    
    @property
    def route_summary(self) -> str:
        """Resumo da rota"""
        if not self.segments:
            return ""
        origins = [self.segments[0].origin]
        destinations = [seg.destination for seg in self.segments]
        return " → ".join(origins + destinations)


class SearchCriteria(BaseModel):
    """Critérios de busca"""
    origin: str
    destination: str
    depart_dates: List[str]  # "YYYY-MM-DD"
    return_dates: Optional[List[str]] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin_class: Optional[str] = None
    max_stops: Optional[int] = None
    preferred_currency: Optional[str] = None
    locale: Optional[str] = None
    carry_on_only: bool = False
    checked_bag: bool = False
    max_price: Optional[float] = None
    
    def is_round_trip(self) -> bool:
        """Verifica se é ida e volta"""
        return self.return_dates is not None and len(self.return_dates) > 0


class SearchResult(BaseModel):
    """Resultado de uma busca"""
    offers: List[FlightOffer]
    search_criteria: SearchCriteria
    search_timestamp: datetime
    total_found: int
    
    @property
    def best_offer(self) -> Optional[FlightOffer]:
        """Melhor oferta por score de IA ou preço"""
        if not self.offers:
            return None
        return max(self.offers, key=lambda x: x.ai_score or 0.0)
    
    @property
    def cheapest_offer(self) -> Optional[FlightOffer]:
        """Oferta mais barata"""
        if not self.offers:
            return None
        return min(self.offers, key=lambda x: x.price_total)
