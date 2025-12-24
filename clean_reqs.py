import os

def clean_requirements():
    file_path = 'backend/requirements.txt'
    
    # Try reading with different encodings
    content = ""
    try:
        with open(file_path, 'r', encoding='utf-16le') as f:
            content = f.read()
    except:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return

    lines = content.splitlines()
    cleaned_lines = []
    
    # Blocklist of Windows-only or problematic packages
    blocklist = [
        "pywin32", "pypiwin32", "win32", "wmi", "pyobjc", 
        "pytricia", "appscript", "xattr" 
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line starts with any blocklisted package
        # (package name is usually at start, followed by == or @ or just end)
        package_name = line.split('=')[0].split('<')[0].split('>')[0].split('@')[0].strip().lower()
        
        if package_name in blocklist:
            print(f"Removing: {line}")
            continue
            
        # Also remove local file paths if any (common in pip freeze on windows)
        if " @ file:///" in line:
             print(f"Removing local path: {line}")
             continue

        # Fix torch/cuda specific versions (e.g. 2.5.1+cu121 -> 2.5.1)
        if "+cu" in line:
            line = line.split("+cu")[0]
            print(f"Sanitized CUDA version: {line}")
             
        cleaned_lines.append(line)
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned_lines))
        
    print("requirements.txt cleaned and saved as UTF-8.")

if __name__ == "__main__":
    clean_requirements()
