from typing import Optional, Any, Dict

class QuantEngineError(Exception):
    """Base exception for all custom errors in the Quant Engine"""
    def __init__(self, message: str, code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.code}] {self.message}"

class ConfigurationError(QuantEngineError):
    """Raised when there is a configuration error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=503, details=details)

class ExchangeError(QuantEngineError):
    """Base exception for exchange related errors"""
    def __init__(self, message: str, code: int = 502, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code, details=details)

class OrderError(ExchangeError):
    """Raised when an order operation fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=400, details=details)

class InsufficientFundsError(OrderError):
    """Raised when there are insufficient funds for an order"""
    def __init__(self, message: str = "Insufficient funds", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)

class StrategyError(QuantEngineError):
    """Base exception for strategy related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=400, details=details)

class DataError(QuantEngineError):
    """Base exception for data related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=404, details=details)
