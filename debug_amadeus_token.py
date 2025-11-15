#!/usr/bin/env python3
"""
Diagnóstico rápido da Amadeus API: token e busca exemplo
"""
import os
import sys
import asyncio

# Garante que 'src' está no PYTHONPATH
BASE_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from flight_ticker.infrastructure.providers.amadeus_provider import AmadeusProvider
from flight_ticker.infrastructure.config import Config
from flight_ticker.domain.models import SearchCriteria
import httpx


async def main():
    cfg = Config()
    print("Config Amadeus:", bool(cfg.AMADEUS_CLIENT_ID), bool(cfg.AMADEUS_CLIENT_SECRET))

    provider = AmadeusProvider(cfg)
    # Diagnóstico detalhado do token
    print("\nTestando obtenção de token direto (diagnóstico):")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{cfg.get_amadeus_base_url()}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": cfg.AMADEUS_CLIENT_ID,
                    "client_secret": cfg.AMADEUS_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            print("Status:", resp.status_code)
            try:
                print("Resposta:", resp.json())
            except Exception:
                print("Resposta (texto):", resp.text)
            token = resp.json().get("access_token") if resp.headers.get("content-type", "").startswith("application/json") else None
    except Exception as e:
        print("Erro de rede ao obter token:", e)
        token = None
    print("Token:", "OK" if token else "None")

    # Teste de busca simples: RIO -> MVD em 2025-12-15
    criteria = SearchCriteria(
        origin="RIO",
        destination="MVD",
        depart_dates=["2025-12-15"],
        return_dates=None,
        adults=1,
        cabin_class="ECONOMY",
    )
    offers = await provider.search(criteria)
    print("Ofertas encontradas:", len(offers))
    for i, offer in enumerate(offers[:5], start=1):
        print(f"{i}. {offer.provider} {offer.currency} {offer.price_total:.2f} {offer.route_summary}")


if __name__ == "__main__":
    asyncio.run(main())