"""
Main CLI entry point for Cary ReqTrac.

Provides kubectl-style command structure for interacting with the API.
"""

import logging
import sys

import click

from cli import auth, programs, wishlist, cart, config_cmd


# Configure logging
def setup_logging(verbose: int = 0):
    """
    Setup logging configuration.

    Args:
        verbose: Verbosity level
            0 = WARNING and above (clean)
            1 = INFO (shows progress)
            2+ = DEBUG (shows all details)
    """
    if verbose == 0:
        level = logging.WARNING  # Clean output
    elif verbose == 1:
        level = logging.INFO      # Show what's happening
    else:
        level = logging.DEBUG     # Show all details

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Override any existing configuration
    )


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('--verbose', '-v', count=True, help='Increase verbosity (-v for INFO, -vv for DEBUG)')
@click.option('--debug', is_flag=True, help='Enable debug logging (same as -vv)')
@click.option(
    '--output',
    '-o',
    type=click.Choice(['table', 'json', 'raw']),
    default='table',
    help='Output format'
)
@click.option(
    '--config',
    '-c',
    type=click.Path(),
    help='Config file path (default: ~/.config/reqtrac/config.json)'
)
@click.pass_context
def cli(ctx, verbose, debug, output, config):
    """
    Cary ReqTrac CLI - kubectl-style CLI for recreation program registration.

    Examples:
        reqtrac auth login
        reqtrac programs search --keyword TENNIS
        reqtrac cart add <program-id>
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Determine verbosity level
    verbosity = verbose
    if debug:
        verbosity = max(verbosity, 2)  # --debug sets to DEBUG level

    # Setup logging
    setup_logging(verbosity)

    # Store global options in context
    ctx.obj['verbose'] = verbosity
    ctx.obj['output'] = output
    ctx.obj['config_file'] = config


# Register command groups
cli.add_command(auth.auth)
cli.add_command(programs.programs)
cli.add_command(wishlist.wishlist)
cli.add_command(cart.cart)
cli.add_command(config_cmd.config)


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
