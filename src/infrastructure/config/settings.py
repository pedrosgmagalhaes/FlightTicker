"""
Configuration Settings - Singleton pattern para configurações
"""
import os
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Singleton para configurações da aplicação"""
    
    _instance: Optional['Settings'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Settings':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            load_dotenv()
            self._load_settings()
            Settings._initialized = True
    
    def _load_settings(self):
        # API Keys
        self.tequila_api_key = os.getenv("TEQUILA_API_KEY", "")
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID", "")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "")
        
        # Default preferences
        self.default_currency = os.getenv("DEFAULT_CURRENCY", "EUR")
        self.default_locale = os.getenv("DEFAULT_LOCALE", "pt-PT")
        
        # API Settings
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
        
        # Application Settings
        self.app_env = os.getenv("APP_ENV", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
    
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"
    
    @property
    def has_tequila_credentials(self) -> bool:
        return bool(self.tequila_api_key)
    
    @property
    def has_amadeus_credentials(self) -> bool:
        return bool(self.amadeus_client_id and self.amadeus_client_secret)


# Singleton instance
settings = Settings()