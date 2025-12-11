import json
import os

target_file = r'c:\locator-system\session_export.json'

try:
    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("Successfully formatted JSON.")
except Exception as e:
    print(f"Error: {e}")
