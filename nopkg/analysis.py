"""Module analysis and usage example generation."""

import ast
from pathlib import Path
from typing import Dict, Any, List


def analyze_package(package_path: Path) -> Dict[str, Any]:
    """Analyze a Python package to extract importable items from all modules."""
    if not package_path.is_dir() or not (package_path / "__init__.py").exists():
        return {'modules': [], 'functions': [], 'classes': [], 'variables': []}
    
    package_analysis = {'modules': [], 'functions': [], 'classes': [], 'variables': []}
    
    # Analyze __init__.py to find what's exported
    init_file = package_path / "__init__.py"
    if init_file.exists():
        init_analysis = analyze_module(init_file)
        package_analysis['functions'].extend(init_analysis['functions'])
        package_analysis['classes'].extend(init_analysis['classes'])
        package_analysis['variables'].extend(init_analysis['variables'])
        
        # Also check for re-exported items from imports
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
            
            for node in tree.body:
                # Check for "from module import item as name" patterns
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        # Skip star imports and private items
                        if alias.name == '*' or alias.name.startswith('_'):
                            continue
                        
                        # Use the alias name if provided, otherwise use the original name
                        exported_name = alias.asname if alias.asname else alias.name
                        
                        # Don't add if it starts with underscore
                        if not exported_name.startswith('_'):
                            # Add as a variable/callable (we don't know if it's a function or class)
                            if exported_name not in [f['name'] for f in package_analysis['functions']] and \
                               exported_name not in [c['name'] for c in package_analysis['classes']] and \
                               exported_name not in package_analysis['variables']:
                                package_analysis['variables'].append(exported_name)
        except (SyntaxError, UnicodeDecodeError, OSError):
            pass
    
    # Find all Python modules in the package (excluding private ones)
    for py_file in package_path.glob('*.py'):
        if py_file.name != '__init__.py' and not py_file.stem.startswith('_'):
            module_name = py_file.stem
            package_analysis['modules'].append(module_name)
    
    return package_analysis


def analyze_module(file_path: Path) -> Dict[str, Any]:
    """Analyze a Python module to extract importable items."""
    if not file_path.exists() or file_path.suffix != '.py':
        return {'functions': [], 'classes': [], 'variables': []}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        tree = ast.parse(source_code)
        
        functions = []
        classes = []
        variables = []
        
        # Only look at top-level nodes, not nested ones
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                args = [arg.arg for arg in node.args.args if arg.arg != 'self']
                num_defaults = len(node.args.defaults)
                formatted_args = args[:-num_defaults] + [f"{arg}=..." for arg in args[-num_defaults:]] if num_defaults else args
                
                functions.append({
                    'name': node.name,
                    'args': formatted_args,
                    'docstring': ast.get_docstring(node) or ''
                })
            
            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                # Find methods in the class
                methods = []
                for class_node in node.body:
                    if isinstance(class_node, ast.FunctionDef) and not class_node.name.startswith('_'):
                        # Get method signature (excluding self)
                        method_args = [arg.arg for arg in class_node.args.args if arg.arg != 'self']
                        methods.append({
                            'name': class_node.name,
                            'args': method_args
                        })
                
                classes.append({
                    'name': node.name,
                    'methods': methods,
                    'docstring': ast.get_docstring(node) or ''
                })
            
            elif isinstance(node, ast.Assign):
                # Look for module-level variable assignments
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith('_'):
                        # Only include simple constants/variables, not complex expressions
                        if isinstance(node.value, (ast.Constant, ast.Str, ast.Num)):
                            variables.append(target.id)
        
        return {
            'functions': functions,
            'classes': classes,
            'variables': variables
        }
    
    except (SyntaxError, UnicodeDecodeError, OSError):
        return {'functions': [], 'classes': [], 'variables': []}


def _suggest_arg_value(arg: str) -> str:
    """Suggest a value for a parameter based on its name."""
    arg_lower = arg.lower()
    if 'name' in arg_lower:
        return '"World"'
    if any(word in arg_lower for word in ['text', 'string', 'word']):
        return '"hello world"'
    if any(word in arg_lower for word in ['radius', 'num', 'n']):
        return '5'
    if arg_lower in ('a', 'b'):
        return '10'
    return '42'


