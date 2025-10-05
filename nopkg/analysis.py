"""Module analysis and usage example generation."""

import ast
from pathlib import Path
from typing import Dict, Any, List


def analyze_package(package_path: Path) -> Dict[str, Any]:
    """Analyze a Python package to extract importable items from all modules."""
    if not package_path.is_dir() or not (package_path / "__init__.py").exists():
        return {'modules': [], 'functions': [], 'classes': [], 'variables': [], 'submodule_details': {}}
    
    package_analysis = {'modules': [], 'functions': [], 'classes': [], 'variables': [], 'submodule_details': {}}
    
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
    
    # Find all Python modules in the package and analyze them deeply
    for py_file in package_path.glob('*.py'):
        if py_file.name != '__init__.py' and not py_file.stem.startswith('_'):
            module_name = py_file.stem
            package_analysis['modules'].append(module_name)
            
            # Deeply analyze each submodule to get its contents
            submodule_analysis = analyze_module(py_file)
            package_analysis['submodule_details'][module_name] = {
                'functions': [f for f in submodule_analysis['functions'] if not f['name'].startswith('_')],
                'classes': [c for c in submodule_analysis['classes'] if not c['name'].startswith('_')]
            }
    
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
    # Remove default value indicators
    arg = arg.replace('=...', '')
    arg_lower = arg.lower()
    
    # Address/email parameters
    if any(word in arg_lower for word in ['email', 'mail', 'to_address', 'from_address']):
        return '"user@example.com"'
    if 'address' in arg_lower:
        return '"123 Main St"'
    
    # String-like parameters
    if any(word in arg_lower for word in ['name', 'username', 'user']):
        return '"alice"'
    if any(word in arg_lower for word in ['title', 'heading', 'label']):
        return '"My Title"'
    if any(word in arg_lower for word in ['subject']):
        return '"Important Message"'
    if any(word in arg_lower for word in ['body', 'text', 'string', 'msg', 'content']):
        return '"hello world"'
    if 'message' in arg_lower and not 'messages' in arg_lower:  # single message
        return '"hello world"'
    if any(word in arg_lower for word in ['path', 'filepath', 'filename', 'file']):
        return '"data.txt"'
    if any(word in arg_lower for word in ['url', 'uri', 'link', 'endpoint']):
        return '"https://api.example.com"'
    if any(word in arg_lower for word in ['api_key', 'token']) and 'max' not in arg_lower:
        return '"sk-abc123"'
    if 'key' in arg_lower and 'max' not in arg_lower and 'api' not in arg_lower:
        return '"key123"'
    if 'id' in arg_lower:
        return '"id_123"'
    if any(word in arg_lower for word in ['method', 'mode', 'type', 'format', 'style']):
        return '"default"'
    if any(word in arg_lower for word in ['model']):
        return '"gpt-4"'
    if any(word in arg_lower for word in ['password', 'secret']):
        return '"secure_pass123"'
    if any(word in arg_lower for word in ['base_url']):
        return '"https://api.example.com"'
    
    # Collection parameters - check before numeric ones
    if any(word in arg_lower for word in ['messages']):
        return '[{"role": "user", "content": "hello"}]'
    if any(word in arg_lower for word in ['headers', 'header']):
        return '{"Content-Type": "application/json"}'
    if any(word in arg_lower for word in ['attachments', 'files']):
        return '["file1.txt", "file2.pdf"]'
    if any(word in arg_lower for word in ['cc', 'bcc']):
        return '["user@example.com"]'
    if any(word in arg_lower for word in ['params', 'parameters']):
        return '{"key": "value"}'
    if any(word in arg_lower for word in ['tags', 'labels']):
        return '["tag1", "tag2"]'
    
    # Numeric parameters (most specific first, with meaningful values)
    if 'max_tokens' in arg_lower or 'max_token' in arg_lower:
        return '1000'
    if 'top_p' in arg_lower:
        return '0.9'
    if any(word in arg_lower for word in ['temperature', 'temp']):
        return '0.7'
    if any(word in arg_lower for word in ['threshold']):
        return '0.5'
    if any(word in arg_lower for word in ['timeout', 'delay']):
        return '30'
    if any(word in arg_lower for word in ['window', 'window_size']):
        return '5'
    if any(word in arg_lower for word in ['port']):
        return '8080'
    if any(word in arg_lower for word in ['batch_size', 'batch']):
        return '32'
    if any(word in arg_lower for word in ['epoch']):
        return '10'
    if any(word in arg_lower for word in ['learning_rate', 'lr']):
        return '0.001'
    if any(word in arg_lower for word in ['count', 'num', 'number', 'n']):
        return '10'
    if any(word in arg_lower for word in ['page', 'offset']):
        return '1'
    if any(word in arg_lower for word in ['size', 'length']):
        return '100'
    if any(word in arg_lower for word in ['width']):
        return '800'
    if any(word in arg_lower for word in ['height']):
        return '600'
    if any(word in arg_lower for word in ['price', 'cost']):
        return '9.99'
    if any(word in arg_lower for word in ['age']):
        return '25'
    if any(word in arg_lower for word in ['year']):
        return '2024'
    if any(word in arg_lower for word in ['rating', 'score']):
        return '4.5'
    if any(word in arg_lower for word in ['percent', 'percentage']):
        return '75'
    if any(word in arg_lower for word in ['distance']):
        return '100.0'
    if any(word in arg_lower for word in ['index', 'idx', 'position', 'pos']):
        return '0'
    if any(word in arg_lower for word in ['max', 'limit']):
        return '100'
    if any(word in arg_lower for word in ['min', 'minimum']):
        return '0'
    if any(word in arg_lower for word in ['quantity', 'qty', 'amount']):
        return '5'
    if any(word in arg_lower for word in ['value', 'val']):
        return '100'
    
    # Boolean-like parameters
    if any(word in arg_lower for word in ['enable', 'enabled', 'flag', 'verbose', 'debug', 'stream']):
        return 'True'
    if any(word in arg_lower for word in ['normalize', 'strict', 'async']):
        return 'True'
    
    # Additional collection parameters
    if any(word in arg_lower for word in ['list', 'items', 'values']):
        return '[1, 2, 3]'
    if any(word in arg_lower for word in ['data']):
        return '{"field": "value"}'
    if any(word in arg_lower for word in ['dict', 'mapping', 'config', 'options', 'settings']):
        return '{"option": "value"}'
    if any(word in arg_lower for word in ['array', 'numbers']):
        return '[1, 2, 3]'
    
    # Generic defaults based on common single letters
    if arg_lower in ('a', 'b', 'x', 'y'):
        return '10'
    if arg_lower in ('i', 'j', 'k'):
        return '0'
    if arg_lower in ('s', 'str'):
        return '"text"'
    if arg_lower in ('n'):
        return '5'
    
    # Ultimate fallback - try to guess from type patterns
    # If it ends with common suffixes
    if arg_lower.endswith(('_str', '_text', '_name')):
        return '"text"'
    if arg_lower.endswith(('_int', '_num', '_count')):
        return '10'
    if arg_lower.endswith(('_bool', '_flag')):
        return 'True'
    if arg_lower.endswith(('_list', '_array', '_items')):
        return '[]'
    if arg_lower.endswith(('_dict', '_map', '_obj')):
        return '{}'
    if arg_lower.endswith(('_id')):
        return '"id_123"'
    if arg_lower.endswith(('_path')):
        return '"path/to/file"'
    if arg_lower.endswith(('_url')):
        return '"https://example.com"'
    
    # Final intelligent fallback
    # If it looks like it should be a string (has underscores or is CamelCase)
    if '_' in arg_lower or (arg and arg[0].isupper()):
        return '"value"'
    
    # Numeric fallback - use 1 instead of 42 for cleaner examples
    return '1'


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
    
    # Show submodules with their contents
    if public_modules:
        submodule_details = analysis.get('submodule_details', {})
        
        for mod in public_modules[:5]:  # Show up to 5 submodules
            examples.append(f"# {package_name}.{mod}:")
            examples.append(f"from {package_name} import {mod}")
            
            # Show what's in the submodule
            if mod in submodule_details:
                details = submodule_details[mod]
                
                # Show functions from submodule
                if details.get('functions'):
                    func_names = [f['name'] for f in details['functions'][:3]]
                    if func_names:
                        examples.append(f"from {package_name}.{mod} import {', '.join(func_names)}")
                        # Show usage example for first function
                        first_func = details['functions'][0]
                        if first_func['args']:
                            args_str = ', '.join(_suggest_arg_value(arg) for arg in first_func['args'][:2])
                            examples.append(f"{mod}.{first_func['name']}({args_str})")
                        else:
                            examples.append(f"{mod}.{first_func['name']}()")
                
                # Show classes from submodule
                if details.get('classes'):
                    class_names = [c['name'] for c in details['classes'][:2]]
                    if class_names:
                        examples.append(f"from {package_name}.{mod} import {', '.join(class_names)}")
                        # Show usage example for first class
                        first_class = details['classes'][0]
                        examples.append(f"obj = {first_class['name']}()")
            
            examples.append("")
    
    # Show detailed usage examples for functions
    if public_functions:
        for func in public_functions[:3]:  # Show top 3 functions in detail
            # Add docstring as comment if available
            if func.get('docstring'):
                docstring = func['docstring'].split('\n')[0].strip()  # First line only
                if docstring:
                    examples.append(f"# {func['name']}: {docstring}")
            
            # Show function signature
            if func['args']:
                args_display = ', '.join(func['args'])
                examples.append(f"{package_name}.{func['name']}({args_display})")
                
                # Show example call with smart parameter values
                arg_values = []
                for arg in func['args'][:5]:
                    suggested = _suggest_arg_value(arg)
                    # For optional params (with =...), show the param name
                    if '=...' in arg:
                        param_name = arg.replace('=...', '')
                        arg_values.append(f"{param_name}={suggested}")
                    else:
                        arg_values.append(suggested)
                examples.append(f"{package_name}.{func['name']}({', '.join(arg_values)})")
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
                    args_str = ', '.join([_suggest_arg_value(arg) for arg in method['args'][:2]])
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
    
    # Show detailed function usage examples
    if public_functions:
        for func in public_functions[:5]:  # Show up to 5 functions
            # Add docstring as comment if available
            if func.get('docstring'):
                docstring = func['docstring'].split('\n')[0].strip()  # First line only
                if docstring:
                    examples.append(f"# {func['name']}: {docstring}")
            
            # Show function signature
            if func['args']:
                args_display = ', '.join(func['args'])
                examples.append(f"{func['name']}({args_display})")
                
                # Show example call with smart parameter values
                arg_values = []
                for arg in func['args'][:5]:
                    suggested = _suggest_arg_value(arg)
                    # For optional params (with =...), show the param name
                    if '=...' in arg:
                        param_name = arg.replace('=...', '')
                        arg_values.append(f"{param_name}={suggested}")
                    else:
                        arg_values.append(suggested)
                examples.append(f"{func['name']}({', '.join(arg_values)})")
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
                    args_str = ', '.join([_suggest_arg_value(arg) for arg in method['args'][:3]])
                    examples.append(f"obj.{method['name']}({args_str})")
                else:
                    examples.append(f"obj.{method['name']}()")
            if public_classes.index(cls) < len(public_classes) - 1:
                examples.append("")
    
    return examples
