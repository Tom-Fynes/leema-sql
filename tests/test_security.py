"""Tests for security module."""

import pytest
from unittest.mock import patch, MagicMock
from src.security import SecurityManager


def test_store_and_retrieve_password():
    """Test storing and retrieving passwords."""
    manager = SecurityManager()
    test_connection = "test_postgres_conn"
    test_password = "super_secret_password"

    with patch("keyring.set_password") as mock_set, \
         patch("keyring.get_password", return_value=test_password) as mock_get:
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

