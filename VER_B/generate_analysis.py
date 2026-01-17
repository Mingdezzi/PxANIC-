import os
import ast

OUTPUT_FILE = "project_complete_analysis.txt"
TARGET_DIR = "."

def get_py_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "generate_analysis.py":
                py_files.append(os.path.join(root, file))
    return sorted(py_files)

def analyze_ast(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        tree = ast.parse(content)
        structure = []
        details = []

        # Global Variables (Settings)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        val = "Dynamic/Complex"
                        if isinstance(node.value, ast.Constant):
                            val = node.value.value
                        elif isinstance(node.value, ast.List):
                            val = f"[List with {len(node.value.elts)} elements]"
                        elif isinstance(node.value, ast.Dict):
                            val = f"{{Dict with {len(node.value.keys)} keys}}"
                        details.append(f"  [Global Variable] {target.id} = {val}")

        # Classes and Functions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                structure.append(f"  [Class] {node.name}")
                details.append(f"\n  [Class] {node.name}")
                if ast.get_docstring(node):
                    details.append(f"    - Doc: {ast.get_docstring(node).strip()}")
                
                # Methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        args = [a.arg for a in item.args.args]
                        structure.append(f"    └── [Method] {item.name}({', '.join(args)})")
                        details.append(f"    [Method] {item.name}({', '.join(args)})")
                        if ast.get_docstring(item):
                            details.append(f"      - Doc: {ast.get_docstring(item).strip()}")

            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                structure.append(f"  [Function] {node.name}({', '.join(args)})")
                details.append(f"\n  [Function] {node.name}({', '.join(args)})")
                if ast.get_docstring(node):
                    details.append(f"    - Doc: {ast.get_docstring(node).strip()}")

        return structure, details, content
    except Exception as e:
        return [f"  [Error Parsing] {e}"], [f"  [Error] Could not parse AST: {e}"], ""

def main():
    py_files = get_py_files(TARGET_DIR)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        # Header
        out.write("="*80 + "\n")
        out.write("PROJECT COMPLETE ANALYSIS REPORT\n")
        out.write(f"Total Files: {len(py_files)}\n")
        out.write("="*80 + "\n\n")

        # Section 1: Structure Overview
        out.write("(1) PROJECT STRUCTURE TREE\n")
        out.write("="*40 + "\n")
        
        file_analyses = {}

        for file_path in py_files:
            rel_path = os.path.relpath(file_path, TARGET_DIR)
            out.write(f"\n[FILE] {rel_path}\n")
            struct, det, content = analyze_ast(file_path)
            file_analyses[file_path] = (det, content)
            
            if not struct:
                out.write("  (No Classes or Functions detected - likely settings/constants only)\n")
            for s in struct:
                out.write(f"{s}\n")

        out.write("\n\n" + "="*80 + "\n")
        out.write("(2) DETAILED CODE & EXPLANATION\n")
        out.write("="*80 + "\n")

        # Section 2: Detailed Code
        for file_path in py_files:
            rel_path = os.path.relpath(file_path, TARGET_DIR)
            details, content = file_analyses[file_path]

            out.write(f"\n\n{'#'*80}\n")
            out.write(f" FILE: {rel_path}\n")
            out.write(f"{'#'*80}\n")
            
            out.write("\n--- [Code Analysis & Settings] ---\n")
            if not details:
                out.write("  (No specific structural elements found)\n")
            for d in details:
                out.write(f"{d}\n")
            
            out.write("\n--- [Full Source Code] ---\n")
            # If content was failed to read in analyze_ast, try read again or skip
            if not content:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except:
                    content = "# Error reading file content."
            
            out.write(content)
            out.write("\n")

    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
