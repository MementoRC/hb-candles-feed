cmake_minimum_required(VERSION 3.21.0)
project(candles_feed LANGUAGES C CXX)

# Find required packages
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(Cython REQUIRED)

# Include directories for Python
include_directories(${Python_INCLUDE_DIRS})

# Platform-specific compiler flags
if(MSVC)
    # Windows/MSVC specific flags
    add_compile_options(/W3 /O2)
else()
    # Linux/macOS specific flags
    add_compile_options(-Wall -O3 -fPIC)
endif()

# Function to compile Python modules with Cython decorators
function(register_cython_modules package_dir)
    file(GLOB_RECURSE PY_FILES "${package_dir}/*.py")
    
    # Process each Python file for Cython compilation
    foreach(PY_FILE ${PY_FILES})
        # Extract relative path from package directory
        file(RELATIVE_PATH REL_PY_FILE ${package_dir} ${PY_FILE})
        
        # Construct the module name from the Python file path
        string(REPLACE "/" "." MODULE_PATH ${REL_PY_FILE})
        string(REPLACE ".py" "" MODULE_NAME ${MODULE_PATH})
        
        # Run Cython to check if file has decorators that need compilation
        add_custom_target(cythonize_check_${MODULE_NAME} ALL
            COMMAND ${Python_EXECUTABLE} -m cython.inline "import sys; from Cython.Build.Dependencies import cythonize_one; sys.exit(0 if cythonize_one('${PY_FILE}', True) else 1)"
            BYPRODUCTS "${PY_FILE}.c"
            DEPENDS ${PY_FILE}
            COMMENT "Checking if ${PY_FILE} needs Cython compilation"
            # Only attempt to compile if Cython finds decorators
            ERROR_QUIET
        )
    endforeach()
endfunction()

# Register Python modules for Cython compilation
register_cython_modules(${CMAKE_CURRENT_SOURCE_DIR}/candles_feed)

# Install all Python source files
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/candles_feed
        DESTINATION .
        FILES_MATCHING
        PATTERN "*.py"
        PATTERN "*.pyd"
        PATTERN "__pycache__" EXCLUDE
)

# Create a custom target that builds any Cython-decorated files
add_custom_target(build_cython_modules ALL
    COMMAND ${Python_EXECUTABLE} -m cython_builder ${CMAKE_CURRENT_SOURCE_DIR}/candles_feed
    COMMENT "Building Cython modules with decorators"
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/cython_builder.py
)