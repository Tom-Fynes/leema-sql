"""Tests for security module."""

import pytest
from src.security import SecurityManager


def test_store_and_retrieve_password():
    """Test storing and retrieving passwords."""
    manager = SecurityManager()
    test_connection = "test_postgres_conn"
    test_password = "super_secret_password"

    # Store password
    manager.store_password(test_connection, test_password)

    # Retrieve password
    retrieved = manager.retrieve_password(test_connection)
    assert retrieved == test_password

    # Clean up
    manager.delete_password(test_connection)


def test_retrieve_nonexistent_password():
    """Test retrieving a password that doesn't exist."""
    manager = SecurityManager()
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
