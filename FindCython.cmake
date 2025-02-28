# FindCython.cmake
#
# Finds the Cython compiler
#
# This module defines:
#  CYTHON_EXECUTABLE
#  CYTHON_FOUND
#
# Adapted from FindCython.cmake in scikit-build project

# Use python's Cython module to find Cython
find_package(Python REQUIRED COMPONENTS Interpreter)

execute_process(
    COMMAND "${Python_EXECUTABLE}" -c "import Cython; print(Cython.__path__[0])"
    OUTPUT_VARIABLE CYTHON_PATH
    ERROR_QUIET
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

if (CYTHON_PATH)
    # Create a Cython execution wrapper
    set(CYTHON_EXECUTABLE "${Python_EXECUTABLE}" "-m" "cython")
    set(CYTHON_FOUND TRUE)
else()
    # Try to find cython executable directly
    find_program(CYTHON_EXECUTABLE
        NAMES cython cython.bat cython3
    )
    if (CYTHON_EXECUTABLE)
        set(CYTHON_FOUND TRUE)
    endif()
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(Cython
    REQUIRED_VARS CYTHON_EXECUTABLE
)

mark_as_advanced(CYTHON_EXECUTABLE)