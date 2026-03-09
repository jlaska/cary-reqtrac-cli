"""
Program search and info commands for Cary ReqTrac CLI.
"""

import fnmatch
import json
import logging
import sys

import click
from bs4 import BeautifulSoup

from api_client_httpx import CaryReqTracClientHttpx
from session import SessionManager

logger = logging.getLogger(__name__)


def _parse_item_details(soup: BeautifulSoup, program_id: str) -> dict:
    """Parse program details from item info page."""
    data = {'id': program_id}

    # Extract main heading (title)
    title_elem = soup.find('h1', class_='item-info__heading')
    if title_elem:
        data['title'] = title_elem.get_text(strip=True)

    # Extract full name with dates
    name_elem = soup.find('h2', class_='item-info-main-content__heading')
    if name_elem:
        data['name'] = name_elem.get_text(strip=True)

    # Extract description from first details text
    desc_elem = soup.find('div', class_='item-info__details-text')
    if desc_elem:
        # Get all text but clean up extra whitespace
        desc_text = desc_elem.get_text(separator=' ', strip=True)
        data['description'] = desc_text

    # Extract fee range
    fee_elem = soup.find('h3', class_='item-info-sidebar__heading')
    if fee_elem:
        fee_text = fee_elem.get_text(strip=True)
        if '$' in fee_text:
            data['fee'] = fee_text

    # Extract details from sidebar sections
    details = {}

    # Find all detail sections
    for details_div in soup.find_all('div', class_='item-info__details'):
        # Get heading
        heading_elem = details_div.find('h4', class_='item-info__details-heading')
        if heading_elem:
            heading = heading_elem.get_text(strip=True)
            # Get content
            text_elem = details_div.find('div', class_='item-info__details-text')
            if text_elem:
                # Clean up the text
                text = text_elem.get_text(separator=' ', strip=True)
                text = ' '.join(text.split())  # Normalize whitespace
                details[heading] = text

    # Extract from tables if present
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).rstrip(':')
                value = cells[1].get_text(strip=True)
                if label and value:
                    details[label] = value

    data['details'] = details

    return data


def _display_item_details(data: dict):
    """Display program details in a readable format."""
    click.echo()
    click.echo("=" * 70)

    # Title
    if 'title' in data:
        click.echo(f"  {data['title']}")
    click.echo("=" * 70)

    # ID
    click.echo(f"ID: {data['id']}")

    # Full name
    if 'name' in data:
        click.echo(f"Name: {data['name']}")

    # Fee
    if 'fee' in data:
        click.echo(f"Fee: {data['fee']}")

    click.echo()

    # Description
    if 'description' in data:
        click.echo("Description:")
        # Wrap long descriptions
        desc = data['description']
        import textwrap
        wrapped = textwrap.fill(desc, width=68, initial_indent="  ", subsequent_indent="  ")
        click.echo(wrapped)
        click.echo()

    # Details table
    if 'details' in data and data['details']:
        click.echo("Details:")
        max_label_len = max(len(label) for label in data['details'].keys())
        for label, value in data['details'].items():
            click.echo(f"  {label:<{max_label_len}} : {value}")

    click.echo("=" * 70)
    click.echo()


def get_authenticated_client() -> CaryReqTracClientHttpx:
    """
    Get an authenticated client instance.

    Returns:
        Authenticated CaryReqTracClientHttpx

    Raises:
        SystemExit if not authenticated
    """
    session_mgr = SessionManager()

    if not session_mgr.is_authenticated():
        click.echo("Error: Not authenticated. Run 'reqtrac auth login' first.", err=True)
        sys.exit(1)

    client = CaryReqTracClientHttpx()
    csrf_token = session_mgr.load_session_httpx(client)
    client.csrf_token = csrf_token
    client.is_authenticated = True

    return client


