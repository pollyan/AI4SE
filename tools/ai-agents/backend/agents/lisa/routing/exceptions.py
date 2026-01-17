class RoutingError(Exception):
    """Base exception for routing errors."""
    pass

class SemanticRouterError(RoutingError):
    """Raised when semantic routing fails."""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error

class LLMRouterError(RoutingError):
    """Raised when LLM routing fails."""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error
