# DebugInfoPlugin

## Clang plugin for enhancing debug information on binaries compiled with optimization

### Usage

> mkdir build && cd build && cmake .. && make

> clang -g -O3 -Xclang -load -Xclang build/libDebugInfoPlugin.so test/inline.c -o test/inline

> dwarf-writer -u -b inline.json inline inline_enh
