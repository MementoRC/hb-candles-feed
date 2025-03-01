cmake_minimum_required(VERSION 3.21)
project(candles_feed)

# Set Python as the required language
find_package(Python REQUIRED COMPONENTS Interpreter Development)

# Add the cmake directory to the module path so FindCython.cmake can be found
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# Find Cython
find_package(Cython REQUIRED)

# Include directory configuration
include_directories(${Python_INCLUDE_DIRS})

# Add our custom Cython build module
add_custom_target(build_cython ALL
    COMMAND ${Python_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/cmake/cython_builder.py ${CMAKE_CURRENT_SOURCE_DIR}/candles_feed
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running Cython builder for performance-critical modules"
)

# Install Python package
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/candles_feed DESTINATION .)