"""Tests for security module."""

from unittest.mock import patch
from src.security import SecurityManager


def test_store_and_retrieve_password():
    """Test storing and retrieving passwords."""
    manager = SecurityManager()
    test_connection = "test_postgres_conn"
    test_password = "super_secret_password"

    with (
        patch("keyring.set_password") as mock_set,
        patch("keyring.get_password", return_value=test_password) as mock_get,
    ):
        manager.store_password(test_connection, test_password)
        mock_set.assert_called_once_with(
            SecurityManager.KEYRING_SERVICE, test_connection, test_password
        )

        retrieved = manager.retrieve_password(test_connection)
        mock_get.assert_called_once_with(
            SecurityManager.KEYRING_SERVICE, test_connection
        )
        assert retrieved == test_password


def test_retrieve_nonexistent_password():
    """Test retrieving a password that doesn't exist."""
    manager = SecurityManager()

    with patch("keyring.get_password", return_value=None):
        result = manager.retrieve_password("nonexistent_connection")
        assert result is None


def test_validate_cert_path(tmp_path):
    """Test certificate path validation."""
    # Create a temporary cert file
    cert_file = tmp_path / "test_cert.pem"
    cert_file.write_text("FAKE CERTIFICATE")

    assert SecurityManager.validate_cert_path(str(cert_file))
    assert not SecurityManager.validate_cert_path("/nonexistent/path/cert.pem")
    assert not SecurityManager.validate_cert_path("")


# --- Bug fix tests ---


def test_set_password_uses_composite_key():
    """Bug fix: set_password(engine, host, username, password) stores under a composite key."""
    with patch("keyring.set_password") as mock_set:
        SecurityManager.set_password("postgres", "db.example.com", "alice", "s3cr3t")
        expected_key = "postgres:db.example.com:alice"
        mock_set.assert_called_once_with(
            SecurityManager.KEYRING_SERVICE, expected_key, "s3cr3t"
        )


def test_get_password_uses_composite_key():
    """Bug fix: get_password(engine, host, username) retrieves by composite key."""
    with patch("keyring.get_password", return_value="s3cr3t") as mock_get:
        result = SecurityManager.get_password("mysql", "localhost", "bob")
        expected_key = "mysql:localhost:bob"
        mock_get.assert_called_once_with(SecurityManager.KEYRING_SERVICE, expected_key)
        assert result == "s3cr3t"


def test_get_password_returns_none_when_not_found():
    """Bug fix: get_password returns None when no password is stored."""
    with patch("keyring.get_password", return_value=None):
        result = SecurityManager.get_password("postgres", "localhost", "nobody")
        assert result is None


def test_make_key_format():
    """Test that the composite key is formatted correctly."""
    key = SecurityManager._make_key("duckdb", "localhost", "admin")
    assert key == "duckdb:localhost:admin"