def generate_package_usage_examples(package_name: str, analysis: Dict[str, Any]) -> List[str]:
    """Generate comprehensive usage examples for a Python package."""
    examples = []
    
    # Filter out private items
    public_modules = [m for m in analysis['modules'] if not m.startswith('_')]
    public_functions = [f for f in analysis['functions'] if not f['name'].startswith('_')]
    public_classes = [c for c in analysis['classes'] if not c['name'].startswith('_')]
    public_variables = [v for v in analysis.get('variables', []) if not v.startswith('_')]
    
    # Basic import
    examples.append(f"import {package_name}")
    examples.append("")
    
    # Show what's available to import
    importable_items = []
    if public_functions:
        importable_items.extend([f['name'] for f in public_functions[:3]])
    if public_classes:
        importable_items.extend([c['name'] for c in public_classes[:2]])
    if public_variables:
        importable_items.extend(public_variables[:3])
    
    if importable_items:
        if len(importable_items) == 1:
            examples.append(f"from {package_name} import {importable_items[0]}")
        elif len(importable_items) <= 3:
            examples.append(f"from {package_name} import {', '.join(importable_items)}")
        else:
            examples.append(f"from {package_name} import ({', '.join(importable_items[:2])},")
            examples.append(f"                            {', '.join(importable_items[2:])})")
        examples.append("")
    
    # Show submodules if any
    if public_modules:
        examples.append("# Submodules:")
        for mod in public_modules[:5]:
            examples.append(f"from {package_name} import {mod}")
        examples.append("")
    
    # Show usage examples for functions
    if public_functions:
        examples.append("# Functions:")
        for func in public_functions[:5]:
            if func['args']:
                args_str = ', '.join(_suggest_arg_value(arg) for arg in func['args'][:3])
                examples.append(f"{package_name}.{func['name']}({args_str})")
            else:
                examples.append(f"{package_name}.{func['name']}()")
        examples.append("")
    
    # Show usage for exported variables/callables
    if public_variables:
        examples.append("# Exported items:")
        for var in public_variables[:5]:
            # Assume it's callable if it looks like a function name
            if var.islower() or '_' in var:
                examples.append(f"{package_name}.{var}(...)")
            else:
                examples.append(f"{package_name}.{var}")
        examples.append("")
    
    # Show usage for classes
    if public_classes:
        examples.append("# Classes:")
        for cls in public_classes[:3]:
            examples.append(f"obj = {package_name}.{cls['name']}()")
            public_methods = [m for m in cls.get('methods', []) if not m['name'].startswith('_')]
            if public_methods:
                method = public_methods[0]
                if method['args']:
                    args_str = ', '.join(['...' for _ in method['args'][:2]])
                    examples.append(f"obj.{method['name']}({args_str})")
                else:
                    examples.append(f"obj.{method['name']}()")
            examples.append("")
    
    # Remove trailing empty line
    while examples and examples[-1] == "":
        examples.pop()
    
    return examples


def generate_usage_examples(module_name: str, analysis: Dict[str, Any]) -> List[str]:
    """Generate comprehensive usage examples based on module analysis."""
    examples = []
    
    # Check if this is package analysis (has 'modules' key)
    if 'modules' in analysis:
        return generate_package_usage_examples(module_name, analysis)
    
    # Filter out private items
    public_functions = [f for f in analysis['functions'] if not f['name'].startswith('_')]
    public_classes = [c for c in analysis['classes'] if not c['name'].startswith('_')]
    
    # Basic import
    examples.append(f"import {module_name}")
    examples.append("")
    
    # Show function imports
    if public_functions:
        func_names = [f['name'] for f in public_functions[:5]]
        if len(func_names) == 1:
            examples.append(f"from {module_name} import {func_names[0]}")
        elif len(func_names) <= 3:
            examples.append(f"from {module_name} import {', '.join(func_names)}")
        else:
            examples.append(f"from {module_name} import ({', '.join(func_names[:3])},")
            examples.append(f"                            {', '.join(func_names[3:])})")
        examples.append("")
    
    # Show class imports
    if public_classes:
        class_names = [c['name'] for c in public_classes[:3]]
        if len(class_names) == 1:
            examples.append(f"from {module_name} import {class_names[0]}")
        else:
            examples.append(f"from {module_name} import {', '.join(class_names)}")
        examples.append("")
    
    # Show function usage examples
    if public_functions:
        examples.append("# Functions:")
        for func in public_functions[:5]:
            if func['args']:
                args_str = ', '.join(_suggest_arg_value(arg.replace('=...', '')) for arg in func['args'][:3])
                examples.append(f"{func['name']}({args_str})")
            else:
                examples.append(f"{func['name']}()")
        examples.append("")
    
    # Show class usage examples
    if public_classes:
        examples.append("# Classes:")
        for cls in public_classes[:3]:
            examples.append(f"obj = {cls['name']}()")
            # Show first few public methods
            public_methods = [m for m in cls.get('methods', []) if not m['name'].startswith('_')]
            for method in public_methods[:2]:
                if method['args']:
                    args_str = ', '.join(['...' for _ in method['args'][:2]])
                    examples.append(f"obj.{method['name']}({args_str})")
                else:
                    examples.append(f"obj.{method['name']}()")
            if public_classes.index(cls) < len(public_classes) - 1:
                examples.append("")
    
    return examples
