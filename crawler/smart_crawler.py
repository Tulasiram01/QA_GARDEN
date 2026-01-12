from playwright.sync_api import Page, Browser, TimeoutError as PlaywrightTimeoutError
import requests
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SmartCrawler:
    def __init__(self, base_url, username, password, api_url, skip_patterns=None, **kwargs):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_url = api_url
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.clicked_per_url = {}
        self.extracted = set()
        self.screens = {}
        self.visited_urls = set()
        self.skip_patterns = skip_patterns or ['logout', 'sign out', 'log out', 'delete', 'remove']
        
    def crawl(self, browser: Browser):
        page = browser.new_page()
        try:
            page.goto(self.base_url, timeout=30000, wait_until="domcontentloaded")
            logger.info(f"\n{'='*60}\nSession: {self.session_id}\n{'='*60}\n")
            
            if self._is_login_page(page):
                if self._auto_login(page):
                    logger.info("✓ Login\n")
                else:
                    return {"error": "Login failed or 2FA required"}
            
            self._explore_screen(page, 0)
            
            logger.info(f"\n{'='*60}\nDone! Elements: {len(self.extracted)}\n{'='*60}\n")
            return {
                "session_id": self.session_id,
                "screens_discovered": len(self.screens),
                "total_elements": len(self.extracted)
            }
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            return {"error": str(e)}
        finally:
            page.close()
    
    def _explore_screen(self, page: Page, depth: int):
        if depth > 5:
            return
        
        url = page.url.split('?')[0].split('#')[0]
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        self.clicked_per_url[url] = set()
        
        logger.info(f"{'  '*depth}→ {url}")
        page.wait_for_timeout(500)
        
        extracted_count = self._extract_all_elements(page)
        logger.info(f"{'  '*depth}  Extracted {extracted_count} elements")
        
        self._interact_with_elements(page, depth, url)
    
    def _interact_with_elements(self, page: Page, depth: int, original_url: str):
        selectors = ['button', 'a', 'input', 'select', 'textarea', 'div[onclick]', 'div[role]', '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]', '[role="combobox"]', '[role="option"]', '[onclick]', '[class*="btn"]', '[class*="avatar"]', '[class*="profile"]', '[class*="dropdown"]', '[class*="menu"]']
        
        all_elements = []
        for sel in selectors:
            try:
                all_elements.extend(page.query_selector_all(sel))
            except:
                pass
        
        if not all_elements:
            logger.info(f"{'  '*depth}✓ No elements to interact")
            return
        
        sorted_elements = []
        for element in all_elements:
            try:
                if element.is_visible():
                    box = element.bounding_box()
                    if box:
                        sorted_elements.append((box['y'], box['x'], element))
            except:
                pass
        
        sorted_elements.sort(key=lambda x: (x[0], x[1]))
        
        for _, _, element in sorted_elements:
            try:
                if not element.is_visible():
                    continue
                
                tag = element.evaluate("el => el.tagName.toLowerCase()")
                text = element.text_content()[:50] if element.text_content() else ""
                elem_id = element.get_attribute('id') or ""
                
                key = f"{tag}::{elem_id}::{text[:20]}"
                
                if key in self.clicked_per_url[original_url]:
                    continue
                
                if any(p in text.lower() for p in self.skip_patterns):
                    continue
                
                logger.info(f"{'  '*depth}  [{tag}] {text}")
                element.scroll_into_view_if_needed()
                element.click(timeout=2000)
                page.wait_for_timeout(1500)
                
                self.clicked_per_url[original_url].add(key)
                
                # Extract newly revealed elements
                new_count = self._extract_all_elements(page)
                if new_count > 0:
                    logger.info(f"{'  '*depth}    +{new_count} new elements")
                
                # Check if navigated to new page
                new_url = page.url.split('?')[0].split('#')[0]
                if new_url != original_url and new_url not in self.visited_urls:
                    logger.info(f"{'  '*depth}  → Navigated to {new_url}")
                    self._explore_screen(page, depth + 1)
                    
                    page.goto(original_url, wait_until="domcontentloaded")
                    page.wait_for_timeout(500)
                    
            except Exception as e:
                logger.debug(f"Click failed: {e}")
                continue
        
        logger.info(f"{'  '*depth}✓ All elements processed")
    
    def _get_parent_label(self, element):
        try:
            label = element.evaluate("el => el.closest('label')?.textContent || el.closest('[role=\"group\"]')?.textContent || el.closest('.form-group')?.textContent || el.closest('[class*=\"field\"]')?.textContent || ''")
            return label.strip() if label else ""
        except:
            return ""
    
    def _extract_all_elements(self, page: Page) -> int:
        count = 0
        selectors = ['button', 'a', 'input', 'select', 'textarea', 'div[onclick]', 'div[role]', '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]', '[role="combobox"]', '[role="option"]', '[onclick]', '[class*="btn"]', '[class*="avatar"]', '[class*="profile"]', '[class*="dropdown"]', '[class*="menu"]', '[class*="nav"]', '[data-testid]', '[aria-label]']
        
        all_elements = []
        for sel in selectors:
            try:
                all_elements.extend(page.query_selector_all(sel))
            except:
                pass
        
        logger.info(f"Found {len(all_elements)} total elements")
        
        for element in all_elements:
            try:
                if not element.is_visible():
                    continue
                
                tag = element.evaluate("el => el.tagName.toLowerCase()")
                text = (element.text_content() or "").strip()[:100]
                elem_id = element.get_attribute('id') or ""
                aria_label = element.get_attribute('aria-label') or ""
                data_testid = element.get_attribute('data-testid') or ""
                role = element.get_attribute('role') or ""
                placeholder = element.get_attribute('placeholder') or ""
                
                if not text and not elem_id and not aria_label and not data_testid and not placeholder:
                    continue
                
                sig = f"{tag}::{elem_id}::{text[:20]}::{aria_label[:20]}"
                if sig in self.extracted:
                    continue
                
                self.extracted.add(sig)
                
                screen_id = self._get_or_create_screen(page.url)
                if not screen_id:
                    continue
                
                if role == 'combobox' and not text:
                    parent_label = self._get_parent_label(element)
                    if parent_label:
                        text = parent_label[:100]
                
                if text and text.strip():
                    display_name = text
                elif aria_label and aria_label.strip():
                    display_name = aria_label
                elif placeholder and placeholder.strip():
                    display_name = placeholder
                elif data_testid and data_testid.strip():
                    display_name = data_testid
                else:
                    display_name = f"{tag}_element"
                
                display_name = display_name.replace(' ', '_').replace('\n', '_').lower()[:100]
                
                if elem_id:
                    css_selector = f"#{elem_id}"
                    xpath = f"//*[@id='{elem_id}']"
                elif data_testid:
                    css_selector = f"[data-testid='{data_testid}']"
                    xpath = f"//*[@data-testid='{data_testid}']"
                elif aria_label:
                    css_selector = f"[aria-label='{aria_label}']"
                    xpath = f"//*[@aria-label='{aria_label}']"
                elif text and text.strip():
                    css_selector = f"{tag}:has-text('{text}')"
                    xpath = f"//{tag}[contains(text(), '{text}')]"
                else:
                    css_selector = tag
                    xpath = f"//{tag}"
                
                data = {
                    "screen_id": screen_id,
                    "element_name": display_name,
                    "element_type": tag,
                    "css_selector": css_selector,
                    "xpath": xpath,
                    "text_content": text if text else None,
                    "verified": True
                }
                
                if elem_id:
                    data['element_id'] = elem_id
                if data_testid:
                    data['data_testid'] = data_testid
                if aria_label:
                    data['aria_label'] = aria_label
                if role:
                    data['role'] = role
                
                try:
                    resp = requests.post(f"{self.api_url}/add-locator", json=data, timeout=5)
                    if resp.status_code in [200, 201]:
                        count += 1
                except Exception as e:
                    logger.debug(f"API save failed: {e}")
                    
            except Exception as e:
                logger.debug(f"Element extraction failed: {e}")
                continue
        
        return count
    
    def _get_or_create_screen(self, url: str):
        clean_url = url.split('?')[0].split('#')[0]
        
        if clean_url in self.screens:
            return self.screens[clean_url]
        
        path = clean_url.replace(self.base_url, '').strip('/')
        screen_name = path.split('/')[-1] if path else 'home'
        
        try:
            resp = requests.post(f"{self.api_url}/screens", json={
                "name": screen_name,
                "url": clean_url,
                "title": screen_name,
                "session_id": self.session_id
            }, timeout=5)
            
            if resp.status_code in [200, 201]:
                screen_id = resp.json().get('id')
                self.screens[clean_url] = screen_id
                return screen_id
        except Exception as e:
            logger.debug(f"Screen creation failed: {e}")
        
        return None
    
    def _is_login_page(self, page: Page):
        try:
            return 'login' in page.url.lower() or page.query_selector('input[type="password"]') is not None
        except:
            return False
    
    def _auto_login(self, page: Page):
        try:
            page.wait_for_timeout(2000)
            
            email_input = page.query_selector('input[type="email"]')
            if not email_input:
                email_input = page.query_selector('input[name="email"]')
            if not email_input:
                email_input = page.query_selector('input')
            
            if email_input:
                email_input.fill(self.username)
                page.wait_for_timeout(1000)
            
            password_input = page.query_selector('input[type="password"]')
            if password_input:
                password_input.fill(self.password)
                page.wait_for_timeout(1000)
            else:
                logger.error("Password input not found")
                return False
            
            submit_btn = page.query_selector('button[type="submit"]')
            if not submit_btn:
                submit_btn = page.query_selector('button')
            
            if submit_btn:
                try:
                    submit_btn.wait_for_element_state("enabled", timeout=5000)
                except:
                    pass
                
                try:
                    with page.expect_navigation(timeout=15000):
                        submit_btn.click(timeout=5000)
                except:
                    try:
                        submit_btn.click(timeout=5000)
                    except:
                        password_input.press('Enter')
            else:
                password_input.press('Enter')
            
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=8000)
                except:
                    pass
            
            page.wait_for_timeout(2000)
            
            if 'two_step_verification' in page.url or 'checkpoint' in page.url:
                logger.warning("2FA verification required - cannot proceed")
                return False
            
            is_logged_in = 'login' not in page.url.lower()
            logger.info(f"Login result: {is_logged_in}, URL: {page.url}")
            return is_logged_in
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
