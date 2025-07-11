cmake_minimum_required(VERSION 3.13)
project(DetectInlinedCallsPass LANGUAGES CXX)

find_package(LLVM REQUIRED CONFIG)
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")

include_directories(${LLVM_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

add_library(DetectInlinedCallsPass SHARED DetectInlinedCallsPass.cpp)

set_target_properties(DetectInlinedCallsPass PROPERTIES
  COMPILE_FLAGS "-fno-rtti"
)

llvm_map_components_to_libnames(llvm_libs support core irreader)
target_link_libraries(DetectInlinedCallsPass PRIVATE ${llvm_libs})
