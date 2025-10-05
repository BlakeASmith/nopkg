"""Module analysis and usage example generation."""

import ast
from pathlib import Path
from typing import Dict, Any, List


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
        
        for node in ast.walk(tree):
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


def generate_usage_examples(module_name: str, analysis: Dict[str, Any]) -> List[str]:
    """Generate usage examples based on module analysis."""
    examples = []
    
    # Add basic import statement
    examples.append(f"import {module_name}")
    
    # Generate function import examples
    if analysis['functions']:
        func_names = [f['name'] for f in analysis['functions'][:3]]  # Limit to first 3
        if len(func_names) == 1:
            examples.append(f"from {module_name} import {func_names[0]}")
        elif len(func_names) > 1:
            examples.append(f"from {module_name} import {', '.join(func_names)}")
    
    # Generate class import examples
    if analysis['classes']:
        class_names = [c['name'] for c in analysis['classes'][:2]]  # Limit to first 2
        if len(class_names) == 1:
            examples.append(f"from {module_name} import {class_names[0]}")
        elif len(class_names) > 1:
            examples.append(f"from {module_name} import {', '.join(class_names)}")
    
    # Generate usage examples
    usage_examples = []
    
    # Function usage examples
    for func in analysis['functions'][:2]:  # Limit to first 2 functions
        if func['args']:
            args_str = ', '.join(_suggest_arg_value(arg) for arg in func['args'][:2])
            usage_examples.append(f"{module_name}.{func['name']}({args_str})")
        else:
            usage_examples.append(f"{module_name}.{func['name']}()")
    
    # Class usage examples
    for cls in analysis['classes'][:1]:  # Limit to first class
        usage_examples.append(f"obj = {module_name}.{cls['name']}()")
        if cls['methods']:
            method = cls['methods'][0]
            if method['args']:
                args_str = ', '.join(['42' for _ in method['args'][:2]])
                usage_examples.append(f"obj.{method['name']}({args_str})")
            else:
                usage_examples.append(f"obj.{method['name']}()")
    
    if usage_examples:
        examples.append("\n# Usage examples:")
        examples.extend(usage_examples)
    
    return examples
