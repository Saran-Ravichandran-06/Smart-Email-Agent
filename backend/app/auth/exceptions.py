class AuthError(Exception):
    """Base authentication error."""


class NotAuthenticatedError(AuthError):
    """No valid session or user context."""


class InvalidSessionError(AuthError):
    """Session exists but is invalid or expired."""


class OAuthTokenError(AuthError):
    """OAuth token missing, expired, or cannot be refreshed."""
