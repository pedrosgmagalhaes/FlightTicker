"""
Configuração da aplicação
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuração centralizada"""
    
    # API Keys
    TEQUILA_API_KEY = os.getenv("TEQUILA_API_KEY", "")
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
    AMADEUS_ENV = os.getenv("AMADEUS_ENV", "TEST").upper()
    
    # Defaults
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
    DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "pt-PT")
    
    # Limites
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    @classmethod
    def is_tequila_configured(cls) -> bool:
        return bool(cls.TEQUILA_API_KEY)
    
    @classmethod
    def is_amadeus_configured(cls) -> bool:
        return bool(cls.AMADEUS_CLIENT_ID and cls.AMADEUS_CLIENT_SECRET)

    @classmethod
    def get_amadeus_base_url(cls) -> str:
        """Retorna a base URL da Amadeus conforme ambiente."""
        return "https://api.amadeus.com" if cls.AMADEUS_ENV == "PRODUCTION" else "https://test.api.amadeus.com"
