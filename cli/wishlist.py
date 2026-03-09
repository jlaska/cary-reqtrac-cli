"""
Wishlist commands for Cary ReqTrac CLI.
"""

import logging
import sys

import click

from api_client_httpx import CaryReqTracClientHttpx
from session import SessionManager

logger = logging.getLogger(__name__)


def get_authenticated_client() -> CaryReqTracClientHttpx:
    """Get an authenticated client instance."""
    session_mgr = SessionManager()

    if not session_mgr.is_authenticated():
        click.echo("Error: Not authenticated. Run 'reqtrac auth login' first.", err=True)
        sys.exit(1)

    client = CaryReqTracClientHttpx()
    csrf_token = session_mgr.load_session_httpx(client)
    client.csrf_token = csrf_token
    client.is_authenticated = True

    return client


@click.group(context_settings={'help_option_names': ['-h', '--help']})
def wishlist():
    """Wishlist management commands."""
    pass


@wishlist.command()
@click.argument('program_id')
def add(program_id):
    """
    Add a program to wishlist.

    Arguments:
        program_id: The program FMID to add to wishlist

    Examples:
        reqtrac wishlist add 12345
    """
    client = get_authenticated_client()

    try:
        if client.add_to_wishlist(program_id):
            click.echo(f"✓ Added program {program_id} to wishlist")
        else:
            click.echo(f"Error: Failed to add program {program_id} to wishlist", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@wishlist.command()
def list():
    """
    List wishlist items (if supported by API).

    Note: This feature may not be implemented yet in the API client.
    """
    click.echo("Error: Wishlist listing not yet implemented", err=True)
    click.echo("Check the web interface to view your wishlist", err=True)
    sys.exit(1)
