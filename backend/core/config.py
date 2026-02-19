import os
import yaml
from typing import Optional, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, BaseModel
from backend.core.exceptions import ConfigurationError

class SystemConfig(BaseModel):
    enable_logging: bool = True

class KeysConfig(BaseModel):
    real_api_key: Optional[str] = None
    real_secret_key: Optional[str] = None
    spot_test_api_key: Optional[str] = None
    spot_test_secret_key: Optional[str] = None
    future_test_api_key: Optional[str] = None
    future_test_secret_key: Optional[str] = None

class UrlsConfig(BaseModel):
    spot_test_base_url: str = "https://testnet.binance.vision"
    future_test_base_url: str = "https://testnet.binancefuture.com"

class Settings(BaseSettings):
    system: SystemConfig = SystemConfig()
    keys: KeysConfig = KeysConfig()
    urls: UrlsConfig = UrlsConfig()

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    @classmethod
    def load_from_yaml(cls, path: str = None) -> "Settings":
        if path is None:
            # Default to backend/core/config.yaml
            path = os.path.join(os.path.dirname(__file__), "config.yaml")
        
        if not os.path.exists(path):
            return cls()

        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        
        return cls(**data)

    def get_spot_test_keys(self) -> Tuple[str, str]:
        """
        Get Spot Testnet API keys.
        """
        api_key = self.keys.spot_test_api_key
        secret_key = self.keys.spot_test_secret_key
        
        if not api_key or not secret_key:
            raise ConfigurationError("Spot Testnet keys are missing in configuration")
            
        return api_key, secret_key

    def get_future_test_keys(self) -> Tuple[str, str]:
        """
        Get Futures Testnet API keys.
        """
        api_key = self.keys.future_test_api_key
        secret_key = self.keys.future_test_secret_key
        
        if not api_key or not secret_key:
            # Fallback logic could be here, but for now we enforce explicit config
            # Or use the spot keys if user intended to reuse them (not recommended but possible)
            raise ConfigurationError("Futures Testnet keys are missing in configuration")
            
        return api_key, secret_key

    def get_real_keys(self) -> Tuple[str, str]:
        """
        Get Real Trading API keys.
        """
        api_key = self.keys.real_api_key
        secret_key = self.keys.real_secret_key
        
        if not api_key or not secret_key:
            raise ConfigurationError("Real trading keys are missing in configuration")
            
        return api_key, secret_key

# Singleton instance
settings = Settings.load_from_yaml()
