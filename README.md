# Web Locator Extraction System

## Overview
Automated system that crawls web applications, extracts UI locators, and provides API access to the data.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Setup PostgreSQL
```bash
# Install PostgreSQL and create database
createdb locator_system
```

### 3. Environment Setup
```bash
# Copy and configure environment file
copy .env.example .env
# Edit .env with your database credentials and target application details
```

### 4. Initialize Database
```bash
python database/setup.py
```

### 5. Start FastAPI Server
```bash
python backend/main.py
```
Server will start at http://localhost:8000

### 6. Run Crawler
```bash
python crawler/main.py
```

## API Documentation

### Endpoints

#### GET /screens
Returns all crawled screens
```json
[
  {
    "id": 1,
    "url": "https://app.com/dashboard",
    "name": "dashboard",
    "title": "Dashboard - MyApp",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00"
  }
]
```

#### GET /elements/{screen_id}
Returns all elements for a specific screen
```json
[
  {
    "id": 1,
    "screen_id": 1,
    "element_name": "Login Button",
    "element_type": "button",
    "element_id": "login-btn",
    "css_selector": "#login-btn",
    "xpath": "//button[@id='login-btn']",
    "verified": false
  }
]
```

#### GET /locator?screen={name}&element={name}
Get specific locator for an element
```json
{
  "css_selector": "#login-btn",
  "xpath": "//button[@id='login-btn']",
  "element_id": "login-btn",
  "data_testid": null,
  "verified": false
}
```

#### POST /add-locator
Add a new locator manually
```json
{
  "screen_id": 1,
  "element_name": "Submit Button",
  "element_type": "button",
  "css_selector": "#submit",
  "xpath": "//button[@id='submit']"
}
```

#### PUT /verify-locator/{element_id}
Mark locator as verified/unverified
```json
{
  "verified": true
}
```

## Usage Examples

### Using the API to get locators
```python
import requests

# Get all screens
screens = requests.get("http://localhost:8000/screens").json()

# Get elements for first screen
elements = requests.get(f"http://localhost:8000/elements/{screens[0]['id']}").json()

# Get specific locator
locator = requests.get(
    "http://localhost:8000/locator",
    params={"screen": "dashboard", "element": "Login Button"}
).json()

print(f"CSS Selector: {locator['css_selector']}")
print(f"XPath: {locator['xpath']}")
```

### Customizing the Crawler

To customize the crawler for your specific application, modify the `login` method in `crawler/web_crawler.py`:

```python
def login(self, page: Page, username: str, password: str, login_url: str = None):
    login_url = login_url or f"{self.base_url}/login"
    page.goto(login_url)
    
    # Your specific login logic here
    page.fill('#email', username)
    page.fill('#password', password)
    page.click('button[type="submit"]')
    
    # Wait for successful login
    page.wait_for_selector('.dashboard', timeout=10000)
```

## Architecture

- **Crawler**: Playwright-based web crawler that extracts locators
- **Backend**: FastAPI REST API for locator management
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Communication**: HTTP API calls between crawler and backend

## Security Notes

- Store credentials in environment variables
- Use HTTPS in production
- Implement authentication for the API in production
- Validate all input data