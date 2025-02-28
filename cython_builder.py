#!/usr/bin/env python
"""
Helper script to build Cython modules from Python files with Cython decorators.
"""

import os
import sys
import glob
from pathlib import Path
import subprocess
import importlib.util

def find_cython_files(directory):
    """Find Python files with Cython decorators that need compilation."""
    cython_files = []
    
    for path in Path(directory).rglob('*.py'):
        # Check if the file contains Cython decorators
        with open(path, 'r') as f:
            content = f.read()
            if '@cython.ccall' in content or '@cython.cfunc' in content or '@cython.cclass' in content:
                cython_files.append(path)
    
    return cython_files

def build_cython_modules(directory):
    """Compile Python files with Cython decorators."""
    # Check if Cython is available
    if importlib.util.find_spec("Cython") is None:
        print("Cython not found. Skipping Cython compilation.")
        return 0
        
    try:
        from Cython.Build import cythonize
    except ImportError:
        print("Cython not found. Skipping Cython compilation.")
        return 0
    
    cython_files = find_cython_files(directory)
    
    if not cython_files:
        print("No files with Cython decorators found.")
        return 0
    
    # Build the Cython modules
    from setuptools import Extension
    from Cython.Build import cythonize
    from Cython.Distutils import build_ext
    import distutils.core
    
    # Determine package path for module naming
    package_dir = os.path.basename(directory)
    
    # Build extensions for each file
    extensions = []
    for path in cython_files:
        # Get module name from file path
        rel_path = path.relative_to(directory)
        module_path = str(rel_path).replace('/', '.').replace('\\', '.').replace('.py', '')
        module_name = f"{package_dir}.{module_path}"
        
        print(f"Will compile {path} as module {module_name}")
        
        # Create extension
        extension = Extension(
            module_name,
            sources=[str(path)],
            # Add any compile-time flags
            extra_compile_args=['-O3'] if os.name != 'nt' else ['/O2'],
        )
        
        extensions.append(extension)
    
    # Cythonize and build
    if extensions:
        print(f"Building {len(extensions)} Cython modules:")
        for ext in extensions:
            print(f" - {ext.name}")
        
        cythonized_extensions = cythonize(
            extensions,
            compiler_directives={
                'language_level': 3,
                'boundscheck': False,
                'wraparound': False,
                'nonecheck': False,
                'cdivision': True,
            },
            force=True,  # Force recompilation
        )
        
        # Build extensions in-place
        cmd_obj = build_ext(distutils.core.Distribution())
        cmd_obj.inplace = True
        cmd_obj.extensions = cythonized_extensions
        cmd_obj.ensure_finalized()
        cmd_obj.run()
        
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cython_builder.py <package_directory>")
        sys.exit(1)
    
    package_dir = sys.argv[1]
    sys.exit(build_cython_modules(package_dir))