"""
AI Ranking Service - Serviço de ranqueamento inteligente
"""
import numpy as np
from typing import List, Tuple
from ...domain.interfaces.services import IAIRankingService
from ...domain.entities import FlightOffer


class AIRankingService(IAIRankingService):
    """Serviço de ranqueamento usando algoritmos de IA"""
    
    def __init__(self):
        # Pesos para diferentes fatores (podem ser ajustados)
        self.weights = {
            'price': 0.4,
            'stops': 0.25,
            'duration': 0.15,
            'baggage': 0.1,
            'cabin': 0.05,
            'reliability': 0.05
        }
    
    def rank_offers(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Ranqueia ofertas usando IA"""
        if not offers:
            return offers
        
        # Calcula preço de referência (mediana)
        prices = [offer.price_total for offer in offers]
        reference_price = float(np.median(prices))
        
        # Calcula scores para todas as ofertas
        scored_offers = []
        for offer in offers:
            score, explanation = self.score_offer(offer, reference_price)
            offer.ai_score = score
            offer.ai_explanation = explanation
            scored_offers.append(offer)
        
        # Ordena por score (decrescente) e desempata por preço (crescente)
        return sorted(
            scored_offers, 
            key=lambda x: (-x.ai_score if x.ai_score else 0, x.price_total)
        )
    
    def score_offer(
        self, 
        offer: FlightOffer, 
        reference_price: float = None
    ) -> Tuple[float, str]:
        """Calcula score detalhado para uma oferta"""
        if reference_price is None:
            reference_price = offer.price_total
        
        # Componentes do score
        price_score = self._calculate_price_score(offer.price_total, reference_price)
        stops_score = self._calculate_stops_score(offer.total_stops)
        duration_score = self._calculate_duration_score(offer)
        baggage_score = self._calculate_baggage_score(offer)
        cabin_score = self._calculate_cabin_score(offer)
        reliability_score = self._calculate_reliability_score(offer)
        
        # Score final ponderado
        final_score = (
            price_score * self.weights['price'] +
            stops_score * self.weights['stops'] +
            duration_score * self.weights['duration'] +
            baggage_score * self.weights['baggage'] +
            cabin_score * self.weights['cabin'] +
            reliability_score * self.weights['reliability']
        ) * 100
        
        # Limita entre 0 e 100
        final_score = max(0, min(100, final_score))
        
        # Gera explicação
        explanation = self._generate_explanation(
            offer, price_score, stops_score, duration_score, 
            baggage_score, cabin_score, reliability_score
        )
        
        return final_score, explanation
    
    def _calculate_price_score(self, price: float, reference: float) -> float:
        """Score baseado no preço (menor é melhor)"""
        if price <= 0 or reference <= 0:
            return 0.5
        
        ratio = reference / price
        # Score entre 0 e 1, onde 1 é o melhor preço
        return min(1.0, max(0.1, ratio))
    
    def _calculate_stops_score(self, stops: int) -> float:
        """Score baseado no número de paradas (menos é melhor)"""
        if stops == 0:
            return 1.0
        elif stops == 1:
            return 0.8
        elif stops == 2:
            return 0.6
        else:
            return 0.3
    
    def _calculate_duration_score(self, offer: FlightOffer) -> float:
        """Score baseado na duração total (heurística)"""
        if not offer.segments:
            return 0.5
        
        # Heurística simples baseada no número de segmentos
        # Voos diretos são preferidos
        segment_penalty = len(offer.segments) * 0.1
        return max(0.3, 1.0 - segment_penalty)
    
    def _calculate_baggage_score(self, offer: FlightOffer) -> float:
        """Score baseado na inclusão de bagagem"""
        return 1.0 if offer.baggage_included else 0.7
    
    def _calculate_cabin_score(self, offer: FlightOffer) -> float:
        """Score baseado na classe da cabine"""
        cabin_scores = {
            'ECONOMY': 1.0,      # Melhor para busca de economia
            'PREMIUM_ECONOMY': 0.9,
            'BUSINESS': 0.7,     # Penaliza classes caras
            'FIRST': 0.5
        }
        
        cabin = (offer.cabin_class or 'ECONOMY').upper()
        return cabin_scores.get(cabin, 0.8)
    
    def _calculate_reliability_score(self, offer: FlightOffer) -> float:
        """Score baseado na confiabilidade do provedor"""
        provider_scores = {
            'Kiwi/Tequila': 0.9,
            'Amadeus': 0.95,
            'SplitTickets': 0.7,  # Menor por ser mais arriscado
        }
        
        return provider_scores.get(offer.provider, 0.8)
    
    def _generate_explanation(
        self, 
        offer: FlightOffer,
        price_score: float,
        stops_score: float, 
        duration_score: float,
        baggage_score: float,
        cabin_score: float,
        reliability_score: float
    ) -> str:
        """Gera explicação legível do score"""
        explanations = []
        
        # Preço
        if price_score > 0.8:
            explanations.append("Excelente preço")
        elif price_score > 0.6:
            explanations.append("Bom preço")
        else:
            explanations.append("Preço alto")
        
        # Paradas
        stops = offer.total_stops
        if stops == 0:
            explanations.append("Voo direto")
        elif stops == 1:
            explanations.append("1 parada")
        else:
            explanations.append(f"{stops} paradas")
        
        # Bagagem
        if offer.baggage_included:
            explanations.append("Bagagem incluída")
        
        # Classe
        if offer.cabin_class and offer.cabin_class != 'ECONOMY':
            explanations.append(f"Classe {offer.cabin_class}")
        
        return "; ".join(explanations)