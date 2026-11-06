cmake_minimum_required(VERSION 3.20)
project(veritas_r91_d3_score LANGUAGES CXX)

option(VERITAS_D3_BUILD_PYBIND "Build the optional pybind11 module" ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Boost REQUIRED)

add_library(veritas_d3_score SHARED src/score.cpp)
target_compile_features(veritas_d3_score PRIVATE cxx_std_20)
target_compile_definitions(veritas_d3_score PRIVATE VERITAS_D3_SCORE_BUILD)
target_include_directories(veritas_d3_score PUBLIC ${Boost_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/include)
set_target_properties(veritas_d3_score PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN YES
    OUTPUT_NAME veritas_d3_score)

if(MSVC)
  target_compile_options(veritas_d3_score PRIVATE /W4 /WX /permissive-)
else()
  target_compile_options(veritas_d3_score PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# The pybind11 module is optional: the C ABI above is always built and the
# Python integration falls back to ctypes, then to the pure-Python scorer.
if(VERITAS_D3_BUILD_PYBIND)
  set(PYBIND11_FINDPYTHON ON)
  find_package(pybind11 CONFIG QUIET)
  if(pybind11_FOUND)
    pybind11_add_module(veritas_d3 MODULE src/bindings.cpp)
    target_link_libraries(veritas_d3 PRIVATE veritas_d3_score)
    target_include_directories(veritas_d3 PRIVATE ${Boost_INCLUDE_DIRS}
        ${CMAKE_CURRENT_SOURCE_DIR}/include)
    set_target_properties(veritas_d3 PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/python
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/python)
    if(MSVC)
      target_compile_options(veritas_d3 PRIVATE /W4 /permissive-)
    else()
      target_compile_options(veritas_d3 PRIVATE -Wall -Wextra -Wpedantic)
    endif()
    message(STATUS "pybind11 ${pybind11_VERSION} found: building veritas_d3")
  else()
    message(STATUS "pybind11 not found: building only the C ABI library")
  endif()
endif()

enable_testing()
add_executable(veritas_d3_selftest tests/selftest.cpp)
target_link_libraries(veritas_d3_selftest PRIVATE veritas_d3_score)
target_include_directories(veritas_d3_selftest PRIVATE ${Boost_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/include)
add_test(NAME veritas_d3_selftest COMMAND veritas_d3_selftest)
