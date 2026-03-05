"""Custom exception hierarchy for the migration tool."""


class AuthenticationError(Exception):
    """Authentication related errors."""
    pass


class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class RateLimitError(MigrationError):
    """Rate limiting errors."""
    pass


class GitOperationError(MigrationError):
    """Git operation errors."""
    pass
