#!/usr/bin/env python
"""
Cython Builder Script for Hummingbot Sub-Packages

This script automatically detects Python modules that have functions decorated with @cython
and compiles them using Cython for performance optimization.

Usage:
    python cython_builder.py [package_dir]

Example:
    python cython_builder.py ./candles_feed

Requirements:
    - Cython>=0.29.33
"""

import ast
import importlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


class CythonDecoratorVisitor(ast.NodeVisitor):
    """AST Visitor to find functions decorated with @cython."""
    
    def __init__(self):
        self.cython_decorated_functions = []
        
    def visit_FunctionDef(self, node):
        """Visit a function definition node."""
        # Check if the function has decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "cython":
                self.cython_decorated_functions.append(node.name)
        self.generic_visit(node)


def find_cython_decorated_files(package_dir: str) -> List[Tuple[str, List[str]]]:
    """
    Find all Python files with @cython decorated functions in the package.
    
    Args:
        package_dir: Path to the package directory
        
    Returns:
        List of (file_path, decorated_function_names) tuples
    """
    cython_files = []
    package_path = Path(package_dir)
    
    for py_file in package_path.glob("**/*.py"):
        # Skip __init__.py files and already compiled modules
        if py_file.name == "__init__.py" or py_file.with_suffix(".c").exists():
            continue
            
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                file_content = f.read()
                
            # Quick check if "cython" is present in the file
            if "@cython" not in file_content:
                continue
                
            # Parse the file with AST
            tree = ast.parse(file_content)
            visitor = CythonDecoratorVisitor()
            visitor.visit(tree)
            
            if visitor.cython_decorated_functions:
                cython_files.append((str(py_file), visitor.cython_decorated_functions))
                
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
    
    return cython_files


def create_cython_wrapper(py_file: str, functions: List[str]) -> str:
    """
    Create a .pyx wrapper file for the given Python file.
    
    Args:
        py_file: Path to the Python file
        functions: List of function names to be compiled
        
    Returns:
        Path to the created .pyx file
    """
    py_path = Path(py_file)
    # Create a .pyx file with the same name
    pyx_file = py_path.with_suffix(".pyx")
    
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace @cython decorators
    for func_name in functions:
        pattern = rf"@cython\s+def\s+{func_name}\s*\("
        content = re.sub(pattern, f"def {func_name}(", content)
    
    # Write the content to the .pyx file
    with open(pyx_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(pyx_file)


def compile_cython_file(pyx_file: str) -> None:
    """
    Compile a .pyx file using Cython and the appropriate compiler.
    
    Args:
        pyx_file: Path to the .pyx file to compile
    """
    try:
        # First, generate the C file
        subprocess.check_call([sys.executable, "-m", "cython", pyx_file, "-3", "--fast-fail"])
        
        # Get the base module name without extension
        module_name = Path(pyx_file).stem
        
        # Use setuptools to build the extension
        setup_py_content = f"""
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extension = Extension(
    "{module_name}",
    ["{pyx_file}"],
    include_dirs=[np.get_include()],
    extra_compile_args=["-O3"],
)

setup(
    ext_modules=cythonize([extension], compiler_directives={{'language_level': '3'}}),
)
"""
        # Write temporary setup.py
        with open("temp_setup.py", "w") as f:
            f.write(setup_py_content)
        
        # Build the extension
        subprocess.check_call([sys.executable, "temp_setup.py", "build_ext", "--inplace"])
        
        # Clean up
        os.remove("temp_setup.py")
        
        print(f"Successfully compiled {pyx_file}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {pyx_file}: {e}")
    except Exception as e:
        print(f"Unexpected error compiling {pyx_file}: {e}")


def main():
    """Main entry point for the Cython builder script."""
    if len(sys.argv) < 2:
        print("Usage: python cython_builder.py [package_dir]")
        sys.exit(1)
    
    package_dir = sys.argv[1]
    print(f"Scanning {package_dir} for @cython decorated functions...")
    
    cython_files = find_cython_decorated_files(package_dir)
    
    if not cython_files:
        print("No files with @cython decorated functions found.")
        return
    
    print(f"Found {len(cython_files)} files with @cython decorators:")
    for py_file, functions in cython_files:
        print(f"  {py_file}: {', '.join(functions)}")
        pyx_file = create_cython_wrapper(py_file, functions)
        compile_cython_file(pyx_file)


if __name__ == "__main__":
    main()