from playwright.sync_api import Page, Browser
import requests
import time
import re
import json
import os
from datetime import datetime

class SmartCrawler:
    def __init__(self, base_url, username, password, api_url, skip_login=False, login_button_texts=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_url = api_url
        self.skip_login = skip_login
        self.login_button_texts = login_button_texts or os.getenv('LOGIN_BUTTON_TEXTS', 'login,sign in').split(',')
        self.visited_urls = set()
        self.extracted_elements = set()
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.auto_logged_in = False
        self.navigation_count = {}
        self.fallback_data = {'screens': {}, 'elements': []}
        self.api_available = True
        self.fallback_file = f"{self.session_id}_fallback.json"
        self.screen_cache = {}  # Cache screen_id by URL
        
    def crawl(self, browser: Browser):
        page = browser.new_page()
        page.goto(self.base_url)
        page.wait_for_timeout(3000)
        
        print(f"\n=== Starting Interactive Extraction ===")
        print(f"Session ID: {self.session_id}")
        print(f"Current URL: {page.url}\n")
        
        self._interactive_explore(page)
        
        # Save fallback data if any
        if len(self.fallback_data['elements']) > 0:
            self._save_fallback_to_file()
        
        return {
            "session_id": self.session_id,
            "total_elements": len(self.extracted_elements),
            "screens_discovered": len(self.visited_urls),
            "interactions_performed": len(self.visited_urls),
            "fallback_saved": len(self.fallback_data['elements']) > 0
        }
    
    def _interactive_explore(self, page: Page):
        """Interactive exploration - extracts everything and waits for user actions"""
        
        force_rescan = False
        
        while True:
            current_url = page.url
            
            # Auto-scroll to reveal all elements
            try:
                page.evaluate("""
                    () => {
                        window.scrollTo(0, 0);
                        const scrollStep = () => {
                            window.scrollBy(0, window.innerHeight / 2);
                        };
                        for (let i = 0; i < 10; i++) {
                            setTimeout(scrollStep, i * 100);
                        }
                        setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 1000);
                        setTimeout(() => window.scrollTo(0, 0), 1500);
                    }
                """)
                page.wait_for_timeout(2000)
            except:
                pass
            
            # Skip if already extracted from this URL in this loop, unless forced
            if current_url in self.visited_urls and not force_rescan:
                pass  # Already extracted, just show menu
            else:
                # Extract all elements from current page
                print(f"\n{'='*60}")
                print(f"Extracting locators from: {current_url}")
                if force_rescan:
                    print(f"(Rescan triggered by manual interaction)")
                print(f"{'='*60}")
                try:
                    self._extract_all_elements(page)
                    self.visited_urls.add(current_url)
                except:
                    print("  ⚠ Page navigated during extraction")
                force_rescan = False  # Reset flag
            
            # Show what's on the page
            try:
                interactive_elements = self._get_all_interactive_elements(page)
            except:
                interactive_elements = []
            print(f"\nFound {len(interactive_elements)} interactive elements on this page")
            
            # Show options to user
            print("\n" + "="*60)
            print("OPTIONS:")
            print("  1. Continue exploring (crawler will auto-click elements)")
            print("  2. Manual interaction (auto-detects errors/popups)")
            print("  3. Stop crawling")
            print("="*60)
            
            choice = input("\nEnter your choice (1/2/3): ").strip()
            
            if choice == "3":
                print("\nStopping crawler...")
                break
            elif choice == "2":
                print("\n" + "="*60)
                print(">>> CONTINUOUS MONITORING MODE ACTIVATED <<<")
                print("="*60)
                print("\nThe crawler will now watch for changes automatically.")
                print("Interact freely with the page:")
                print("  - Fill forms, trigger validation errors")
                print("  - Click buttons, links, navigate pages")
                print("  - The crawler extracts after EACH action automatically\n")
                print("Press ENTER when you're completely done with ALL interactions.\n")
                
                self._continuous_monitor(page)
                force_rescan = True
            elif choice == "1":
                print("\n>>> Auto-exploring elements <<<")
                self._auto_explore_elements(page, interactive_elements)
            else:
                print("Invalid choice, continuing...")
    
    def _auto_explore_elements(self, page: Page, elements: list):
        """Auto-click elements and extract locators (including errors/tooltips)"""
        
        # Auto-login if not done yet and credentials available
        if not self.auto_logged_in and not self.skip_login and self.username and self.password:
            if self._attempt_auto_click_login(page):
                self.auto_logged_in = True
                print("  ✓ Auto-login successful!")
                page.wait_for_timeout(3000)
                self._extract_all_elements(page)
                return  # Return to main loop to re-scan page
        
        for i, elem in enumerate(elements[:20]):
            try:
                print(f"\n[{i+1}/{min(20, len(elements))}] Clicking: {elem['text'][:50]}")
                
                snapshot_url = page.url
                
                # Skip if already visited this URL multiple times
                if self.navigation_count.get(snapshot_url, 0) >= 2:
                    print(f"  → Skipped (already explored this page)")
                    continue
                
                # Click element
                clicked = self._click_element(page, elem)
                if not clicked:
                    continue
                
                page.wait_for_timeout(1500)
                
                # Extract errors/tooltips/popups that appeared
                self._extract_all_elements(page)
                
                # Check if URL changed
                if page.url != snapshot_url:
                    print(f"  → Navigated to: {page.url}")
                    print("  → Extracting from new page...")
                    self._extract_all_elements(page)
                    
                    # Track navigation
                    self.navigation_count[page.url] = self.navigation_count.get(page.url, 0) + 1
                    
                    # Auto-continue if not visited too many times
                    if self.navigation_count.get(page.url, 0) <= 1:
                        print("  → Auto-continuing on new page...")
                        return  # Exit to main loop which will handle new page
                    else:
                        print("  → Already explored, going back...")
                        page.go_back()
                        page.wait_for_timeout(2000)
                else:
                    print(f"  → Stayed on same page, extracted dynamic elements")
                
            except Exception as e:
                print(f"  → Error: {str(e)[:50]}")
                try:
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(500)
                except:
                    pass
    
    def _get_all_interactive_elements(self, page: Page):
        """Get ALL interactive elements AND static content from page with smart sorting"""
        try:
            return page.evaluate("""
                () => {
                    const all = Array.from(document.querySelectorAll('*'));
                    const visible = all.filter(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
                    });
                    
                    const interactive = visible.filter(el => {
                        const tag = el.tagName.toLowerCase();
                        const role = el.getAttribute('role') || '';
                        const classes = (el.className || '').toString().toLowerCase();
                        const onclick = el.onclick || el.hasAttribute('onclick');
                        const ariaLabel = el.getAttribute('aria-label');
                        
                        // Check computed style for cursor pointer (Key for React/Framework/Div buttons)
                        const style = window.getComputedStyle(el);
                        const isPointer = style.cursor === 'pointer';
                        
                        // TEXT LOGIC: Check for "Own Text" (text directly in this node, not children)
                        const childText = Array.from(el.children).map(c => c.textContent).join('');
                        const fullText = el.textContent || '';
                        const ownText = fullText.replace(childText, '').trim();
                        const hasOwnText = ownText.length > 0;
                        
                        const validStartTags = ['h1','h2','h3','h4','h5','h6','p','label','span','div','b','strong','i','em','small','li', 'td', 'th'];
                        const text = (el.textContent || '').trim().toLowerCase();

                        // 1. Standard Interactive
                        const isStandard = ['button','a','input','select','textarea','form'].includes(tag) ||
                               (tag === 'img' && (el.alt || el.title || onclick || isPointer)) || 
                               ['button','link','menuitem','option','combobox', 'checkbox', 'radio', 'switch', 'tab'].includes(role) ||
                               classes.includes('btn') || classes.includes('button') || classes.includes('clickable') || onclick || isPointer;
                        
                        // 2. Non-standard Interactive & SVGs
                        const isAriaInteractive = role === 'button' || 
                            (ariaLabel && !['body','html','main','section','article','header','footer'].includes(tag));
                        
                        // 3. Icons & SVGs
                        const isSemanticIcon = (tag === 'svg' || tag === 'img') && 
                            (ariaLabel || onclick || role === 'img' || role === 'button' || el.getAttribute('data-icon') || el.querySelector('title') || isPointer);

                        // 4. Static Content (Headings, Labels, Text, Errors)
                        const isContent = validStartTags.includes(tag) && hasOwnText;

                        return isStandard || isAriaInteractive || isSemanticIcon || isContent;
                    });
                    
                    return interactive.map((el, idx) => {
                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.textContent || el.alt || '').trim();
                        const tag = el.tagName.toLowerCase();
                        const type = el.type || '';
                        const role = el.getAttribute('role') || '';
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        
                        // Assign priority for smart sorting
                        let priority = 3; // Default: buttons, links
                        
                        // Priority 1: Input fields (text, email, password, etc.)
                        if (tag === 'input' && !['submit','button','reset'].includes(type)) {
                            priority = 1;
                        }
                        if (tag === 'textarea') {
                            priority = 1;
                        }
                        
                        // Priority 2: Dropdowns and selects
                        if (tag === 'select' || role === 'combobox' || role === 'listbox') {
                            priority = 2;
                        }
                        
                        // Priority 3: Buttons and links (default)
                        
                        // Priority 5: Static Content (Headings, textual spans/divs)
                        if (!['button','a','input','select','textarea'].includes(tag) && role !== 'button' && !ariaLabel) {
                             if (tag.startsWith('h')) priority = 5; // Headings
                             else priority = 6; // Other text
                        }
                        
                        return {
                            idx: idx,
                            text: text.substring(0, 100),
                            tag: tag,
                            type: type,
                            role: role,
                            id: el.id || null,
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            priority: priority
                        };
                    }).sort((a, b) => {
                        // Sort by priority first 
                        if (a.priority !== b.priority) {
                            return a.priority - b.priority;
                        }
                        // Then by visual position (top-to-bottom, left-to-right)
                        const yDiff = a.y - b.y;
                        if (Math.abs(yDiff) > 50) return yDiff;
                        return a.x - b.x;
                    });
                }
            """)
        except:
            return []
    
    def _continuous_monitor(self, page: Page):
        """Continuously monitor page for changes and auto-extract"""
        import select
        import sys
        
        last_url = page.url
        
        print("Monitoring started...")
        print("Interact freely - fill forms, click buttons, navigate pages.")
        print("Press ENTER when completely done with ALL interactions.\n")
        
        page.evaluate("""
            () => {
                window.__changeDetected = false;
                const observer = new MutationObserver(() => {
                    window.__changeDetected = true;
                });
                observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    characterData: true
                });
            }
        """)
        
        while True:
            if sys.platform == 'win32':
                import msvcrt
                if msvcrt.kbhit():
                    msvcrt.getch()
                    break
            else:
                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    break
            
            page.wait_for_timeout(300)
            
            try:
                current_url = page.url
                
                if current_url != last_url:
                    print(f"\n  ✓ Detected navigation to: {current_url}")
                    self.visited_urls.discard(current_url)
                    page.wait_for_timeout(1000)
                    print(f"  → Extracting elements from new page...")
                    self._extract_all_elements(page)
                    last_url = current_url
                    page.evaluate("window.__changeDetected = false;")
                
                elif page.evaluate("window.__changeDetected"):
                    print(f"\n  ✓ Detected DOM changes")
                    page.wait_for_timeout(300)
                    print(f"  → Extracting new elements...")
                    self._extract_all_elements(page)
                    page.evaluate("window.__changeDetected = false;")
                    
            except Exception as e:
                print(f"  ✗ Monitor error: {str(e)[:50]}")
        
        print("\n  ✓ Monitoring stopped.")
        print("  ✓ All interactions captured!\n")
    
    def _attempt_auto_login(self, page: Page) -> bool:
        """Attempt to auto-login by detecting and filling login form (LEGACY - direct fill)"""
        try:
            print("\n  → Attempting auto-login...")
            
            # Find email/username input
            email_filled = False
            inputs = page.locator('input').all()
            for inp in inputs:
                try:
                    if inp.is_visible():
                        input_type = (inp.get_attribute('type') or '').lower()
                        input_name = (inp.get_attribute('name') or '').lower()
                        input_placeholder = (inp.get_attribute('placeholder') or '').lower()
                        
                        if 'email' in input_type or 'email' in input_name or 'email' in input_placeholder or \
                           'user' in input_name or 'user' in input_placeholder:
                            inp.fill(self.username)
                            print(f"  → Filled email/username")
                            email_filled = True
                            break
                except:
                    continue
            
            if not email_filled:
                return False
            
            # Find password input
            password_filled = False
            pass_inputs = page.locator('input[type="password"]').all()
            for inp in pass_inputs:
                try:
                    if inp.is_visible():
                        inp.fill(self.password)
                        print(f"  → Filled password")
                        password_filled = True
                        break
                except:
                    continue
            
            if not password_filled:
                return False
            
            # Find and click login button
            buttons = page.locator('button').all()
            for btn in buttons:
                try:
                    if btn.is_visible():
                        text = (btn.text_content() or '').lower()
                        if ('login' in text or 'sign in' in text) and 'sign up' not in text:
                            btn.click()
                            print(f"  → Clicked login button")
                            page.wait_for_timeout(3000)
                            return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def _attempt_auto_click_login(self, page: Page) -> bool:
        """Auto-login by CLICKING inputs and buttons (captures ALL validation errors)"""
        try:
            print("\n  → Attempting auto-login with validation testing...")
            
            # Get all visible inputs
            all_inputs = []
            inputs = page.locator('input').all()
            for inp in inputs:
                try:
                    if inp.is_visible():
                        input_type = (inp.get_attribute('type') or '').lower()
                        input_name = (inp.get_attribute('name') or '').lower()
                        input_placeholder = (inp.get_attribute('placeholder') or '').lower()
                        all_inputs.append({
                            'element': inp,
                            'type': input_type,
                            'name': input_name,
                            'placeholder': input_placeholder
                        })
                except:
                    continue
            
            # Test each input with invalid data to trigger validation
            print(f"  → Testing {len(all_inputs)} inputs for validation errors...")
            for inp_data in all_inputs:
                inp = inp_data['element']
                try:
                    inp.click()
                    page.wait_for_timeout(300)
                    self._extract_all_elements(page)
                    
                    # Test with various invalid inputs
                    if inp_data['type'] == 'email' or 'email' in inp_data['name'] or 'email' in inp_data['placeholder']:
                        inp.type('invalid', delay=30)
                        page.wait_for_timeout(500)
                        self._extract_all_elements(page)
                        inp.fill('')
                    elif inp_data['type'] == 'password' or 'password' in inp_data['name']:
                        inp.type('123', delay=30)
                        page.wait_for_timeout(500)
                        self._extract_all_elements(page)
                        inp.fill('')
                    else:
                        inp.type('test', delay=30)
                        page.wait_for_timeout(500)
                        self._extract_all_elements(page)
                        inp.fill('')
                except:
                    continue
            
            # Fill form with invalid credentials and submit
            print(f"  → Testing form submission with invalid data...")
            for inp_data in all_inputs:
                inp = inp_data['element']
                try:
                    if 'email' in inp_data['type'] or 'email' in inp_data['name'] or 'email' in inp_data['placeholder'] or 'user' in inp_data['name']:
                        inp.fill('nonexistent@invalid.test')
                    elif inp_data['type'] == 'password':
                        inp.fill('wrongpassword123')
                except:
                    continue
            
            # Submit form to trigger server-side errors
            buttons = page.locator('button').all()
            for btn in buttons:
                try:
                    if btn.is_visible():
                        text = (btn.text_content() or '').lower()
                        if any(pattern.strip().lower() in text for pattern in self.login_button_texts) and 'sign up' not in text:
                            btn.click()
                            print(f"  → Submitted with invalid data...")
                            page.wait_for_timeout(2000)
                            self._extract_all_elements(page)
                            page.wait_for_timeout(1000)
                            self._extract_all_elements(page)
                            break
                except:
                    continue
            
            # Now fill with valid credentials
            print(f"  → Filling valid credentials...")
            for inp_data in all_inputs:
                inp = inp_data['element']
                try:
                    if 'email' in inp_data['type'] or 'email' in inp_data['name'] or 'email' in inp_data['placeholder'] or 'user' in inp_data['name']:
                        inp.fill(self.username)
                    elif inp_data['type'] == 'password':
                        inp.fill(self.password)
                except:
                    continue
            
            # Submit with valid credentials
            for btn in buttons:
                try:
                    if btn.is_visible():
                        text = (btn.text_content() or '').lower()
                        if any(pattern.strip().lower() in text for pattern in self.login_button_texts) and 'sign up' not in text:
                            btn.click()
                            print(f"  → Logging in with valid credentials...")
                            page.wait_for_timeout(3000)
                            self._extract_all_elements(page)
                            return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def _click_element(self, page: Page, elem: dict) -> bool:
        """Click element using multiple strategies"""
        try:
            if elem.get('id'):
                page.locator(f"#{elem['id']}").first.click(timeout=3000)
                return True
        except:
            pass
        
        try:
            if elem['text']:
                page.get_by_text(elem['text'][:30], exact=False).first.click(timeout=3000)
                return True
        except:
            pass
        
        try:
            return page.evaluate("""
                (idx) => {
                    const all = Array.from(document.querySelectorAll('*'));
                    const visible = all.filter(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    });
                    
                    const interactive = visible.filter(el => {
                        const tag = el.tagName.toLowerCase();
                        const role = el.getAttribute('role') || '';
                        return ['button','a','input','select','textarea','img'].includes(tag) ||
                               ['button','link','menuitem'].includes(role);
                    });
                    
                    if (idx < interactive.length) {
                        const el = interactive[idx];
                        el.scrollIntoView({block: 'center'});
                        el.click();
                        return true;
                    }
                    return false;
                }
            """, elem['idx'])
        except:
            return False
    
    def _extract_all_elements(self, page: Page):
        """Extract ALL elements including images, buttons, inputs, links, dynamic popups"""
        try:
            elements = page.evaluate("""
                () => {
                    const all = Array.from(document.querySelectorAll('*'));
                    const visible = all.filter(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && style.display !== 'none';
                    });
                    
                    const extractable = visible.filter(el => {
                        const tag = el.tagName.toLowerCase();
                        const role = el.getAttribute('role') || '';
                        const classes = (el.className || '').toString().toLowerCase();
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        const title = el.title || '';
                        const style = window.getComputedStyle(el);
                        const isPointer = style.cursor === 'pointer';
                        
                        // Error/validation message indicators (expanded)
                        const isError = classes.includes('error') || classes.includes('invalid') || 
                                       classes.includes('alert') || classes.includes('warning') ||
                                       classes.includes('message') || classes.includes('validation') ||
                                       classes.includes('help') || classes.includes('hint') ||
                                       classes.includes('feedback') || classes.includes('tooltip') ||
                                       role === 'alert' || role === 'status' || role === 'tooltip';
                        
                        // Check for own text (text directly in element, not children)
                        const childText = Array.from(el.children).map(c => c.textContent).join('');
                        const fullText = el.textContent || '';
                        const ownText = fullText.replace(childText, '').trim();
                        const hasOwnText = ownText.length > 0 && ownText.length < 500;
                        
                        // Check for error-like text content
                        const errorKeywords = ['required', 'invalid', 'error', 'must', 'cannot', 'failed', 
                                              'incorrect', 'wrong', 'missing', 'match', 'contain', 'exist',
                                              'uppercase', 'lowercase', 'numeric', 'symbol', 'character'];
                        const hasErrorText = errorKeywords.some(keyword => ownText.toLowerCase().includes(keyword));
                        
                        const textTags = ['h1','h2','h3','h4','h5','h6','p','label','span','div','b','strong','i','em','small','li','td','th','ul'];
                        
                        return ['button','input','select','textarea','a','img','form','svg','path'].includes(tag) ||
                               ['button','combobox','option','menuitem','alert','dialog','tooltip'].includes(role) ||
                               el.onclick || el.hasAttribute('onclick') || isPointer || ariaLabel || title || isError ||
                               (textTags.includes(tag) && hasOwnText) ||
                               (hasOwnText && hasErrorText);
                    });
                    
                    return extractable.map(el => {
                        // Extract pseudo-element content (::before, ::after)
                        const beforeContent = window.getComputedStyle(el, '::before').content;
                        const afterContent = window.getComputedStyle(el, '::after').content;
                        const pseudoText = [
                            beforeContent !== 'none' && beforeContent !== '' ? beforeContent.replace(/["']/g, '') : '',
                            afterContent !== 'none' && afterContent !== '' ? afterContent.replace(/["']/g, '') : ''
                        ].filter(t => t).join(' ');
                        
                        const mainText = (el.innerText || el.textContent || '').trim();
                        const fullText = [mainText, pseudoText].filter(t => t).join(' ');
                        
                        return {
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            name: el.name || null,
                            testId: el.getAttribute('data-testid') || null,
                            ariaLabel: el.getAttribute('aria-label') || null,
                            role: el.getAttribute('role') || null,
                            text: fullText,
                            type: el.type || null,
                            placeholder: el.placeholder || null,
                            alt: el.alt || null,
                            src: el.src || null,
                            href: el.href || null,
                            className: el.className ? el.className.toString() : null,
                            title: el.title || null,
                            validationMessage: el.validationMessage || null
                        };
                    })
                }
            """)
            
            url = page.url
            count = 0
            for elem in elements:
                if self._save_element(elem, url):
                    count += 1
            
            if count > 0:
                print(f"  ✓ Extracted {count} new elements")
                
        except Exception as e:
            print(f"  ✗ Extraction error: {str(e)[:50]}")
    
    def _save_fallback_to_file(self):
        """Save fallback data to JSON file"""
        try:
            filepath = os.path.join(os.path.dirname(__file__), '..', self.fallback_file)
            with open(filepath, 'w') as f:
                json.dump(self.fallback_data, f, indent=2)
            print(f"\n  ⚠ Fallback data saved to: {self.fallback_file}")
            print(f"  ⚠ Import later with: python import_fallback.py {self.fallback_file}")
        except Exception as e:
            print(f"  ✗ Failed to save fallback: {e}")
    
    def _calculate_stability_score(self, elem: dict) -> int:
        """Calculate stability score based on locator reliability"""
        if elem.get('testId'):
            return 100  # Best: explicitly for testing
        if elem.get('id'):
            return 90   # Excellent: unique identifier
        if elem.get('name'):
            return 80   # Good: form element name
        if elem.get('ariaLabel'):
            return 80   # Good: accessibility label
        if elem.get('placeholder'):
            return 75   # Decent: static prompt text
        if elem.get('text'):
            return 70   # Okay: visible text
        if elem.get('alt'):
            return 65   # Fail-safe: image alt text
        if elem.get('role'):
            return 50   # Low: generic role
        return 30       # Poor: generic tag-based

    def _save_element(self, elem, url) -> bool:
        """Save element to API with fallback to JSON"""
        try:
            # API connection is checked during the first request attempt below
            # Build CSS selector
            if elem['testId']:
                css = f"[data-testid='{elem['testId']}']"
                xpath = f"//*[@data-testid='{elem['testId']}']"
            elif elem['id']:
                css = f"#{elem['id']}"
                xpath = f"//*[@id='{elem['id']}']"
            elif elem['name']:
                css = f"[name='{elem['name']}']"
                xpath = f"//*[@name='{elem['name']}']"
            elif elem['placeholder']:
                css = f"[placeholder='{elem['placeholder']}']"
                xpath = f"//*[@placeholder='{elem['placeholder']}']"
            elif elem['ariaLabel']:
                css = f"[aria-label='{elem['ariaLabel']}']"
                xpath = f"//*[@aria-label='{elem['ariaLabel']}']"
            elif elem['text'] and len(elem['text']) > 0:
                text = elem['text'].replace("'", "\\'")[:30]
                css = f"{elem['tag']}:has-text('{text}')"
                xpath = f"//{elem['tag']}[contains(text(), '{text}')]"
            elif elem['alt']:
                css = f"[alt='{elem['alt']}']"
                xpath = f"//*[@alt='{elem['alt']}']"
            elif elem['role']:
                css = f"[role='{elem['role']}']"
                xpath = f"//*[@role='{elem['role']}']"
            else:
                css = elem['tag']
                xpath = f"//{elem['tag']}"
            
            # Element name
            name_parts = []
            if elem['text']:
                clean = re.sub(r'[^a-zA-Z0-9]', '_', elem['text'].lower())[:50]
                if clean:
                    name_parts.append(clean)
            elif elem['placeholder']:
                clean = re.sub(r'[^a-zA-Z0-9]', '_', elem['placeholder'].lower())[:50]
                if clean:
                    name_parts.append(clean)
            elif elem['alt']:
                clean = re.sub(r'[^a-zA-Z0-9]', '_', elem['alt'].lower())[:50]
                if clean:
                    name_parts.append(clean)
            
            name_parts.append(elem['tag'])
            element_name = '_'.join(name_parts) if name_parts else elem['tag']
            
            # Screen name from URL
            clean_url = url.split('?')[0].split('#')[0]
            path = clean_url.replace(self.base_url, '').strip('/')
            screen_name = path.split('/')[-1] if path else 'home'
            screen_name = re.sub(r'[^a-zA-Z0-9_-]', '_', screen_name) or 'home'
            
            # Get screen_id from cache or create
            screen_id = self.screen_cache.get(clean_url)
            if not screen_id:
                screen_resp = requests.post(f"{self.api_url}/screens", json={
                    "name": screen_name,
                    "url": clean_url,
                    "title": screen_name,
                    "session_id": self.session_id
                }, timeout=5)
                if screen_resp.status_code in [200, 201]:
                    screen_id = screen_resp.json().get('id')
                    self.screen_cache[clean_url] = screen_id
            
            # Prepare element data
            text_content = elem['text'] if elem['text'] else None
            if elem.get('validationMessage') and elem['validationMessage']:
                text_content = f"{text_content} [Validation: {elem['validationMessage']}]" if text_content else f"[Validation: {elem['validationMessage']}]"
            
            # Avoid duplicates (but allow re-extraction if text_content changed)
            text_for_sig = text_content if text_content else elem.get('text', '')[:100]
            sig = f"{elem['tag']}:{elem.get('id') or elem.get('name')}:{text_for_sig}:{url}"
            if sig in self.extracted_elements:
                return False
            self.extracted_elements.add(sig)
            
            element_data = {
                "screen_url": clean_url,
                "screen_name": screen_name,
                "element_name": element_name,
                "element_type": elem['tag'],
                "element_id": elem['id'],
                "element_name_attr": elem['name'],
                "data_testid": elem['testId'],
                "aria_label": elem['ariaLabel'],
                "role": elem['role'],
                "css_selector": css,
                "xpath": xpath,
                "text_content": text_content,
                "stability_score": self._calculate_stability_score(elem),
                "verified": True
            }
            
            # Try API first
            if self.api_available and screen_id:
                try:
                    resp = requests.post(f"{self.api_url}/add-locator", json={
                        "screen_id": screen_id,
                        **element_data
                    }, timeout=5)
                    
                    if resp.status_code in [200, 201]:
                        return True
                    else:
                        self.api_available = False
                        print(f"  ⚠ API error - switching to fallback")
                except:
                    self.api_available = False
                    print(f"  ⚠ API failed - switching to fallback")
            
            # Fallback to JSON
            if clean_url not in self.fallback_data['screens']:
                self.fallback_data['screens'][clean_url] = {
                    "name": screen_name,
                    "url": clean_url,
                    "session_id": self.session_id
                }
            
            self.fallback_data['elements'].append(element_data)
            return True
            
        except Exception as e:
            print(f"  ✗ Save error: {str(e)[:50]}")
            return False
