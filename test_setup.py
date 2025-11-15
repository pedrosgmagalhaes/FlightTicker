#!/usr/bin/env python3
"""
Script de teste para verificar se o projeto está funcionando
"""
import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Testa importações básicas
    from flight_ticker.domain.models import FlightOffer, SearchCriteria
    from flight_ticker.infrastructure.config import Config
    from flight_ticker.presentation.cli import FlightTickerCLI
    
    print("✅ Todas as importações funcionaram!")
    print("✅ Projeto configurado corretamente!")
    
    # Testa configuração
    config = Config()
    print(f"✅ Configuração carregada - Moeda padrão: {config.DEFAULT_CURRENCY}")
    
    print("\n🎉 O projeto FlightTicker está pronto para uso!")
    print("\nPara usar:")
    print("1. Configure suas API keys no arquivo .env")
    print("2. Execute: python -m src.flight_ticker --origin SAO --destination NYC --depart 2025-02-15")
    
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)