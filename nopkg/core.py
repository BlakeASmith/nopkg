"""Core functionality for nopkg module installation."""

import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from .analysis import analyze_module, analyze_package


def is_python_package(directory: Path) -> bool:
    """Check if a directory is a Python package (has __init__.py)."""
    return (directory / "__init__.py").exists()


def has_python_files(directory: Path) -> bool:
    """Check if a directory contains any Python files."""
    return any(directory.glob("*.py"))


def create_empty_init(directory: Path) -> bool:
    """Create an empty __init__.py file in the directory.
    
    Returns:
        bool: True if created successfully, False otherwise
    """
    try:
        init_file = directory / "__init__.py"
        init_file.write_text("# added by nopkg\n")
        return True
    except Exception:
        return False


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


def install_module(source: str, dev_mode: bool = False, python_executable: str = sys.executable) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Install a Python module from a source (file path or directory).
    
    Args:
        source: Source path (local file or directory)
        dev_mode: If True, use .pth file instead of copying
        python_executable: Path to the Python executable to install for
        
    Returns:
        Tuple of (success, message, analysis_data)
    """
    site_packages = get_site_packages_dir(python_executable)
    if site_packages is None:
        return False, "Could not determine site-packages directory", None
    
    source_path = Path(source)
    
    if not source_path.exists():
        return False, f"Source file not found: {source}", None
    
    if source_path.is_file() and source_path.suffix != '.py':
        return False, f"Only Python files (.py) and packages are supported", None
    
    if source_path.is_dir():
        if not has_python_files(source_path):
            return False, f"Directory '{source}' contains no Python files", None
        
        if not is_python_package(source_path) and not create_empty_init(source_path):
            return False, f"Could not create __init__.py in directory '{source}'", None
        
        success, message = _install_package(source_path, site_packages, dev_mode)
        analysis_data = analyze_package(source_path) if success else None
        return success, message, analysis_data
    
    module_name = source_path.stem
    target_path = site_packages / f"{module_name}.py"
    
    if target_path.exists():
        existing_modules = _get_registered_modules()
        if module_name in existing_modules:
            return False, f"Module '{module_name}' is already installed by nopkg. Use 'nopkg uninstall {module_name}' first.", None
        return False, f"Module '{module_name}' already exists (not managed by nopkg)", None
    
    try:
        if dev_mode:
            pth_path = site_packages / f"nopkg_{module_name}.pth"
            pth_path.write_text(str(source_path.parent.absolute()) + "\n")
        else:
            shutil.copy2(source_path, target_path)
        
        _register_module(module_name, source, dev_mode)
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


def _install_package(source_dir: Path, site_packages: Path, dev_mode: bool) -> Tuple[bool, str]:
    """Install a Python package (directory with __init__.py)."""
    package_name = source_dir.name
    target_path = site_packages / package_name
    
    if target_path.exists():
        existing_modules = _get_registered_modules()
        if package_name in existing_modules:
            return False, f"Package '{package_name}' is already installed by nopkg. Use 'nopkg uninstall {package_name}' first."
        return False, f"Package '{package_name}' already exists (not managed by nopkg)"
    
    try:
        if dev_mode:
            pth_path = site_packages / f"nopkg_{package_name}.pth"
            pth_path.write_text(str(source_dir.parent.absolute()) + "\n")
        else:
            shutil.copytree(source_dir, target_path)
        
        _register_module(package_name, str(source_dir), dev_mode)
        return True, f"Successfully installed package '{package_name}'"
        
    except PermissionError:
        return False, f"Permission denied: cannot write to {site_packages}"
    except Exception as e:
        return False, f"Failed to install package: {e}"




def uninstall_module(module_name: str, python_executable: str = sys.executable) -> Tuple[bool, str]:
    """Uninstall a module or package installed by nopkg."""
    site_packages = get_site_packages_dir(python_executable)
    if site_packages is None:
        return False, "Could not determine site-packages directory"
    
    module_path = site_packages / f"{module_name}.py"  # Single module file
    package_path = site_packages / module_name  # Package directory
    pth_path = site_packages / f"nopkg_{module_name}.pth"  # Dev mode
    
    # Check if any form exists
    if not module_path.exists() and not package_path.exists() and not pth_path.exists():
        return False, f"Module/package '{module_name}' is not installed"
    
    try:
        # Remove the module file if it exists
        if module_path.exists():
            module_path.unlink()
        
        # Remove the package directory if it exists
        if package_path.exists():
            shutil.rmtree(package_path)
        
        # Remove the .pth file if it exists (dev mode installation)
        if pth_path.exists():
            pth_path.unlink()
        
        _unregister_module(module_name)
        return True, f"Successfully uninstalled '{module_name}'"
            
    except PermissionError:
        return False, f"Permission denied: cannot remove files for {module_name}"
    except Exception as e:
        return False, f"Failed to uninstall: {e}"


def list_installed_modules() -> List[str]:
    """List all modules installed by nopkg."""
    return _get_registered_modules()


def update_module(module_name: str) -> Tuple[bool, str]:
    """Update an installed module by reinstalling from its original source."""
    registry_path = _get_registry_path()
    if not registry_path.exists():
        return False, f"Module '{module_name}' not found"
    
    # Find module in registry
    with open(registry_path, 'r') as f:
        for line in f:
            if line.strip().startswith(f"{module_name}|"):
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    source, mode = parts[1], parts[2]
                    # Uninstall and reinstall
                    success, msg = uninstall_module(module_name)
                    if not success:
                        return False, f"Failed to uninstall: {msg}"
                    return install_module(source, mode == 'dev')[:2]
    
    return False, f"Module '{module_name}' not found in registry"


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
    entries.append(f"{name}|{source}|{'dev' if dev_mode else 'copy'}")
    
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


