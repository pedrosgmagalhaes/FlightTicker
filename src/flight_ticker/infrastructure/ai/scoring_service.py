"""
Serviço de pontuação inteligente de ofertas
"""
import numpy as np
from typing import List, Tuple, Optional
from ...domain.models import FlightOffer
from ...application.interfaces import ScoringServiceInterface


class AIFlightScoringService(ScoringServiceInterface):
    """Serviço de pontuação usando heurísticas inteligentes"""
    
    def score_offers(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Pontua e ordena ofertas por valor geral"""
        if not offers:
            return offers
        
        # Calcula preço de referência (mediana)
        prices = [o.price_total for o in offers]
        reference_price = float(np.median(prices))
        
        # Pontua cada oferta
        scored_offers = []
        for offer in offers:
            score, explanation = self._calculate_score(offer, reference_price)
            offer.ai_score = score
            offer.ai_explanation = explanation
            scored_offers.append(offer)
        
        # Ordena por score (maior primeiro) e desempata por preço (menor primeiro)
        return sorted(
            scored_offers,
            key=lambda x: (-x.ai_score if x.ai_score else 0.0, x.price_total)
        )
    
    def _calculate_score(self, offer: FlightOffer, reference_price: float) -> Tuple[float, str]:
        """Calcula score individual da oferta"""
        
        # 1. Fator preço (melhor se menor que referência)
        price_factor = reference_price / max(offer.price_total, 1e-6)
        price_factor = min(price_factor, 2.0)  # Cap em 2x
        
        # 2. Penalidade por paradas
        stops_penalty = 1.0 / (1.0 + 0.4 * offer.total_stops)
        
        # 3. Bônus bagagem incluída
        baggage_bonus = 1.1 if offer.baggage_included else 1.0
        
        # 4. Fator classe de cabine
        cabin_factor = self._get_cabin_factor(offer.cabin_class)
        
        # 5. Penalidade por muitos segmentos (complexidade)
        complexity_penalty = 1.0 / (1.0 + 0.1 * max(0, len(offer.segments) - 2))
        
        # Score final
        raw_score = (
            price_factor * 
            stops_penalty * 
            baggage_bonus * 
            cabin_factor * 
            complexity_penalty
        )
        
        # Normaliza para 0-100
        score = float(np.clip(raw_score * 35.0, 0.0, 100.0))
        
        # Explicação
        explanation = self._build_explanation(offer, score)
        
        return score, explanation
    
    def _get_cabin_factor(self, cabin_class: Optional[str]) -> float:
        """Fator baseado na classe de cabine"""
        if not cabin_class:
            return 1.0
        
        factors = {
            "ECONOMY": 1.05,        # Leve bônus para economia
            "PREMIUM_ECONOMY": 0.98, # Leve penalidade (mais caro)
            "BUSINESS": 0.90,       # Penalidade maior
            "FIRST": 0.85,          # Maior penalidade
        }
        
        return factors.get(cabin_class.upper(), 1.0)
    
    def _build_explanation(self, offer: FlightOffer, score: float) -> str:
        """Constrói explicação do score"""
        parts = [
            f"Preço: {offer.currency} {offer.price_total:.2f}",
            f"Paradas: {offer.total_stops}",
            f"Bagagem: {'incluída' if offer.baggage_included else 'não incluída'}",
            f"Classe: {offer.cabin_class or 'ECONOMY'}",
            f"Score: {score:.1f}/100"
        ]
        
        return " | ".join(parts)
