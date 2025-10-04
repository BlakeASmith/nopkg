"""Basic integration tests for nopkg."""

import sys
import tempfile
from pathlib import Path

import pytest


def test_imports():
    """Test that all modules can be imported."""
    from nopkg import cli, core, analysis
    
    assert cli is not None
    assert core is not None
    assert analysis is not None


def test_get_site_packages_dir():
    """Test that we can get the site-packages directory."""
    from nopkg.core import get_site_packages_dir
    
    site_packages = get_site_packages_dir()
    assert site_packages is not None
    assert site_packages.exists()
    assert site_packages.is_dir()


def test_cli_version():
    """Test that CLI version command works."""
    from nopkg.cli import get_version
    
    version = get_version()
    assert version is not None
    assert isinstance(version, str)
    assert version != "unknown"


def test_analyze_module():
    """Test that module analysis works."""
    from nopkg.analysis import analyze_module
    
    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def test_function(arg1, arg2):
    """Test function."""
    pass

class TestClass:
    """Test class."""
    def method(self):
        pass
''')
        temp_file = Path(f.name)
    
    try:
        analysis = analyze_module(temp_file)
        
        assert 'functions' in analysis
        assert 'classes' in analysis
        assert 'variables' in analysis
        
        # Note: ast.walk traverses all nodes, so methods are also counted as functions
        assert len(analysis['functions']) >= 1
        function_names = [f['name'] for f in analysis['functions']]
        assert 'test_function' in function_names
        
        assert len(analysis['classes']) == 1
        assert analysis['classes'][0]['name'] == 'TestClass'
    finally:
        temp_file.unlink()


def test_generate_usage_examples():
    """Test that usage example generation works."""
    from nopkg.analysis import generate_usage_examples
    
    analysis = {
        'functions': [{'name': 'test_func', 'args': ['x', 'y']}],
        'classes': [{'name': 'TestClass', 'methods': []}],
        'variables': []
    }
    
    examples = generate_usage_examples('mymodule', analysis)
    
    assert len(examples) > 0
    assert 'import mymodule' in examples
