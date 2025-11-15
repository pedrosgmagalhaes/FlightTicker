"""
Flight Strategy Service - Strategy Pattern para diferentes estratégias de busca
"""
from typing import List, Set, Tuple
from datetime import datetime, timedelta
from ...domain.interfaces.services import IFlightStrategyService


class FlightStrategyService(IFlightStrategyService):
    """Implementação de estratégias de busca de voos"""
    
    # Grupos de aeroportos por região
    AIRPORT_GROUPS = {
        "SAO": {"GRU", "CGH", "VCP"},  # São Paulo
        "RIO": {"GIG", "SDU"},         # Rio de Janeiro
        "LON": {"LHR", "LGW", "STN", "LTN", "LCY", "SEN"},  # Londres
        "PAR": {"CDG", "ORY", "BVA"},  # Paris
        "NYC": {"JFK", "EWR", "LGA"},  # Nova York
        "MIL": {"MXP", "LIN", "BGY"},  # Milão
        "ROM": {"FCO", "CIA"},         # Roma
        "BCN": {"BCN", "GRO"},         # Barcelona
        "BER": {"BER", "SXF"},         # Berlim
    }
    
    # Hubs principais para conexões
    MAJOR_HUBS = {
        "LIS", "MAD", "IST", "CDG", "FRA", "LHR", "AMS", 
        "DOH", "DXB", "MUC", "ZRH", "BCN", "FCO", "ATH",
        "VIE", "CPH", "ARN", "HEL", "WAW", "PRG"
    }
    
    def expand_flexible_dates(
        self, 
        base_date: str, 
        days_before: int = 3, 
        days_after: int = 3
    ) -> List[str]:
        """Expande datas flexíveis para encontrar melhores preços"""
        try:
            dt = datetime.strptime(base_date, "%Y-%m-%d")
            expanded = []
            
            for delta in range(-days_before, days_after + 1):
                new_date = dt + timedelta(days=delta)
                expanded.append(new_date.strftime("%Y-%m-%d"))
            
            return sorted(set(expanded))
        except ValueError:
            return [base_date]
    
    def get_nearby_airports(self, iata: str) -> List[str]:
        """Obtém aeroportos próximos para expandir opções"""
        # Verifica se é um grupo conhecido
        if iata in self.AIRPORT_GROUPS:
            return list(self.AIRPORT_GROUPS[iata])
        
        # Verifica se o IATA está em algum grupo
        for group_key, airports in self.AIRPORT_GROUPS.items():
            if iata in airports:
                return list(airports)
        
        # Se não encontrou, retorna apenas o próprio
        return [iata]
    
    def get_hub_combinations(
        self, 
        origin: str, 
        destination: str
    ) -> List[Tuple[str, str, str]]:
        """Gera combinações via hubs para trechos separados"""
        origin_airports = set(self.get_nearby_airports(origin))
        dest_airports = set(self.get_nearby_airports(destination))
        
        combinations = []
        
        for o in origin_airports:
            for d in dest_airports:
                for hub in self.MAJOR_HUBS:
                    # Evita hub igual à origem ou destino
                    if hub != o and hub != d:
                        combinations.append((o, hub, d))
        
        # Limita combinações para evitar explosão combinatória
        return combinations[:50]
    
    def calculate_route_efficiency(
        self, 
        origin: str, 
        destination: str, 
        via_hub: str
    ) -> float:
        """Calcula eficiência da rota via hub (heurística simples)"""
        # Heurística baseada em hubs conhecidos
        major_hubs_score = {
            "LIS": 0.9, "MAD": 0.9, "CDG": 0.95, "FRA": 0.95,
            "LHR": 0.9, "AMS": 0.9, "IST": 0.85, "DOH": 0.8,
            "DXB": 0.8, "MUC": 0.9, "ZRH": 0.9
        }
        
        return major_hubs_score.get(via_hub, 0.7)
    
    def filter_efficient_combinations(
        self, 
        combinations: List[Tuple[str, str, str]],
        min_efficiency: float = 0.7
    ) -> List[Tuple[str, str, str]]:
        """Filtra combinações por eficiência"""
        efficient = []
        
        for origin, hub, destination in combinations:
            efficiency = self.calculate_route_efficiency(origin, destination, hub)
            if efficiency >= min_efficiency:
                efficient.append((origin, hub, destination))
        
        return efficient