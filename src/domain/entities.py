"""
Domain Entities - Core business objects
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FlightSegment(BaseModel):
    """Representa um segmento de voo individual"""
    origin: str = Field(..., description="IATA código de origem")
    destination: str = Field(..., description="IATA código de destino")
    departure: str = Field(..., description="ISO datetime de partida")
    arrival: str = Field(..., description="ISO datetime de chegada")
    marketing_carrier: Optional[str] = Field(None, description="Código da companhia aérea")
    flight_number: Optional[str] = Field(None, description="Número do voo")
    
    @property
    def duration_minutes(self) -> int:
        """Calcula duração do segmento em minutos"""
        try:
            dep = datetime.fromisoformat(self.departure.replace('Z', '+00:00'))
            arr = datetime.fromisoformat(self.arrival.replace('Z', '+00:00'))
            return int((arr - dep).total_seconds() / 60)
        except:
            return 0


class FlightOffer(BaseModel):
    """Representa uma oferta de voo completa"""
    provider: str = Field(..., description="Nome do provedor")
    price_total: float = Field(..., description="Preço total")
    currency: str = Field(..., description="Código da moeda")
    baggage_included: bool = Field(default=False, description="Bagagem incluída")
    cabin_class: Optional[str] = Field(None, description="Classe da cabine")
    segments: List[FlightSegment] = Field(..., description="Segmentos do voo")
    booking_link: Optional[str] = Field(None, description="Link para reserva")
    refundable: Optional[bool] = Field(None, description="Reembolsável")
    changeable: Optional[bool] = Field(None, description="Alterável")
    notes: Optional[str] = Field(None, description="Notas adicionais")
    ai_score: Optional[float] = Field(None, description="Score de IA")
    ai_explanation: Optional[str] = Field(None, description="Explicação do score")
    
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
    """Critérios de busca de voos"""
    origin: str = Field(..., description="IATA origem")
    destination: str = Field(..., description="IATA destino")
    depart_dates: List[str] = Field(..., description="Datas de partida (YYYY-MM-DD)")
    return_dates: Optional[List[str]] = Field(None, description="Datas de retorno")
    adults: int = Field(default=1, ge=1, le=9, description="Número de adultos")
    cabin_class: Optional[str] = Field(None, description="Classe da cabine")
    max_stops: Optional[int] = Field(None, ge=0, description="Máximo de paradas")
    preferred_currency: Optional[str] = Field(None, description="Moeda preferida")
    locale: Optional[str] = Field(None, description="Localização")
    carry_on_only: bool = Field(default=False, description="Apenas bagagem de mão")
    checked_bag: bool = Field(default=False, description="Bagagem despachada")
    max_price: Optional[float] = Field(None, gt=0, description="Preço máximo")