"""
API Exception Classes

Custom exception classes for API error handling.
"""

from fastapi import HTTPException, status


class APIException(HTTPException):
    """Base API exception class."""
    pass


class ValidationError(APIException):
    """Raised when request validation fails."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class NotFoundError(APIException):
    """Raised when requested resource not found."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class UnauthorizedError(APIException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ForbiddenError(APIException):
    """Raised when user lacks permissions."""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ConflictError(APIException):
    """Raised on resource conflict."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )
