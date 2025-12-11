import json
import sys
import requests

if len(sys.argv) < 2:
    print("Usage: python import_fallback.py <fallback_file.json>")
    sys.exit(1)

fallback_file = sys.argv[1]
API_URL = "http://localhost:8000"

print(f"\nImporting fallback data from: {fallback_file}")

try:
    with open(fallback_file, 'r') as f:
        data = json.load(f)
    
    print(f"Found {len(data['screens'])} screens and {len(data['elements'])} elements")
    
    # Test API
    try:
        requests.get(f"{API_URL}/screens", timeout=5)
    except:
        print("\nERROR: API server not running. Start with: python backend/main.py")
        sys.exit(1)
    
    # Import screens
    screen_map = {}
    for url, screen_data in data['screens'].items():
        resp = requests.post(f"{API_URL}/screens", json=screen_data)
        if resp.status_code in [200, 201]:
            screen_map[url] = resp.json()['id']
            print(f"  Created screen: {screen_data['name']}")
    
    # Import elements
    success = 0
    for elem in data['elements']:
        screen_url = elem.pop('screen_url')
        screen_name = elem.pop('screen_name')
        
        if screen_url in screen_map:
            elem['screen_id'] = screen_map[screen_url]
            resp = requests.post(f"{API_URL}/add-locator", json=elem)
            if resp.status_code in [200, 201]:
                success += 1
    
    print(f"\nImport complete!")
    print(f"  - Screens: {len(screen_map)}")
    print(f"  - Elements: {success}/{len(data['elements'])}")
    print(f"\nView at: {API_URL}/screens?session_id={data['screens'][list(data['screens'].keys())[0]]['session_id']}")

except FileNotFoundError:
    print(f"ERROR: File not found: {fallback_file}")
except Exception as e:
    print(f"ERROR: {e}")
