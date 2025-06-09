# DebugInfoPlugin

## Clang plugin for enhancin debug information on binaries compiled with optimization

### Usage

> cd build && cmake .. && make

> cd .. && clang -Xclang -load -Xclang build/libDebugInfoPlugin.so test/test.c 
