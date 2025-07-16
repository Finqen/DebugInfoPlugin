import subprocess
import json
import re
import sys
import argparse
import os

def compile_to_bitcode(source_file, output_file, optimize=False):
    optimization_flag = ["-O3"] if optimize else ["-O0"]
    command = ["clang", "-g", "-emit-llvm", "-c", source_file, "-o", output_file] + optimization_flag
    subprocess.run(command, check=True)

def bitcode_to_ll(bitcode_file, ll_file):
    command = ["llvm-dis", bitcode_file, "-o", ll_file]
    subprocess.run(command, check=True)

def parse_ll_file(ll_file):
    with open(ll_file, 'r') as file:
        content = file.read()
    return content

def extract_source_filename(ll_content):
    """Extract the source_filename from LLVM IR content"""
    # Look for the source_filename line
    match = re.search(r'source_filename\s*=\s*"([^"]+)"', ll_content)
    if match:
        return match.group(1)
    return None

def find_inlined_functions(unoptimized_ll, optimized_ll):
    # Use regular expressions to find function calls in the unoptimized LLVM IR
    unoptimized_function_calls = re.findall(r'call.*@(\w+)\(', unoptimized_ll)

    # Use regular expressions to find function definitions in the optimized LLVM IR
    optimized_function_definitions = re.findall(r'define.*@(\w+)\(', optimized_ll)

    # Determine which functions have been inlined by comparing calls and definitions
    inlined_functions = set(unoptimized_function_calls) - set(optimized_function_definitions)

    # Extract filename information from debug metadata
    filename = extract_source_filename(unoptimized_ll)

    return list(inlined_functions), filename

def find_line_numbers(source_file, functions, filename):
    line_numbers = {func: {"definition": None, "calls": [], "filename": filename} for func in functions}

    if not source_file or not os.path.exists(source_file):
        print(f"Warning: Source file '{source_file}' not found. Line numbers will not be available.")
        return line_numbers

    with open(source_file, 'r') as file:
        lines = file.readlines()
        for line_number, line in enumerate(lines, start=1):
            for func in functions:
                # Check for function definition
                if re.search(rf"\b{func}\b\s*\(", line):
                    if line_numbers[func]["definition"] is None:
                        line_numbers[func]["definition"] = line_number

                # Check for function call, excluding the definition line
                if re.search(rf"\b{func}\b\s*\(", line) and line_number != line_numbers[func]["definition"]:
                    # Ensure it's not a function declaration or definition
                    if not re.search(rf"define.*{func}|declare.*{func}", line):
                        line_numbers[func]["calls"].append(line_number)

    return line_numbers

def main():
    parser = argparse.ArgumentParser(description='Extract inlined function information from LLVM bitcode')
    parser.add_argument('input', help='Source file (.c) or first bitcode file (.bc) when using --nocompile')
    parser.add_argument('-nc', '--nocompile', action='store_true', 
                       help='Skip compilation and use existing bitcode files')
    parser.add_argument('--optimized-bc', 
                       help='Optimized bitcode file (required when using --nocompile)')
    parser.add_argument('-o', '--output', 
                       help='Output JSON file (default: <input_name>_callees.json)')
    parser.add_argument('-s', '--source', 
                       help='Source file for line number extraction (optional when using --nocompile)')
    
    args = parser.parse_args()
    
    if args.nocompile:
        # No-compile mode: use existing bitcode files
        if not args.optimized_bc:
            print("Error: --optimized-bc is required when using --nocompile")
            sys.exit(1)
        
        unoptimized_bc = args.input
        optimized_bc = args.optimized_bc
        
        # Check if bitcode files exist
        if not os.path.exists(unoptimized_bc):
            print(f"Error: Unoptimized bitcode file '{unoptimized_bc}' not found")
            sys.exit(1)
        if not os.path.exists(optimized_bc):
            print(f"Error: Optimized bitcode file '{optimized_bc}' not found")
            sys.exit(1)
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(unoptimized_bc))[0]
        if base_name.endswith('_O0'):
            base_name = base_name[:-3]
        output_json = args.output or f"{base_name}_callees.json"
        
        # Generate .ll file names
        unoptimized_ll = os.path.splitext(unoptimized_bc)[0] + ".ll"
        optimized_ll = os.path.splitext(optimized_bc)[0] + ".ll"
        
        source_file = args.source
        
    else:
        # Normal mode: compile from source
        source_file = args.input
        if not os.path.exists(source_file):
            print(f"Error: Source file '{source_file}' not found")
            sys.exit(1)
        
        source_file_name = os.path.splitext(os.path.basename(source_file))[0]
        unoptimized_bc = source_file_name + "_O0.bc"
        optimized_bc = source_file_name + "_O3.bc"
        unoptimized_ll = unoptimized_bc.replace(".bc", ".ll")
        optimized_ll = optimized_bc.replace(".bc", ".ll")
        output_json = args.output or f"{source_file_name}_callees.json"
        
        # Compile source to bitcode
        print(f"Compiling {source_file} to bitcode...")
        compile_to_bitcode(source_file, unoptimized_bc, optimize=False)
        compile_to_bitcode(source_file, optimized_bc, optimize=True)
    
    # Convert bitcode to LLVM IR
    print(f"Converting bitcode to LLVM IR...")
    bitcode_to_ll(unoptimized_bc, unoptimized_ll)
    bitcode_to_ll(optimized_bc, optimized_ll)
    
    # Parse LLVM IR files
    print(f"Parsing LLVM IR files...")
    unoptimized_content = parse_ll_file(unoptimized_ll)
    optimized_content = parse_ll_file(optimized_ll)
    
    # Find inlined functions
    print(f"Finding inlined functions...")
    inlined_functions, filename = find_inlined_functions(unoptimized_content, optimized_content)
    
    # Extract line numbers from source file
    if inlined_functions:
        print(f"Extracting line numbers for {len(inlined_functions)} inlined functions...")
        line_numbers = find_line_numbers(source_file, inlined_functions, filename)
    else:
        print("No inlined functions found.")
        line_numbers = {}
    
    # Write output JSON
    print(f"Writing output to {output_json}...")
    with open(output_json, 'w') as json_file:
        json.dump(line_numbers, json_file, indent=4)
    
    print(f"Done! Results saved to {output_json}")

if __name__ == "__main__":
    main()
