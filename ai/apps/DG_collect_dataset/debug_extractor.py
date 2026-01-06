import ast
import os
import sys

# Define the target file
TARGET_FILE = 'DG_collect_dataset.py'

def extract_clean_step():
    if not os.path.exists(TARGET_FILE):
        print(f"❌ Could not find {TARGET_FILE}")
        return

    print(f"🔍 Scanning {TARGET_FILE} for the 'clean' step...")
    
    try:
        with open(TARGET_FILE, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        found = False
        for node in ast.walk(tree):
            # We look for functions with "clean" or "step_4" in the name
            if isinstance(node, ast.FunctionDef) and ('clean' in node.name.lower() or '04' in node.name):
                found = True
                print(f"\nFound Function: {node.name}")
                print("-" * 40)
                # Extract the source lines for this function
                # (Python 3.8+ support for end_lineno)
                try:
                    lines = source.splitlines()[node.lineno-1 : node.end_lineno]
                    print("\n".join(lines))
                except Exception:
                    # Fallback: print the first line only
                    print(source.splitlines()[node.lineno-1])
                print("-" * 40)
        
        if not found:
            print("⚠️ Could not verify a specific function named 'clean' or '04'.")
            print("Please manually check the code following the print statement: '--> [04_clean] Running Step 4...'")

    except Exception as e:
        print(f"❌ Error parsing file: {e}")

if __name__ == "__main__":
    extract_clean_step()
