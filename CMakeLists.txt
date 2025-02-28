cmake_minimum_required(VERSION 3.21.0)
project(candles_feed LANGUAGES C CXX)

# Add the current directory to the module path so FindCython.cmake can be found
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}")

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

# Simplified approach - just use the cython_builder script instead of trying to 
# check each file individually with cython.inline
function(register_cython_modules package_dir)
    # Create a custom target that will process the entire package
    add_custom_target(build_cython_package ALL
        COMMAND ${Python_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/cython_builder.py ${package_dir}
        COMMENT "Building Cython modules with decorators in ${package_dir}"
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/cython_builder.py
    )
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

# We've already set up the Cython build in the register_cython_modules function,
# so we don't need this duplicate target.