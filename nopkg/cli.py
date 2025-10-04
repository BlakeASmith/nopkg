"""Command-line interface for nopkg."""

import click
from pathlib import Path

from .core import install_module, uninstall_module, list_installed_modules, update_module
from .analysis import generate_usage_examples


def get_version():
    """Get version from package metadata."""
    try:
        from importlib.metadata import version
        return version("nopkg")
    except ImportError:
        # Fallback for Python < 3.8
        try:
            from importlib_metadata import version
            return version("nopkg")
        except ImportError:
            return "unknown"
    except Exception:
        return "unknown"


@click.group()
@click.version_option(version=get_version())
def cli():
    """Install Python modules without packaging setup."""
    pass


@cli.command()
@click.argument("source")
@click.option("-e", "--dev", is_flag=True, help="Development mode")
def install(source: str, dev: bool):
    """Install a Python module from a file, URL, or directory."""
    success, message, analysis_data = install_module(source, None, dev)
    
    if success:
        click.echo(click.style(message, fg='green'))
        
        # Display usage information if analysis data is available
        if analysis_data:
            module_name = Path(source).stem
            usage_examples = generate_usage_examples(module_name, analysis_data)
            
            if usage_examples:
                click.echo()
                click.echo(click.style("Usage:", fg='cyan', bold=True))
                for example in usage_examples:
                    if example.startswith('#'):
                        click.echo(click.style(example, fg='yellow'))
                    else:
                        click.echo(f"  {example}")
    else:
        click.echo(click.style(f"Error: {message}", fg='red'), err=True)
        raise click.ClickException("Installation failed")


@cli.command()
@click.argument("module_name")
def uninstall(module_name: str):
    """Uninstall a module installed by nopkg."""
    success, message = uninstall_module(module_name)
    
    if success:
        click.echo(click.style(message, fg='green'))
    else:
        click.echo(click.style(f"Error: {message}", fg='red'), err=True)
        raise click.ClickException("Uninstallation failed")


@cli.command()
def list():
    """List all modules installed by nopkg."""
    modules = list_installed_modules()
    
    if not modules:
        click.echo("No modules installed by nopkg")
    else:
        click.echo("Modules installed by nopkg:")
        for module in sorted(modules):
            click.echo(f"  {module}")


@cli.command()
@click.argument("module_name")
def update(module_name: str):
    """Update an installed module by reinstalling from its original source."""
    success, message = update_module(module_name)
    
    if success:
        click.echo(click.style(message, fg='green'))
    else:
        click.echo(click.style(f"Error: {message}", fg='red'), err=True)
        raise click.ClickException("Update failed")


@cli.command()
@click.argument("module_name")
def info(module_name: str):
    """Show information about an installed module."""
    from .core import _get_registry_path
    
    registry_path = _get_registry_path()
    
    if not registry_path.exists():
        click.echo(click.style(f"No information found for module '{module_name}'", fg='red'), err=True)
        return
    
    found = False
    with open(registry_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith(f"{module_name}|"):
                parts = line.split('|')
                if len(parts) >= 3:
                    name, source, mode = parts[0], parts[1], parts[2]
                    click.echo(f"Module: {name}")
                    click.echo(f"Source: {source}")
                    click.echo(f"Mode: {mode}")
                    found = True
                    break
    
    if not found:
        click.echo(click.style(f"Module '{module_name}' not found", fg='red'), err=True)


if __name__ == "__main__":
    cli()