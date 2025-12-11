import os
import sys
import argparse
import getpass
from playwright.sync_api import sync_playwright
from smart_crawler import SmartCrawler
from dotenv import load_dotenv

# Load .env from parent directory (optional)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_credentials():
    """Get credentials from command line args, env, or interactive input"""
    parser = argparse.ArgumentParser(description='Smart UI Crawler - Extract locators from any web application')
    parser.add_argument('--url', help='Target application URL')
    parser.add_argument('--username', help='Login username/email')
    parser.add_argument('--password', help='Login password')
    parser.add_argument('--api-url', help='API base URL')
    parser.add_argument('--no-login', action='store_true', help='Skip login (for public apps)')
    
    args = parser.parse_args()
    
    # Get URL
    base_url = args.url or os.getenv('TARGET_APP_URL')
    if not base_url:
        base_url = input("Enter target application URL: ").strip()
    
    # Get credentials if login required
    username = password = None
    if not args.no_login:
        username = args.username or os.getenv('LOGIN_USERNAME')
        password = args.password or os.getenv('LOGIN_PASSWORD')
        
        if not username:
            username = input("Enter username/email: ").strip()
        if not password:
            password = getpass.getpass("Enter password: ")
    
    api_url = args.api_url or os.getenv('API_BASE_URL', 'http://localhost:8000')
    
    return base_url, username, password, api_url, args.no_login

def main():
    print("=== Interactive Locator Extractor ===")
    print("Extract locators from any web application\n")
    
    # Get configuration
    base_url, username, password, api_url, skip_login = get_credentials()
    
    if not base_url:
        print("ERROR: Target URL is required")
        return 1
    
    # Test API connection before starting
    print(f"\nTesting API connection at {api_url}...")
    try:
        import requests
        response = requests.get(f"{api_url}/pages", timeout=5)
        if response.status_code == 200:
            print("  ✓ API server is running\n")
        else:
            print(f"  ✗ API returned status {response.status_code}")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to API server at {api_url}")
        print("\n  Please start the API server first:")
        print("    cd backend")
        print("    python main.py\n")
        return 1
    except Exception as e:
        print(f"  ✗ API test failed: {e}")
        return 1
    
    print(f"Starting Interactive Locator Extractor")
    print(f"Target: {base_url}")
    print(f"API: {api_url}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        crawler = SmartCrawler(base_url, username, password, api_url, skip_login)
        
        try:
            results = crawler.crawl(browser)
            
            if "error" in results:
                print(f"ERROR: {results['error']}")
                return 1
            
            print(f"\n{'='*60}")
            print(f"Extraction completed!")
            print(f"  - Session ID: {results['session_id']}")
            print(f"  - Screens discovered: {results['screens_discovered']}")
            print(f"  - Total elements extracted: {results['total_elements']}")
            
            if results.get('fallback_saved'):
                print(f"\n⚠ Data saved to fallback file (API was unavailable)")
                print(f"  - Import with: python import_fallback.py {results['session_id']}_fallback.json")
            else:
                print(f"\nData saved to API at: {api_url}")
                print(f"  - View session (pages + elements): {api_url}/session/{results['session_id']}")
                print(f"  - API docs: {api_url}/docs")
            print(f"{'='*60}")
            return 0
            
        except Exception as e:
            import traceback
            print(f"ERROR: Extraction failed: {e}")
            traceback.print_exc()
            return 1
        finally:
            browser.close()

if __name__ == "__main__":
    import sys
    sys.exit(main())