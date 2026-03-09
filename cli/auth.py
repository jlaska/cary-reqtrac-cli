"""
Authentication commands for Cary ReqTrac CLI.
"""

import logging
import sys

import click

from api_client_httpx import CaryReqTracClientHttpx
from config import ConfigManager
from session import SessionManager

logger = logging.getLogger(__name__)


@click.group(context_settings={'help_option_names': ['-h', '--help']})
def auth():
    """Authentication commands."""
    pass


@auth.command()
@click.option('--username', '-u', help='Username (or set REQTRAC_USERNAME)')
@click.option('--password', '-p', help='Password (or set REQTRAC_PASSWORD)')
@click.pass_context
def login(ctx, username, password):
    """
    Login and save session.

    Credentials are loaded in this order:
    1. Command line options
    2. Environment variables (REQTRAC_USERNAME, REQTRAC_PASSWORD)
    3. Config file (~/.config/reqtrac/config.json)
    4. Interactive prompt
    """
    config = ConfigManager(ctx.obj.get('config_file'))
    session_mgr = SessionManager()

    # Get credentials from various sources
    if not username:
        username = config.get_username()
    if not password:
        password = config.get_password()

    # Prompt if still missing
    if not username:
        username = click.prompt('Username')
    if not password:
        password = click.prompt('Password', hide_input=True)

    if not username or not password:
        click.echo("Error: Username and password are required", err=True)
        sys.exit(1)

    # Create client and login
    click.echo("Logging in...")
    client = CaryReqTracClientHttpx()

    try:
        # Initialize session
        if not client.initialize_session():
            click.echo("Error: Failed to initialize session", err=True)
            sys.exit(1)

        # Attempt login
        if client.login(username, password):
            # Save session - httpx client uses .client instead of .session
            session_mgr.save_session_httpx(client.cookies, client.csrf_token)
            click.echo("✓ Login successful - session saved")
        else:
            click.echo("Error: Login failed - check credentials", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@auth.command()
def logout():
    """
    Logout and clear session.
    """
    session_mgr = SessionManager()
    client = CaryReqTracClientHttpx()

    # Load session if exists
    csrf_token = session_mgr.load_session_httpx(client)
    if csrf_token:
        client.csrf_token = csrf_token
        client.is_authenticated = True

        try:
            # Attempt to logout on server
            client.logout()
        except Exception as e:
            logger.warning(f"Server logout failed: {e}")

    # Clear local session
    session_mgr.clear_session()
    click.echo("✓ Logged out - session cleared")


@auth.command()
def status():
    """
    Show current authentication status.
    """
    session_mgr = SessionManager()
    config = ConfigManager()

    if session_mgr.is_authenticated():
        username = config.get_username() or "<not configured>"
        click.echo(f"✓ Authenticated")
        click.echo(f"  Username: {username}")
        click.echo(f"  Session: {session_mgr.session_file}")
    else:
        click.echo("✗ Not authenticated")
        click.echo("  Run 'reqtrac auth login' to login")
