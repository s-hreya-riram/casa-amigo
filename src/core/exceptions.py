# TODO refine exception hierarchy and messages as needed
class CasaAmigoError(Exception):
    """Base exception for Casa Amigo"""
    pass

class NotFoundError(CasaAmigoError):
    """Resource not found"""
    pass

class ValidationError(CasaAmigoError):
    """Data validation failed"""
    pass

class AuthenticationError(CasaAmigoError):
    """Authentication failed"""
    pass

class OperationError(CasaAmigoError):
    """Database operation failed"""
    pass