def format_search_results(
    results: list,
    output_format: str,
    total_count: int = None,
    limit: int = None
):
    """
    Format and display search results.

    Args:
        results: List of parsed program results
        output_format: Output format (table, json, raw)
        total_count: Total number of results available (may be more than returned)
        limit: Result limit if applied
    """
    if output_format == 'raw':
        click.echo("Error: --output raw not supported with pagination", err=True)
        return

    if output_format == 'json':
        click.echo(json.dumps(results, indent=2))
        return

    # Table format
    if not results:
        click.echo("No programs found")
        return

    # Show result count if different from total
    if total_count and total_count != len(results):
        if limit:
            click.echo(f"# Showing {len(results)} of {total_count} total results (limited to {limit})", err=True)
        else:
            click.echo(f"# Showing {len(results)} of {total_count} total results", err=True)

    # kubectl-style plain text table (no colors, no borders)
    # Determine column widths
    col_widths = {
        'id': 10,
        'activity': 14,
        'name': 50,
        'dates': 22,
        'location': 30,
        'status': 12
    }

    # Print header
    header = (
        f"{'ID':<{col_widths['id']}}  "
        f"{'ACTIVITY':<{col_widths['activity']}}  "
        f"{'NAME':<{col_widths['name']}}  "
        f"{'DATES':<{col_widths['dates']}}  "
        f"{'LOCATION':<{col_widths['location']}}  "
        f"{'STATUS':<{col_widths['status']}}"
    )
    click.echo(header)

    # Print rows
    for program in results:
        fmid = program.get('fmid', 'N/A')
        activity_num = program.get('activity_number', 'N/A')
        name = program.get('description') or program.get('name', 'N/A')
        dates = program.get('dates', '-')
        location = program.get('location', '-')
        status = program.get('status', '-')

        # Truncate long values to fit in columns
        name = (name[:col_widths['name']-3] + '...') if len(name) > col_widths['name'] else name
        location = (location[:col_widths['location']-3] + '...') if len(location) > col_widths['location'] else location

        row = (
            f"{fmid:<{col_widths['id']}}  "
            f"{activity_num:<{col_widths['activity']}}  "
            f"{name:<{col_widths['name']}}  "
            f"{dates:<{col_widths['dates']}}  "
            f"{location:<{col_widths['location']}}  "
            f"{status:<{col_widths['status']}}"
        )
        click.echo(row)


@click.group(context_settings={'help_option_names': ['-h', '--help']})
def programs():
    """Program search and information commands."""
    pass


