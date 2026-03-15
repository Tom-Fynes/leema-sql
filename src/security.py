"""Security management for credentials and certificates."""

import keyring
from pathlib import Path
from typing import Optional


class SecurityManager:
    """Manages password storage and certificate paths using keyring."""

    KEYRING_SERVICE = "leema-sql"

    @staticmethod
    def store_password(connection_name: str, password: str) -> None:
        """Store a password securely in the system keyring.

        Args:
            connection_name: The connection profile name.
            password: The password to store.
        """
        keyring.set_password(SecurityManager.KEYRING_SERVICE,
                             connection_name, password)

    @staticmethod
    def retrieve_password(connection_name: str) -> Optional[str]:
        """Retrieve a password from the system keyring.

        Args:
            connection_name: The connection profile name.

        Returns:
            The stored password or None if not found.
        """
        return keyring.get_password(SecurityManager.KEYRING_SERVICE, connection_name)

    @staticmethod
    def delete_password(connection_name: str) -> None:
        """Delete a password from the system keyring.

        Args:
            connection_name: The connection profile name.
        """
        try:
            keyring.delete_password(
                SecurityManager.KEYRING_SERVICE, connection_name)
        except keyring.errors.PasswordDeleteError:
            pass  # Password doesn't exist

    @staticmethod
    def validate_cert_path(cert_path: str) -> bool:
        """Validate that a certificate file exists.

        Args:
            cert_path: Path to the certificate file.

        Returns:
            True if the file exists and is readable.
        """
        path = Path(cert_path)
        return path.exists() and path.is_file() and path.stat().st_size > 0
