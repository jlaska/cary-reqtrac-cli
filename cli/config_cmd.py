"""
Configuration commands for Cary ReqTrac CLI.
"""

import json
import logging
import sys

import click

from config import ConfigManager

logger = logging.getLogger(__name__)


@click.group(context_settings={'help_option_names': ['-h', '--help']})
def config():
    """Configuration management commands."""
    pass


@config.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def set(ctx, key, value):
    """
    Set a configuration value.

    Arguments:
        key: Configuration key (e.g., username, password, base_url)
        value: Configuration value

    Examples:
        reqtrac config set username myuser
        reqtrac config set password mypassword
        reqtrac config set base_url https://custom.url.com
    """
    config_mgr = ConfigManager(ctx.obj.get('config_file'))

    try:
        if config_mgr.set(key, value):
            click.echo(f"✓ Set {key} = {value if key != 'password' else '********'}")
        else:
            click.echo(f"Error: Failed to set {key}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@config.command()
@click.pass_context
def show(ctx):
    """
    Show current configuration.

    Passwords are masked in output.

    Examples:
        reqtrac config show
    """
    config_mgr = ConfigManager(ctx.obj.get('config_file'))

    try:
        config_data = config_mgr.show_config()

        if not config_data:
            click.echo("No configuration set")
            click.echo(f"Config file: {config_mgr.config_file}")
            return

        click.echo("\n=== Configuration ===\n")
        click.echo(f"Config file: {config_mgr.config_file}\n")

        for key, value in config_data.items():
            click.echo(f"{key}: {value}")

        click.echo("\nNote: Environment variables (REQTRAC_*) override config file values")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
