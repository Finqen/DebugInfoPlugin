import subprocess
import json
import re
import sys
import os
import glob
from pathlib import Path
import argparse

def find_source_files(root_dir, extensions=['.c', '.cpp', '.cc', '.cxx']):
    """Find all source files in a directory tree"""
    source_files = []
    for ext in extensions:
        pattern = f"**/*{ext}"
        source_files.extend(glob.glob(os.path.join(root_dir, pattern), recursive=True))
    return source_files

def find_binaries(build_dir):
    """Find all compiled binaries in the build directory"""
    binaries = []
    # Look for executable files (simplified - you might need to adjust this)
    for root, dirs, files in os.walk(build_dir):
        for file in files:
            filepath = os.path.join(root, file)
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                # Check if it's likely a binary (not a script)
                try:
                    with open(filepath, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'\x7fELF') or header.startswith(b'\x89PNG') == False:
                            binaries.append(filepath)
                except:
                    pass
    return binaries

def extract_object_files_from_binary(binary_path, temp_dir):
    """Extract object files from a binary using objdump or similar tools"""
    object_files = []
    try:
        # Try to get debug info to find source files
        result = subprocess.run(['objdump', '-g', binary_path], 
                              capture_output=True, text=True, check=True)
        
        # Parse objdump output to find source files
        for line in result.stdout.split('\n'):
            if 'DW_AT_name' in line and '.c' in line:
                match = re.search(r'DW_AT_name.*?([^/\s]+\.c)', line)
                if match:
                    source_file = match.group(1)
                    object_files.append(source_file)
    except subprocess.CalledProcessError:
        print(f"Warning: Could not extract debug info from {binary_path}")
    
    return list(set(object_files))  # Remove duplicates

def compile_to_bitcode(source_file, output_file, optimize=False, include_dirs=None, define_flags=None):
    """Compile source file to bitcode with additional flags for package builds"""
    optimization_flag = ["-O3"] if optimize else ["-O0"]
    command = ["clang", "-g", "-emit-llvm", "-c", source_file, "-o", output_file] + optimization_flag
    
    # Add include directories
    if include_dirs:
        for inc_dir in include_dirs:
            command.extend(["-I", inc_dir])
    
    # Add define flags
    if define_flags:
        for define in define_flags:
            command.extend(["-D", define])
    
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to compile {source_file}: {e}")
        return False

def bitcode_to_ll(bitcode_file, ll_file):
    command = ["llvm-dis", bitcode_file, "-o", ll_file]
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def parse_ll_file(ll_file):
    try:
        with open(ll_file, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return None

def extract_source_filename(ll_content):
    """Extract the source_filename from LLVM IR content"""
    if not ll_content:
        return None
    match = re.search(r'source_filename\s*=\s*"([^"]+)"', ll_content)
    if match:
        return match.group(1)
    return None

def find_inlined_functions(unoptimized_ll, optimized_ll):
    if not unoptimized_ll or not optimized_ll:
        return [], None
    
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
    if not functions or not os.path.exists(source_file):
        return {}
    
    line_numbers = {func: {"definition": None, "calls": [], "filename": filename} for func in functions}

    try:
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
    except Exception as e:
        print(f"Warning: Could not read {source_file}: {e}")

    return line_numbers

def analyze_source_file(source_file, include_dirs=None, define_flags=None, temp_dir="temp"):
    """Analyze a single source file"""
    if not os.path.exists(source_file):
        return None
    
    # Create temporary directory
    os.makedirs(temp_dir, exist_ok=True)
    
    source_file_name = os.path.basename(source_file).replace(".c", "").replace(".cpp", "")
    unoptimized_bc = os.path.join(temp_dir, f"{source_file_name}_O0.bc")
    optimized_bc = os.path.join(temp_dir, f"{source_file_name}_O3.bc")
    unoptimized_ll = unoptimized_bc.replace(".bc", ".ll")
    optimized_ll = optimized_bc.replace(".bc", ".ll")

    # Compile to bitcode
    if not compile_to_bitcode(source_file, unoptimized_bc, optimize=False, 
                             include_dirs=include_dirs, define_flags=define_flags):
        return None
    
    if not compile_to_bitcode(source_file, optimized_bc, optimize=True, 
                             include_dirs=include_dirs, define_flags=define_flags):
        return None

    # Convert to LLVM IR
    if not bitcode_to_ll(unoptimized_bc, unoptimized_ll):
        return None
    if not bitcode_to_ll(optimized_bc, optimized_ll):
        return None

    # Parse LLVM IR
    unoptimized_content = parse_ll_file(unoptimized_ll)
    optimized_content = parse_ll_file(optimized_ll)

    # Find inlined functions
    inlined_functions, filename = find_inlined_functions(unoptimized_content, optimized_content)
    line_numbers = find_line_numbers(source_file, inlined_functions, filename)

    # Clean up temporary files
    for temp_file in [unoptimized_bc, optimized_bc, unoptimized_ll, optimized_ll]:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return {
        "source_file": source_file,
        "inlined_functions": line_numbers
    }

def get_package_build_info(package_dir):
    """Extract build information from package (Makefile, configure, etc.)"""
    include_dirs = []
    define_flags = []
    
    # Look for common include directories
    common_includes = ['include', 'src', 'lib', '.']
    for inc_dir in common_includes:
        full_path = os.path.join(package_dir, inc_dir)
        if os.path.exists(full_path):
            include_dirs.append(full_path)
    
    # Try to extract defines from config.h if it exists
    config_h = os.path.join(package_dir, 'config.h')
    if os.path.exists(config_h):
        try:
            with open(config_h, 'r') as f:
                content = f.read()
                defines = re.findall(r'#define\s+(\w+)', content)
                define_flags.extend(defines[:10])  # Limit to avoid too many flags
        except:
            pass
    
    return include_dirs, define_flags

def main():
    parser = argparse.ArgumentParser(description='Analyze inlined functions in a package')
    parser.add_argument('package_dir', help='Path to the package source directory')
    parser.add_argument('--output', '-o', default='package_analysis.json', 
                       help='Output JSON file')
    parser.add_argument('--temp-dir', default='temp_analysis', 
                       help='Temporary directory for intermediate files')
    parser.add_argument('--include-dirs', nargs='*', 
                       help='Additional include directories')
    parser.add_argument('--defines', nargs='*', 
                       help='Additional preprocessor defines')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.package_dir):
        print(f"Error: Package directory {args.package_dir} does not exist")
        return 1
    
    # Get build information
    include_dirs, define_flags = get_package_build_info(args.package_dir)
    
    # Add user-specified includes and defines
    if args.include_dirs:
        include_dirs.extend(args.include_dirs)
    if args.defines:
        define_flags.extend(args.defines)
    
    # Find all source files
    source_files = find_source_files(args.package_dir)
    print(f"Found {len(source_files)} source files")
    
    # Create output directory
    os.makedirs(args.temp_dir, exist_ok=True)
    
    # Analyze each source file
    results = {}
    for i, source_file in enumerate(source_files):
        print(f"Analyzing {source_file} ({i+1}/{len(source_files)})")
        result = analyze_source_file(source_file, include_dirs, define_flags, args.temp_dir)
        if result:
            results[source_file] = result
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Analysis complete. Results saved to {args.output}")
    print(f"Analyzed {len(results)} source files successfully")
    
    # Clean up temp directory
    import shutil
    if os.path.exists(args.temp_dir):
        shutil.rmtree(args.temp_dir)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())