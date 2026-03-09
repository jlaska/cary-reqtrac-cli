"""
Utility functions for CLI commands.
"""

import asyncio
import logging
import sys
from typing import Optional

import click

from session import SessionManager

logger = logging.getLogger(__name__)


def get_authenticated_client(use_playwright: bool = False):
    """
    Get an authenticated client instance.

    Args:
        use_playwright: Use Playwright client instead of requests

    Returns:
        Authenticated client (CaryReqTracClient or CaryReqTracClientPlaywright)

    Raises:
        SystemExit if not authenticated
    """
    if use_playwright:
        click.echo("Error: Playwright mode not yet implemented in CLI", err=True)
        click.echo("Workaround: Use the Playwright client directly via Python", err=True)
        sys.exit(1)

    # Use requests-based client
    from api_client import CaryReqTracClient

    session_mgr = SessionManager()

    if not session_mgr.is_authenticated():
        click.echo("Error: Not authenticated. Run 'reqtrac auth login' first.", err=True)
        sys.exit(1)

    client = CaryReqTracClient()
    csrf_token = session_mgr.load_session(client.session)
    client.csrf_token = csrf_token
    client.is_authenticated = True

    return client
