"""
Shopping cart commands for Cary ReqTrac CLI.
"""

import json
import logging
import sys

import click
from bs4 import BeautifulSoup

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
def cart():
    """Shopping cart commands."""
    pass


@cart.command()
@click.argument('program_id')
@click.option('--begin-date', required=True, help='Begin date (MM/DD/YYYY)')
@click.option('--begin-time', required=True, help='Begin time in seconds (e.g., 43200 for 12:00 PM)')
@click.option('--end-date', required=True, help='End date (MM/DD/YYYY)')
@click.option('--end-time', required=True, help='End time in seconds')
def add(program_id, begin_date, begin_time, end_date, end_time):
    """
    Add program to cart with date/time selection.

    Arguments:
        program_id: The program FMID to add to cart

    Examples:
        reqtrac cart add 12345 \\
            --begin-date "07/13/2026" \\
            --begin-time "43200" \\
            --end-date "07/17/2026" \\
            --end-time "46800"
    """
    client = get_authenticated_client()

    try:
        # Step 1: Update selection with date/time
        click.echo(f"Setting up program {program_id} with dates...")
        if not client.update_selection(
            item_id=program_id,
            begin_date=begin_date,
            begin_time=begin_time,
            end_date=end_date,
            end_time=end_time
        ):
            click.echo("Error: Failed to update selection", err=True)
            sys.exit(1)

        # Step 2: Add to cart
        click.echo("Adding to cart...")
        if client.add_to_cart():
            click.echo(f"✓ Added program {program_id} to cart")
        else:
            click.echo("Error: Failed to add to cart", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cart.command()
@click.pass_context
def view(ctx):
    """
    View current cart contents.

    Examples:
        reqtrac cart view
        reqtrac cart view -o json
    """
    client = get_authenticated_client()
    output_format = ctx.obj.get('output', 'table')

    try:
        success, html = client.view_cart()

        if not success:
            click.echo("Error: Failed to retrieve cart", err=True)
            sys.exit(1)

        if output_format == 'raw':
            click.echo(html)
        elif output_format == 'json':
            # Parse HTML to extract cart items
            soup = BeautifulSoup(html, 'html.parser')
            # Simple extraction - can be enhanced
            data = {
                'html': html[:500]  # Truncated
            }
            click.echo(json.dumps(data, indent=2))
        else:
            # Table format
            soup = BeautifulSoup(html, 'html.parser')
            click.echo("\n=== Shopping Cart ===\n")

            # Look for cart items table
            tables = soup.find_all('table')
            if tables:
                rows = tables[0].find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if cells:
                        text = ' | '.join(cell.get_text(strip=True) for cell in cells)
                        click.echo(text)
            else:
                click.echo("Cart appears to be empty or could not be parsed")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cart.command()
@click.pass_context
def checkout(ctx):
    """
    Access checkout page.

    Examples:
        reqtrac cart checkout
        reqtrac cart checkout -o raw
    """
    client = get_authenticated_client()
    output_format = ctx.obj.get('output', 'table')

    try:
        success, html = client.get_checkout_page()

        if not success:
            click.echo("Error: Failed to access checkout", err=True)
            sys.exit(1)

        if output_format == 'raw':
            click.echo(html)
        elif output_format == 'json':
            soup = BeautifulSoup(html, 'html.parser')
            data = {
                'html': html[:500]  # Truncated
            }
            click.echo(json.dumps(data, indent=2))
        else:
            # Table format
            soup = BeautifulSoup(html, 'html.parser')
            click.echo("\n=== Checkout ===\n")
            click.echo("Checkout page accessed successfully")
            click.echo("Visit the web interface to complete checkout\n")

            # Extract any important information
            forms = soup.find_all('form')
            if forms:
                click.echo(f"Found {len(forms)} form(s) on checkout page")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
