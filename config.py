"""
Configuration management for Cary ReqTrac CLI.

Handles loading config from file and environment variables.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration for the CLI."""

    DEFAULT_BASE_URL = "https://nccaryweb.myvscloud.com"

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_file: Path to config file (default: ~/.config/reqtrac/config.json)
        """
        if config_file is None:
            config_dir = Path.home() / ".config" / "reqtrac"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                logger.debug(f"Config loaded from {self.config_file}")
            else:
                logger.debug("No config file found, using defaults")
                self._config = {}

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = {}

    def _save_config(self) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.debug(f"Config saved to {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a config value with environment variable override.

        Environment variables take precedence over config file.
        Format: REQTRAC_<KEY> (uppercased)

        Args:
            key: Config key
            default: Default value if not found

        Returns:
            Config value
        """
        # Check environment variable first
        env_key = f"REQTRAC_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value

        # Fall back to config file
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Set a config value and save to file.

        Args:
            key: Config key
            value: Config value

        Returns:
            True if successful, False otherwise
        """
        self._config[key] = value
        return self._save_config()

    def get_username(self) -> Optional[str]:
        """Get username from config or environment."""
        return self.get('username')

    def get_password(self) -> Optional[str]:
        """Get password from config or environment."""
        return self.get('password')

    def get_base_url(self) -> str:
        """Get base URL from config or environment."""
        return self.get('base_url', self.DEFAULT_BASE_URL)

    def show_config(self) -> Dict[str, Any]:
        """
        Get all config values (with password masked).

        Returns:
            Dictionary of config values
        """
        config_copy = self._config.copy()

        # Mask password if present
        if 'password' in config_copy:
            config_copy['password'] = '********'

        return config_copy