@programs.command()
@click.option('--keyword', '-k', help='Search keyword')
@click.option('--location', '-l', multiple=True, help='Location filter - supports glob patterns (*, ?, [])')
@click.option('--instructor', '-i', multiple=True, help='Instructor ID filter - supports glob patterns (use "programs instructors" to find IDs)')
@click.option('--age', '-a', type=int, help='Age filter')
@click.option('--month', '-m', type=int, help='Beginning month (1-12)')
@click.option('--page', '-p', type=int, help='Fetch specific page only (overrides --limit)')
@click.option('--limit', type=int, default=50, help='Limit total results returned (default: 50, use 0 for unlimited)')
@click.pass_context
def search(ctx, keyword, location, instructor, age, month, page, limit):
    """
    Search for programs with filters.

    By default, returns up to 50 results (fetches pages until limit reached).
    Use --limit 0 for unlimited results, or --page to fetch a specific page.

    Supports multiple locations/instructors and glob patterns.

    NOTE: Instructor filter uses instructor IDs, not display names.
    Use 'reqtrac programs instructors' to find IDs.

    Examples:
        reqtrac programs search --keyword TENNIS
        reqtrac programs search -k CAMP -l "Bond*"
        reqtrac programs search -i "GWilliams" --keyword TENNIS
        reqtrac programs search -i "*Williams*" --keyword TENNIS
        reqtrac programs search -l "The Hive" -i "*Smith*" --age 10

        # Pagination examples
        reqtrac programs search -a 10                    # First 50 results (default)
        reqtrac programs search -a 10 --limit 0          # All results (may be slow)
        reqtrac programs search -a 10 --limit 100        # First 100 results
        reqtrac programs search -a 10 --page 1           # Only first page (25 results)
        reqtrac programs search -a 10 --page 2           # Second page (25 results)

    Location patterns:
        -l "The Hive"          # Exact location name
        -l "Bond*"             # All Bond Park locations
        -l "*Tennis*"          # All tennis facilities

    Instructor patterns:
        -i "GWilliams"         # Exact instructor ID
        -i "*Williams*"        # All Williams instructors (by name or ID)
        -i "J*"                # All instructors with ID starting with J
    """
    client = get_authenticated_client()
    output_format = ctx.obj.get('output', 'table')

    # Expand glob patterns in locations
    expanded_locations = None
    if location:
        expanded_locations = []
        all_locations = None  # Load once if needed

        for loc_pattern in location:
            # Check if this is a glob pattern
            has_glob = any(c in loc_pattern for c in ['*', '?', '[', ']'])

            if has_glob:
                # Need to expand glob pattern
                if all_locations is None:
                    all_locations = client.get_locations()

                # Match pattern against all locations
                matched = [
                    loc for loc in all_locations
                    if fnmatch.fnmatch(loc.lower(), loc_pattern.lower())
                ]

                if not matched:
                    click.echo(f"Warning: No locations match pattern '{loc_pattern}'", err=True)
                else:
                    expanded_locations.extend(matched)
            else:
                # Use as-is (exact location name)
                expanded_locations.append(loc_pattern)

        # Remove duplicates while preserving order
        seen = set()
        expanded_locations = [x for x in expanded_locations if not (x in seen or seen.add(x))]

    # Expand glob patterns in instructors
    expanded_instructors = None
    if instructor:
        expanded_instructors = []
        all_instructors = None  # Load once if needed

        for inst_pattern in instructor:
            # Check if this is a glob pattern
            has_glob = any(c in inst_pattern for c in ['*', '?', '[', ']'])

            if has_glob:
                # Need to expand glob pattern
                if all_instructors is None:
                    all_instructors = client.get_instructors()

                # Match pattern against instructor names or values
                matched = []
                for inst in all_instructors:
                    # Match against either the name (display) or value (ID)
                    if (fnmatch.fnmatch(inst['name'].lower(), inst_pattern.lower()) or
                        fnmatch.fnmatch(inst['value'].lower(), inst_pattern.lower())):
                        matched.append(inst['value'])

                if not matched:
                    click.echo(f"Warning: No instructors match pattern '{inst_pattern}'", err=True)
                else:
                    expanded_instructors.extend(matched)
            else:
                # Use as-is (exact instructor ID)
                expanded_instructors.append(inst_pattern)

        # Remove duplicates while preserving order
        seen = set()
        expanded_instructors = [x for x in expanded_instructors if not (x in seen or seen.add(x))]

    try:
        # Determine pagination strategy
        if page is not None:
            # Fetch specific page only (--page overrides --limit)
            success, html = client.search_programs(
                keyword=keyword,
                locations=expanded_locations,
                instructors=expanded_instructors,
                age=age,
                begin_month=month,
                page=page,
                display='detail'
            )

            if not success:
                click.echo("Error: Search failed", err=True)
                sys.exit(1)

            # Parse results from HTML
            results = client.parse_search_results(html)
            metadata = client.parse_pagination_metadata(html)
            total_count = metadata['total'] if metadata else len(results)

        else:
            # Fetch pages until limit reached (or all if limit=0)
            max_results = None if limit == 0 else limit

            success, results, total_count = client.search_programs_paginated(
                keyword=keyword,
                locations=expanded_locations,
                instructors=expanded_instructors,
                age=age,
                begin_month=month,
                max_results=max_results
            )

            if not success:
                click.echo("Error: Search failed", err=True)
                sys.exit(1)

        # Format and display
        format_search_results(results, output_format, total_count, limit if limit > 0 else None)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@programs.command()
