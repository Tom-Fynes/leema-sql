"""Configuration management for Leema."""
import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ConnectionProfile:
    """Database connection profile."""
    name: str
    engine: str
    host: str
    port: int
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False
    options: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate connection profile.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.name:
            errors.append("Profile name is required")

        if not self.engine:
            errors.append("Engine type is required")

        if not self.host:
            errors.append("Host is required")

        if not isinstance(self.port, int) or self.port <= 0 or self.port > 65535:
            errors.append(f"Invalid port number: {self.port}")

        if not self.database and self.engine != "duckdb":
            errors.append("Database name is required")

        return errors


@dataclass
class LeemaConfig:
    """Main Leema configuration."""
    profiles: Dict[str, ConnectionProfile] = field(default_factory=dict)
    default_profile: Optional[str] = None
    config_path: Optional[Path] = None

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "LeemaConfig":
        """Load configuration from file.

        Args:
            config_path: Path to config file. If None, uses XDG_CONFIG_HOME.

        Returns:
            LeemaConfig instance.

        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        path = cls._resolve_config_path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        # Parse profiles
        profiles = {}
        for name, profile_data in data.get('profiles', {}).items():
            profile_data['name'] = name
            profiles[name] = ConnectionProfile(**profile_data)

        config = cls(
            profiles=profiles,
            default_profile=data.get('default_profile'),
            config_path=path
        )

        # Validate configuration
        errors = config.validate()
        if errors:
            error_msg = "\n".join(errors)
            raise ValueError(f"Configuration validation failed:\n{error_msg}")

        return config

    def save(self, config_path: Optional[str] = None) -> None:
        """Save configuration to file.

        Args:
            config_path: Path to save config. If None, uses stored path or XDG default.
        """
        path = self._resolve_config_path(
            config_path) if config_path else self.config_path

        if not path:
            path = self._resolve_config_path(None)

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        data = {
            'default_profile': self.default_profile,
            'profiles': {}
        }

        for name, profile in self.profiles.items():
            profile_dict = asdict(profile)
            profile_dict.pop('name')  # Don't duplicate name
            profile_dict.pop('password', None)  # Never save passwords
            data['profiles'][name] = profile_dict

        # Write YAML
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        self.config_path = path

    def validate(self) -> list[str]:
        """Validate entire configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Validate each profile
        for name, profile in self.profiles.items():
            profile_errors = profile.validate()
            for error in profile_errors:
                errors.append(f"Profile '{name}': {error}")

        # Validate default profile exists
        if self.default_profile and self.default_profile not in self.profiles:
            errors.append(
                f"Default profile '{self.default_profile}' does not exist")

        return errors

    @staticmethod
    def _resolve_config_path(config_path: Optional[str] = None) -> Path:
        """Resolve configuration file path using XDG Base Directory specification.

        Args:
            config_path: Explicit path to config file.

        Returns:
            Resolved Path object.
        """
        if config_path:
            return Path(config_path).expanduser().resolve()

        # Use XDG_CONFIG_HOME if set, otherwise ~/.config
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')

        if xdg_config_home:
            config_dir = Path(xdg_config_home)
        else:
            config_dir = Path.home() / '.config'

        return config_dir / 'leema' / 'config.yaml'

    @staticmethod
    def get_default_config_path() -> Path:
        """Get the default configuration file path.

        Returns:
            Path to default config file location.
        """
        return LeemaConfig._resolve_config_path(None)
