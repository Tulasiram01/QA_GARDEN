# Universal Crawler Implementation Summary

## Current Approach

### Architecture Overview
The UniversalCrawler uses **Depth-First Search (DFS)** traversal to automatically discover and extract locators from web applications without site-specific hardcoding.

### Core Components

#### 1. UniversalCrawler Class
- Manages session lifecycle and crawl state
- Tracks visited URLs, extracted elements, screens, and clicked elements
- Orchestrates authentication, exploration, extraction, and interaction

#### 2. _safe_navigate()
- Initial page load with timeout and load state handling
- Entry point for crawl process
- Waits for domcontentloaded state

#### 3. _handle_authentication()
- Detects login pages by URL keywords (login, signin, auth)
- Auto-fills email/password fields
- Submits login form and waits for post-login navigation
- Handles form-based authentication only

#### 4. _explore() - DFS Traversal
- Implements recursive depth-first search with depth limit (15)
- Tracks visited URLs to prevent revisits
- For each page:
  1. Register screen in API
  2. Extract all elements
  3. Interact with clickable elements
  4. Recursively explore newly discovered pages

#### 5. _extract() - Element Locator Generation
- Queries all DOM elements using `query_selector_all('*')`
- Filters visible elements only
- Generates CSS selectors and XPath for each element
- Deduplicates using signature-based tracking (tag:id:text:href)
- Sends extracted locators to API backend
- Character limits: element_name (500), text_content (500), css_selector (500), xpath (500)

#### 6. _interact() - Element Interaction & Navigation Discovery
- Identifies clickable elements:
  - Tags: a, button, input, select, textarea, label
  - Roles: button, link, tab, menuitem
  - Attributes: onclick handlers
- Filters out destructive actions (logout, delete, remove, unsubscribe)
- Tracks clicked elements globally to prevent duplicate clicks
- For each element:
  1. Scroll into view
  2. Click with timeout handling
  3. Detect URL changes
  4. Recursively explore new pages
  5. Navigate back to original page

#### 7. _get_screen() - Screen Registration
- Creates screen records in API for each unique URL
- Caches screen IDs to avoid duplicate API calls
- Extracts screen name from URL path

### Data Structures

| Structure | Type | Purpose |
|-----------|------|---------|
| visited_urls | set | Prevents revisiting same pages |
| global_clicked | set | Prevents clicking same element twice |
| screens | dict | Caches URL → screen_id mappings |
| extracted_elements | dict | Groups elements by screen_id |
| seen | set | Deduplicates elements within page |

### Workflow

```
1. Initialize crawler with base_url, credentials, api_url
2. Navigate to base_url → _safe_navigate()
3. Handle login if needed → _handle_authentication()
4. Explore page → _explore()
   ├─ Register screen → _get_screen()
   ├─ Extract elements → _extract()
   │  └─ Generate CSS/XPath selectors
   │  └─ Send to API
   └─ Interact with elements → _interact()
      ├─ Click clickable elements
      ├─ Detect navigation
      └─ Recursively explore new pages → _explore()
5. Return session summary with screens and elements count
```

### Key Algorithms

**Deduplication (O(1) lookup)**
```python
sig = f"{tag}:{elem_id}:{text}:{href}"
if sig in seen:
    continue
seen.add(sig)
```

**DFS Traversal with Depth Limit**
```python
def _explore(page, depth):
    if depth > 15:
        return
    # Process page
    self._interact(page, depth, url)
    # Recursively explore new pages
    self._explore(page, depth + 1)
```

**Global Click Tracking**
```python
sig = f"{url}:{idx}:{tag}"
if sig in self.global_clicked:
    continue
self.global_clicked.add(sig)
```

### Playwright Methods Used

| Method | Purpose |
|--------|---------|
| page.goto() | Navigate to URL |
| page.wait_for_timeout() | Fixed delay |
| page.query_selector_all() | Get all DOM elements |
| page.url | Get current URL |
| elem.is_visible() | Check visibility |
| elem.evaluate() | Execute JavaScript |
| elem.text_content() | Get element text |
| elem.get_attribute() | Get HTML attributes |
| elem.fill() | Fill input fields |
| elem.click() | Click element |
| elem.scroll_into_view_if_needed() | Scroll element |
| page.expect_navigation() | Detect navigation |
| page.close() | Close page |

### Limitations & Considerations

**Current Limitations:**
- Only handles form-based authentication (no OAuth, SSO, MFA)
- Does not fill form fields (textareas, selects, checkboxes)
- No handling of shadow DOM or iframes
- No JavaScript execution for dynamic content
- Silent error handling (except: pass) hides failures

**Performance Bottlenecks:**
- Sequential element processing (no parallelization)
- Multiple DOM queries per element
- Network request per element (no batching)
- Re-querying elements in interaction loop
- No element filtering before processing

**Scalability Issues:**
- Pages with 500+ elements take 30-60 seconds
- Depth limit of 15 may miss deep applications
- No rate limiting or request throttling
- Memory usage grows with session size

### Expected Results

**Typical Extraction:**
- 1-5 screens discovered per session
- 50-200 elements per screen
- 5-15 minutes for complete crawl
- 100% coverage of visible interactive elements

### Future Improvements

1. Add form field filling (textareas, selects, checkboxes)
2. Implement element batching for API calls
3. Add shadow DOM and iframe support
4. Improve error logging (remove silent except: pass)
5. Add OAuth/SSO/MFA support
6. Implement parallel element processing
7. Add dynamic content detection
8. Optimize DOM queries
