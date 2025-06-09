cmake_minimum_required(VERSION 3.13)

project(DebugInfoPlugin LANGUAGES CXX)

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

include_directories(${LLVM_INCLUDE_DIRS})
include_directories(${CLANG_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

add_library(DebugInfoPlugin MODULE DebugInfoPlugin.cpp)

set_target_properties(DebugInfoPlugin PROPERTIES
  COMPILE_FLAGS "-fno-rtti"
)

target_link_libraries(DebugInfoPlugin
  PRIVATE
  clangTooling
  clangBasic
  clangASTMatchers
)

