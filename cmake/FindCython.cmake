# Find the Cython compiler.
#
# This module defines
#  CYTHON_EXECUTABLE, the path to the cython executable
#  CYTHON_FOUND, whether cython has been found

find_program(CYTHON_EXECUTABLE NAMES cython cython.bat cython3)

# handle REQUIRED and QUIET options
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(Cython REQUIRED_VARS CYTHON_EXECUTABLE)

mark_as_advanced(CYTHON_EXECUTABLE)