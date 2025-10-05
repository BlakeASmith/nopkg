"""Command-line interface for nopkg."""

import click
import fnmatch
import glob
from pathlib import Path
from typing import List

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
@click.argument("sources", nargs=-1, required=True)
@click.option("-e", "--dev", is_flag=True, help="Development mode")
def install(sources: tuple, dev: bool):
    """Install Python modules or packages from files or directories.
    If a module is already installed by nopkg, it will be updated instead.
    
    Supports glob patterns and multiple arguments:
    nopkg install *.py          # all .py files
    nopkg install one.py two.py # multiple specific files
    nopkg install my_package/   # directory
    """
    expanded_sources = _expand_patterns(
        sources,
        glob_func=glob.glob,
        exists_func=lambda path: Path(path).exists()
    )
    
    if not expanded_sources:
        click.echo(click.style("Error: No files found matching the provided patterns", fg='red'), err=True)
        raise click.ClickException("Installation failed")
    
    success_count = 0
    failure_count = 0
    
    for source in expanded_sources:
        click.echo(f"Installing {source}...")
        success, message, analysis_data = install_module(source, dev)
        
        if success:
            success_count += 1
            click.echo(click.style(f"  ✓ {message}", fg='green'))
            
            if analysis_data:
                source_path = Path(source)
                module_name = source_path.name if source_path.is_dir() else source_path.stem
                usage_examples = generate_usage_examples(module_name, analysis_data)
                
                if usage_examples:
                    click.echo()
                    click.echo(click.style(f"  Usage for {module_name}:", fg='cyan', bold=True))
                    for example in usage_examples:
                        if example.startswith('#'):
                            click.echo(click.style(f"    {example}", fg='yellow'))
                        else:
                            click.echo(f"    {example}")
                    click.echo()
        else:
            failure_count += 1
            click.echo(click.style(f"  ✗ Error: {message}", fg='red'), err=True)
    
    if failure_count > 0 and success_count == 0:
        raise click.ClickException("All installations failed")
    elif failure_count > 0:
        click.echo(click.style(f"\nCompleted with {success_count} successful, {failure_count} failed", fg='yellow'))


@cli.command()
@click.argument("module_names", nargs=-1, required=True)
def uninstall(module_names: tuple):
    """Uninstall modules or packages installed by nopkg.
    
    Supports glob patterns and multiple arguments:
    nopkg uninstall *           # uninstall everything
    nopkg uninstall foo.py bar  # multiple specific modules
    nopkg uninstall my_*        # glob pattern matching
    """
    from .core import list_installed_modules
    
    installed_modules = list_installed_modules()
    expanded_modules = _expand_patterns(
        module_names,
        glob_func=lambda pattern: [mod for mod in installed_modules if fnmatch.fnmatch(mod, pattern)],
        exists_func=lambda name: (name.replace('.py', '') if name.endswith('.py') else name) in installed_modules,
        all_items_func=lambda: installed_modules
    )
    
    if not expanded_modules:
        click.echo(click.style("Error: No modules found matching the provided patterns", fg='red'), err=True)
        raise click.ClickException("Uninstallation failed")
    
    success_count = 0
    failure_count = 0
    
    for module_name in expanded_modules:
        click.echo(f"Uninstalling {module_name}...")
        success, message = uninstall_module(module_name)
        
        if success:
            success_count += 1
            click.echo(click.style(f"  ✓ {message}", fg='green'))
        else:
            failure_count += 1
            click.echo(click.style(f"  ✗ Error: {message}", fg='red'), err=True)
    
    if failure_count > 0 and success_count == 0:
        raise click.ClickException("All uninstallations failed")
    elif failure_count > 0:
        click.echo(click.style(f"\nCompleted with {success_count} successful, {failure_count} failed", fg='yellow'))


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


def _expand_patterns(patterns: tuple, glob_func, exists_func, all_items_func=None) -> List[str]:
    """Expand patterns using provided matching functions.
    
    Args:
        patterns: Tuple of pattern strings
        glob_func: Function to expand glob patterns (pattern -> List[str])
        exists_func: Function to check if literal item exists (item -> bool) 
        all_items_func: Optional function to get all items for '*' pattern (-> List[str])
    """
    expanded = []
    
    for pattern in patterns:
        if all_items_func and pattern == '*':
            # Special case: all available items
            expanded.extend(all_items_func())
        elif '*' in pattern or '?' in pattern or '[' in pattern:
            # It's a glob pattern
            matches = glob_func(pattern)
            if matches:
                expanded.extend(sorted(matches))
        else:
            # It's a literal item - check if it exists
            if exists_func(pattern):
                # For modules, we want the normalized name (without .py)
                if all_items_func:  # This means we're dealing with modules
                    module_name = pattern.replace('.py', '') if pattern.endswith('.py') else pattern
                    expanded.append(module_name)
                else:
                    expanded.append(pattern)
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for item in expanded:
        if item not in seen:
            seen.add(item)
            result.append(item)
    
    return result


if __name__ == "__main__":
    cli()
