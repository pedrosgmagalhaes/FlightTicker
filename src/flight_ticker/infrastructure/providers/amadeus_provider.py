"""
Provedor Amadeus API
"""
import httpx
from typing import List, Optional
from ...domain.models import SearchCriteria, FlightOffer, FlightSegment
from ...application.interfaces import FlightProviderInterface
from ..config import Config


class AmadeusProvider:
    """Provedor de voos via Amadeus API"""
    
    name = "Amadeus"
    
    def __init__(self, config: Config = Config()):
        self._config = config
        self._base_url = self._config.get_amadeus_base_url()
        self._token_cache: Optional[str] = None
    
    async def search(self, criteria: SearchCriteria) -> List[FlightOffer]:
        """Busca ofertas via Amadeus API"""
        if not self._config.is_amadeus_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        # Simplificação: usa apenas primeira data
        depart_date = criteria.depart_dates[0]
        return_date = criteria.return_dates[0] if criteria.return_dates else None
        
        params = self._build_search_params(criteria, depart_date, return_date)
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=self._config.REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(
                    f"{self._base_url}/v2/shopping/flight-offers",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data, criteria)
                
            except Exception:
                return []
    
    async def _get_access_token(self) -> Optional[str]:
        """Obtém token de acesso OAuth2"""
        if self._token_cache:
            return self._token_cache
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._config.AMADEUS_CLIENT_ID,
                        "client_secret": self._config.AMADEUS_CLIENT_SECRET,
                    }
                )
                response.raise_for_status()
                token = response.json().get("access_token")
                self._token_cache = token
                return token
                
            except Exception:
                return None
    
    def _build_search_params(self, criteria: SearchCriteria, depart_date: str, return_date: Optional[str]) -> dict:
        """Constrói parâmetros da requisição"""
        params = {
            "originLocationCode": criteria.origin,
            "destinationLocationCode": criteria.destination,
            "departureDate": depart_date,
            "adults": criteria.adults,
            "nonStop": criteria.max_stops == 0 if criteria.max_stops is not None else False,
            "currencyCode": criteria.preferred_currency or self._config.DEFAULT_CURRENCY,
        }
        if criteria.children and criteria.children > 0:
            params["children"] = criteria.children
        if criteria.infants and criteria.infants > 0:
            params["infants"] = criteria.infants
        
        if return_date:
            params["returnDate"] = return_date
        
        if criteria.cabin_class:
            params["travelClass"] = criteria.cabin_class
        
        return params
    
    def _parse_response(self, data: dict, criteria: SearchCriteria) -> List[FlightOffer]:
        """Converte resposta da API em ofertas"""
        offers = []
        
        for offer_data in data.get("data", []):
            try:
                price_info = offer_data.get("price", {})
                price = float(price_info.get("grandTotal", price_info.get("total", 0.0)))
                
                if criteria.max_price and price > criteria.max_price:
                    continue
                
                # Verificar bagagem incluída: travelerPricings -> fareDetailsBySegment -> includedCheckedBags.quantity
                baggage_included = False
                for tp in offer_data.get("travelerPricings", []):
                    for fd in tp.get("fareDetailsBySegment", []):
                        bags = fd.get("includedCheckedBags") or {}
                        qty = bags.get("quantity")
                        if isinstance(qty, int) and qty > 0:
                            baggage_included = True
                            break
                    if baggage_included:
                        break

                # Se usuário exigiu bagagem despachada, filtra somente ofertas com bagagem incluída
                if criteria.checked_bag and not baggage_included:
                    continue

                segments = []
                first_outbound_dep_date = None
                return_dep_date = None
                for itinerary in offer_data.get("itineraries", []):
                    # Identifica data de partida do primeiro trecho de ida e, se existir, da volta
                    if first_outbound_dep_date is None:
                        first_seg = (itinerary.get("segments") or [{}])[0]
                        dep_ts = (first_seg.get("departure") or {}).get("at")
                        if dep_ts:
                            first_outbound_dep_date = dep_ts[:10]
                    else:
                        # Considera segunda itinerary como retorno (quando ida e volta)
                        first_seg = (itinerary.get("segments") or [{}])[0]
                        dep_ts = (first_seg.get("departure") or {}).get("at")
                        if dep_ts:
                            return_dep_date = dep_ts[:10]
                    for segment_data in itinerary.get("segments", []):
                        segments.append(FlightSegment(
                            origin=segment_data["departure"]["iataCode"],
                            destination=segment_data["arrival"]["iataCode"],
                            departure=segment_data["departure"]["at"],
                            arrival=segment_data["arrival"]["at"],
                            marketing_carrier=segment_data.get("carrierCode"),
                            flight_number=segment_data.get("number"),
                        ))
                
                # Gera link de checkout: preferir site da companhia quando houver um único carrier
                # e sempre construir link alternativo via Google Flights
                checkout_link = None
                alt_link = None
                try:
                    if segments:
                        origin = segments[0].origin
                        destination = segments[0].destination
                        dep_date = first_outbound_dep_date or (segments[0].departure[:10] if segments[0].departure else None)
                        carriers = sorted({seg.marketing_carrier for seg in segments if seg.marketing_carrier})
                        # Prepara link alternativo (Google Flights)
                        hl = (criteria.locale or self._config.DEFAULT_LOCALE).replace('_', '-')
                        currency = criteria.preferred_currency or self._config.DEFAULT_CURRENCY
                        flt_param = f"{origin}.{destination}.{dep_date}" if (origin and destination and dep_date) else ""
                        if return_dep_date and origin and destination and dep_date:
                            flt_param = f"{origin}.{destination}.{dep_date}*{destination}.{origin}.{return_dep_date}"
                        if flt_param:
                            alt_link = (
                                f"https://www.google.com/travel/flights?hl={hl}#flt={flt_param};c:{currency}"
                            )
                        # Preferir link direto da companhia quando houver uma única
                        if origin and destination and dep_date:
                            if len(carriers) == 1:
                                code = carriers[0]
                                # Mapear alguns sites de cias comuns na região
                                adults = criteria.adults or 1
                                children = criteria.children or 0
                                infants = criteria.infants or 0
                                if code == "LA":
                                    # LATAM com parâmetros de busca
                                    checkout_link = (
                                        f"https://www.latamairlines.com/br/pt/oferta-de-voos?"
                                        f"origin={origin}&destination={destination}&departureDate={dep_date}"
                                        f"{f'&returnDate={return_dep_date}' if return_dep_date else ''}"
                                        f"&adt={adults}&chd={children}&inf={infants}"
                                    )
                                elif code == "G3":
                                    # GOL - sem padrão público de deep link estável, usar página inicial
                                    checkout_link = "https://www.voegol.com.br/"
                                elif code == "H2":
                                    # SKY - sem padrão público de deep link estável, usar página BR
                                    checkout_link = "https://www.skyairline.com/br/pt"
                                elif code in ("JA", "J4", "WJ"):
                                    checkout_link = "https://www.jetsmart.com/br/pt"
                                elif code == "AV":
                                    checkout_link = "https://www.avianca.com/br/pt/"
                            
                            # Caso não tenhamos link direto ou múltiplos carriers, usar o alternativo
                            if not checkout_link and alt_link:
                                checkout_link = alt_link
                except Exception:
                    checkout_link = None
                    alt_link = None

                # Inclui alt_link nas notas para exibir ambos na CLI
                notes_text = None
                if checkout_link and alt_link and checkout_link != alt_link:
                    notes_text = f"Alternativo: {alt_link}"

                offers.append(FlightOffer(
                    provider=self.name,
                    price_total=price,
                    currency=price_info.get("currency", criteria.preferred_currency or self._config.DEFAULT_CURRENCY),
                    baggage_included=baggage_included,
                    cabin_class=criteria.cabin_class,
                    segments=segments,
                    booking_link=checkout_link,
                    notes=notes_text,
                ))
                
            except Exception:
                continue
        
        return offers
