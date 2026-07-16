from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound,
    AuthenticationFailed,
    Throttled,
)
from rest_framework import status
from .responses import error_response


def custom_exception_handler(exc, context):
    if isinstance(exc, ValidationError):
        return error_response(
            errors=exc.detail if isinstance(exc.detail, dict) else {'detail': exc.detail},
            message="Validation failed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, PermissionDenied):
        return error_response(
            errors={'detail': str(exc)},
            message="Permission denied.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, NotFound):
        return error_response(
            errors={'detail': str(exc)},
            message="Not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, AuthenticationFailed):
        return error_response(
            errors={'detail': str(exc)},
            message="Authentication failed.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, Throttled):
        return error_response(
            errors={'detail': f"Rate limit exceeded. Try again in {exc.wait:.0f} seconds."},
            message="Rate limit exceeded.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    response = exception_handler(exc, context)
    if response is not None:
        return error_response(
            errors=response.data if isinstance(response.data, dict) else {'detail': response.data},
            message="Error.",
            status_code=response.status_code,
        )

    return error_response(
        errors={'detail': 'Internal server error.'},
        message="Internal server error.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
