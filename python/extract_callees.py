import subprocess
import json
import re
import sys

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

def main(source_file):
    source_file_name = source_file.split('/')[-1].replace(".c", "")
    unoptimized_bc = source_file_name + "_O0.bc"
    optimized_bc = source_file_name + "_O3.bc"
    unoptimized_ll = unoptimized_bc.replace(".bc", ".ll")
    optimized_ll = optimized_bc.replace(".bc", ".ll")
    output_json = source_file_name + "_callees.json"

    compile_to_bitcode(source_file, unoptimized_bc, optimize=False)
    compile_to_bitcode(source_file, optimized_bc, optimize=True)

    bitcode_to_ll(unoptimized_bc, unoptimized_ll)
    bitcode_to_ll(optimized_bc, optimized_ll)

    unoptimized_content = parse_ll_file(unoptimized_ll)
    optimized_content = parse_ll_file(optimized_ll)

    inlined_functions, filename = find_inlined_functions(unoptimized_content, optimized_content)
    line_numbers = find_line_numbers(source_file, inlined_functions, filename)

    with open(output_json, 'w') as json_file:
        json.dump(line_numbers, json_file, indent=4)

if __name__ == "__main__":
    main(sys.argv[1])
