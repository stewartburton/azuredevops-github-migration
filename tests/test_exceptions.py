"""Tests for custom exception hierarchy."""
import pytest
from azuredevops_github_migration.exceptions import (
    AuthenticationError,
    MigrationError,
    RateLimitError,
    GitOperationError,
)


class TestExceptionHierarchy:
    def test_migration_error_is_exception(self):
        assert issubclass(MigrationError, Exception)

    def test_authentication_error_is_exception(self):
        assert issubclass(AuthenticationError, Exception)

    def test_rate_limit_error_inherits_migration_error(self):
        assert issubclass(RateLimitError, MigrationError)

    def test_git_operation_error_inherits_migration_error(self):
        assert issubclass(GitOperationError, MigrationError)

    def test_exception_messages(self):
        with pytest.raises(AuthenticationError, match="bad creds"):
            raise AuthenticationError("bad creds")

        with pytest.raises(MigrationError, match="failed"):
            raise MigrationError("failed")

        with pytest.raises(RateLimitError, match="429"):
            raise RateLimitError("429")

        with pytest.raises(GitOperationError, match="push failed"):
            raise GitOperationError("push failed")
