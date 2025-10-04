"""Core functionality for nopkg module installation."""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from .analysis import analyze_module


def get_site_packages_dir(python_executable: str = sys.executable) -> Optional[Path]:
    """Get the site-packages directory for a specific Python interpreter.
    
    Args:
        python_executable: Path to the Python executable to query
    """
    try:
        result = subprocess.run(
            [python_executable, "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            site_packages_path = Path(result.stdout.strip())
            if site_packages_path.exists():
                return site_packages_path
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    
    return None


def install_module(source: str, name: Optional[str] = None, dev_mode: bool = False, python_executable: str = sys.executable) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Install a Python module from a source (file path or directory).
    
    Args:
        source: Source path (local file or directory)
        name: Optional custom name for the module
        dev_mode: If True, use .pth file instead of copying
        python_executable: Path to the Python executable to install for
        
    Returns:
        Tuple of (success, message, analysis_data)
    """
    site_packages = get_site_packages_dir(python_executable)
    if site_packages is None:
        return False, "Could not determine site-packages directory", None
    
    source_path = Path(source)
    
    # Handle directory installation
    if source_path.is_dir():
        success, message = _install_directory(source_path, site_packages, name, dev_mode)
        return success, message, None  # Directory analysis not implemented yet
    
    # Handle single file installation
    if not source_path.exists():
        return False, f"Source file not found: {source}", None
    
    # Determine module name
    module_name = name if name else source_path.stem
    
    # Install the module
    target_path = site_packages / f"{module_name}.py"
    
    try:
        if target_path.exists():
            # Check if it's already managed by nopkg
            existing_modules = _get_registered_modules()
            if module_name in existing_modules:
                return False, f"Module '{module_name}' is already installed by nopkg. Use 'nopkg uninstall {module_name}' first.", None
            else:
                return False, f"Module '{module_name}' already exists (not managed by nopkg)", None
        
        if dev_mode:
            # Create .pth file for development mode
            pth_filename = f"nopkg_{module_name}.pth"
            pth_path = site_packages / pth_filename
            
            # Write the .pth file with the absolute path to the source directory
            # (source_path is always a file at this point)
            pth_content = str(source_path.parent.absolute())
            pth_path.write_text(pth_content + "\n")
        else:
            # Copy the file
            shutil.copy2(source_path, target_path)
        
        # Register the installation
        _register_module(module_name, source, dev_mode)
        
        # Analyze the installed module for usage information
        analysis_data = analyze_module(target_path)
        
        return True, f"Successfully installed module '{module_name}'", analysis_data
        
    except PermissionError:
        return False, f"Permission denied: cannot write to {site_packages}", None
    except FileNotFoundError:
        return False, f"Source file not found: {source}", None
    except OSError as e:
        return False, f"System error during installation: {e}", None
    except Exception as e:
        return False, f"Failed to install module: {e}", None


def _install_directory(source_dir: Path, site_packages: Path, name: Optional[str], dev_mode: bool) -> Tuple[bool, str]:
    """Install all Python files from a directory."""
    python_files = list(source_dir.glob("*.py"))
    if not python_files:
        return False, f"No Python files found in {source_dir}"
    
    installed = []
    for py_file in python_files:
        module_name = py_file.stem
        target_path = site_packages / f"{module_name}.py"
        
        try:
            if target_path.exists():
                continue  # Skip existing modules
            
            if dev_mode:
                # Create .pth file for development mode
                pth_filename = f"nopkg_{module_name}.pth"
                pth_path = site_packages / pth_filename
                # Add the parent directory to path so the module can be imported
                pth_content = str(py_file.parent.absolute())
                pth_path.write_text(pth_content + "\n")
            else:
                shutil.copy2(py_file, target_path)
            
            _register_module(module_name, str(py_file), dev_mode)
            installed.append(module_name)
            
        except Exception as e:
            continue  # Skip files that fail to install
    
    if not installed:
        return False, "No modules were installed"
    
    return True, f"Successfully installed modules: {', '.join(installed)}"


def uninstall_module(module_name: str, python_executable: str = sys.executable) -> Tuple[bool, str]:
    """Uninstall a module installed by nopkg."""
    site_packages = get_site_packages_dir(python_executable)
    if site_packages is None:
        return False, "Could not determine site-packages directory"
    
    target_path = site_packages / f"{module_name}.py"
    pth_path = site_packages / f"nopkg_{module_name}.pth"
    
    # Check if either the module file or .pth file exists
    if not target_path.exists() and not pth_path.exists():
        return False, f"Module {module_name} is not installed"
    
    try:
        removed_something = False
        
        # Remove the module file if it exists
        if target_path.exists():
            target_path.unlink()
            removed_something = True
        
        # Remove the .pth file if it exists (dev mode installation)
        if pth_path.exists():
            pth_path.unlink()
            removed_something = True
        
        if removed_something:
            _unregister_module(module_name)
            return True, f"Successfully uninstalled module '{module_name}'"
        else:
            return False, f"No files found for module '{module_name}'"
            
    except PermissionError:
        return False, f"Permission denied: cannot remove files for {module_name}"
    except Exception as e:
        return False, f"Failed to uninstall module: {e}"


def list_installed_modules() -> List[str]:
    """List all modules installed by nopkg."""
    return _get_registered_modules()


def update_module(module_name: str) -> Tuple[bool, str]:
    """Update an installed module by reinstalling from its original source."""
    # Find the module in the registry
    registry_path = _get_registry_path()
    if not registry_path.exists():
        return False, f"Module '{module_name}' not found"
    
    module_info = None
    with open(registry_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith(f"{module_name}|"):
                parts = line.split('|')
                if len(parts) >= 3:
                    module_info = {
                        'name': parts[0],
                        'source': parts[1],
                        'mode': parts[2]
                    }
                break
    
    if not module_info:
        return False, f"Module '{module_name}' not found in registry"
    
    # Uninstall the existing module
    success, message = uninstall_module(module_name)
    if not success:
        return False, f"Failed to uninstall existing module: {message}"
    
    # Reinstall with the same settings
    dev_mode = module_info['mode'] == 'dev'
    success, message, _ = install_module(module_info['source'], module_name, dev_mode)
    
    if success:
        return True, f"Successfully updated module '{module_name}'"
    else:
        return False, f"Failed to reinstall module: {message}"


def _get_registry_path() -> Path:
    """Get the path to the nopkg registry file."""
    # Store registry in user's home directory
    home = Path.home()
    nopkg_dir = home / ".nopkg"
    nopkg_dir.mkdir(exist_ok=True)
    return nopkg_dir / "registry.txt"


def _register_module(name: str, source: str, dev_mode: bool):
    """Register a module installation in the registry."""
    registry_path = _get_registry_path()
    
    # Read existing entries
    entries = []
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            entries = [line.strip() for line in f if line.strip()]
    
    # Add new entry
    mode = "dev" if dev_mode else "copy"
    entry = f"{name}|{source}|{mode}"
    entries.append(entry)
    
    # Write back to registry
    with open(registry_path, 'w') as f:
        for entry in entries:
            f.write(entry + '\n')


def _unregister_module(name: str):
    """Remove a module from the registry."""
    registry_path = _get_registry_path()
    
    if not registry_path.exists():
        return
    
    # Read existing entries
    with open(registry_path, 'r') as f:
        entries = [line.strip() for line in f if line.strip()]
    
    # Filter out the module
    filtered_entries = [e for e in entries if not e.startswith(f"{name}|")]
    
    # Write back to registry
    with open(registry_path, 'w') as f:
        for entry in filtered_entries:
            f.write(entry + '\n')


def _get_registered_modules() -> List[str]:
    """Get list of registered module names."""
    registry_path = _get_registry_path()
    
    if not registry_path.exists():
        return []
    
    modules = []
    with open(registry_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and '|' in line:
                name = line.split('|')[0]
                modules.append(name)
    
    return modules


