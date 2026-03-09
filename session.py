"""
Session persistence for Cary ReqTrac CLI.

Handles saving and loading session cookies and CSRF tokens.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages persistent session storage for the CLI."""

    def __init__(self, session_file: Optional[Path] = None):
        """
        Initialize session manager.

        Args:
            session_file: Path to session file (default: ~/.config/reqtrac/session.json)
        """
        if session_file is None:
            config_dir = Path.home() / ".config" / "reqtrac"
            config_dir.mkdir(parents=True, exist_ok=True)
            session_file = config_dir / "session.json"

        self.session_file = session_file

    def save_session(
        self,
        session: Any,  # requests.Session
        csrf_token: Optional[str] = None
    ) -> bool:
        """
        Save session cookies and CSRF token to file.

        Args:
            session: The requests Session to save
            csrf_token: CSRF token to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize cookies from session
            cookies_dict = dict(session.cookies)

            session_data = {
                'cookies': cookies_dict,
                'csrf_token': csrf_token
            }

            # Write to file
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            logger.debug(f"Session saved to {self.session_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session(self, session: Any) -> Optional[str]:  # requests.Session
        """
        Load session cookies and CSRF token from file.

        Args:
            session: The requests Session to populate

        Returns:
            CSRF token if found, None otherwise
        """
        try:
            if not self.session_file.exists():
                logger.debug("No session file found")
                return None

            with open(self.session_file, 'r') as f:
                session_data = json.load(f)

            # Restore cookies
            cookies_dict = session_data.get('cookies', {})
            for name, value in cookies_dict.items():
                session.cookies.set(name, value)

            csrf_token = session_data.get('csrf_token')

            logger.debug(f"Session loaded from {self.session_file}")
            return csrf_token

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def clear_session(self) -> bool:
        """
        Clear saved session by deleting the session file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.debug(f"Session file deleted: {self.session_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if a valid session exists.

        Returns:
            True if session file exists, False otherwise
        """
        return self.session_file.exists()

    def save_session_httpx(
        self,
        cookies: Dict[str, str],
        csrf_token: Optional[str] = None
    ) -> bool:
        """
        Save httpx client cookies and CSRF token to file.

        Args:
            cookies: Dictionary of cookies
            csrf_token: CSRF token to save

        Returns:
            True if successful, False otherwise
        """
        try:
            session_data = {
                'cookies': cookies,
                'csrf_token': csrf_token
            }

            # Write to file
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            logger.debug(f"Session saved to {self.session_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session_httpx(self, client: Any) -> Optional[str]:  # CaryReqTracClientHttpx
        """
        Load session cookies and CSRF token for httpx client.

        Args:
            client: The httpx client to populate

        Returns:
            CSRF token if found, None otherwise
        """
        try:
            if not self.session_file.exists():
                logger.debug("No session file found")
                return None

            with open(self.session_file, 'r') as f:
                session_data = json.load(f)

            # Restore cookies
            cookies_dict = session_data.get('cookies', {})
            client.set_cookies(cookies_dict)

            csrf_token = session_data.get('csrf_token')

            logger.debug(f"Session loaded from {self.session_file}")
            return csrf_token

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