@click.option('--search', '-s', help='Search/filter instructors by pattern (supports glob: *, ?, [])')
@click.pass_context
def instructors(ctx, search):
    """
    List all available instructors.

    Use --search to filter instructors using glob patterns:
    - Exact match: "Smith, John" matches only that instructor
    - Contains: "*Mary*" matches any instructor with "Mary" in name
    - Prefix: "Smith*" matches all Smiths
    - Value match: "JSmith" matches by instructor ID

    Examples:
        reqtrac programs instructors
        reqtrac programs instructors --search "*Smith*"
        reqtrac programs instructors -s "*Mary*"
    """
    client = get_authenticated_client()

    try:
        all_instructors = client.get_instructors()

        if not all_instructors:
            click.echo("No instructors found")
            return

        # Filter if search term provided
        has_glob = False
        if search:
            # Check if pattern contains glob characters
            has_glob = any(c in search for c in ['*', '?', '[', ']'])

            if has_glob:
                # Use glob pattern matching (case-insensitive)
                filtered_instructors = [
                    inst for inst in all_instructors
                    if (fnmatch.fnmatch(inst['name'].lower(), search.lower()) or
                        fnmatch.fnmatch(inst['value'].lower(), search.lower()))
                ]
                match_type = "glob pattern"
            else:
                # Exact match for simple strings (case-insensitive)
                filtered_instructors = [
                    inst for inst in all_instructors
                    if (inst['name'].lower() == search.lower() or
                        inst['value'].lower() == search.lower())
                ]
                match_type = "exact match"
        else:
            filtered_instructors = all_instructors
            match_type = "all"

        if not filtered_instructors:
            click.echo(f"No instructors matching '{search}'")
            if search and not has_glob:
                click.echo(f"Tip: Try a glob pattern like '*{search}*' to match instructors containing '{search}'")
            return

        # Display instructors in kubectl-style format
        click.echo(f"{'INSTRUCTOR':<50}  {'ID':<15}")

        for inst in filtered_instructors:
            click.echo(f"{inst['name']:<50}  {inst['value']:<15}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@programs.command()
@click.option('--search', '-s', help='Search/filter locations by pattern (supports glob: *, ?, [])')
@click.pass_context
def locations(ctx, search):
    """
    List all available locations.

    Use --search to filter locations using glob patterns:
    - Exact match: "Bond" matches only "Bond"
    - Prefix: "Bond*" matches "Bond Park...", "Bond Park Community Center", etc.
    - Suffix: "*Park" matches "Downtown Cary Park", "Middle Creek Park", etc.
    - Contains: "*Creek*" matches any location with "Creek"
    - Multiple chars: "?ark" matches "Park", "Dark", etc.
    - Character class: "[BM]ond*" matches "Bond..." or "Mond..."

    Examples:
        reqtrac programs locations
        reqtrac programs locations --search "Bond*"
        reqtrac programs locations -s "*Tennis*"
        reqtrac programs locations -s "*Community Center"
    """
    client = get_authenticated_client()

    try:
        all_locations = client.get_locations()

        if not all_locations:
            click.echo("No locations found")
            return

        # Filter if search term provided
        has_glob = False
        if search:
            # Check if pattern contains glob characters
            has_glob = any(c in search for c in ['*', '?', '[', ']'])

            if has_glob:
                # Use glob pattern matching (case-insensitive)
                filtered_locations = [
                    loc for loc in all_locations
                    if fnmatch.fnmatch(loc.lower(), search.lower())
                ]
                match_type = "glob pattern"
            else:
                # Exact match for simple strings (case-insensitive)
                filtered_locations = [
                    loc for loc in all_locations
                    if loc.lower() == search.lower()
                ]
                match_type = "exact match"
        else:
            filtered_locations = all_locations
            match_type = "all"

        if not filtered_locations:
            click.echo(f"No locations matching '{search}'")
            if search and not has_glob:
                click.echo(f"Tip: Try a glob pattern like '{search}*' to match locations starting with '{search}'")
            return

        # Display locations in kubectl-style format
        click.echo(f"{'LOCATION':<70}")

        for loc in filtered_locations:
            click.echo(f"{loc:<70}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@programs.command()
@click.argument('program_id')
@click.pass_context
def get(ctx, program_id):
    """
    Get details for a specific program ID.

    Arguments:
        program_id: The program FMID to retrieve

    Examples:
        reqtrac programs get 12345
        reqtrac programs get 12345 -o json
    """
    client = get_authenticated_client()
    output_format = ctx.obj.get('output', 'table')

    try:
        success, html = client.get_item_info(program_id)

        if not success:
            click.echo(f"Error: Failed to get program {program_id}", err=True)
            sys.exit(1)

        if output_format == 'raw':
            click.echo(html)
        elif output_format == 'json':
            # Parse HTML to extract structured data
            soup = BeautifulSoup(html, 'html.parser')
            data = _parse_item_details(soup, program_id)
            click.echo(json.dumps(data, indent=2))
        else:
            # Table format - extract and display key info
            soup = BeautifulSoup(html, 'html.parser')
            data = _parse_item_details(soup, program_id)
            _display_item_details(data)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
