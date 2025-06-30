# DebugInfoPlugin

## Clang plugin for enhancing debug information on binaries compiled with optimization

### Usage

> cd build && cmake .. && make

> clang -g -O3 -Xclang -load -Xclang build/libDebugInfoPlugin.so test/inline.c -o test/inline
