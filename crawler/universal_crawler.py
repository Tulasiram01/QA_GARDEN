from playwright.sync_api import Page, Browser
import requests
from datetime import datetime
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class UniversalCrawler:
    def __init__(self, base_url, username, password, api_url, **kwargs):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_url = api_url
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.visited_urls = set()
        self.extracted_elements = {}
        self.screens = {}
        self.global_clicked = set()
        
    def crawl(self, browser: Browser):
        page = browser.new_page()
        try:
            logger.info(f"\n{'='*60}\nSession: {self.session_id}\n{'='*60}\n")
            
            self._safe_navigate(page, self.base_url)
            self._handle_authentication(page)
            self._explore(page, 0)
            
            total = sum(len(v) for v in self.extracted_elements.values())
            logger.info(f"\n{'='*60}\nCrawl Complete!\nScreens: {len(self.screens)}\nElements: {total}\n{'='*60}\n")
            
            return {
                "session_id": self.session_id,
                "screens_discovered": len(self.screens),
                "total_elements": total
            }
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            return {"error": str(e)}
        finally:
            page.close()
    
    def _handle_authentication(self, page: Page):
        try:
            page.wait_for_timeout(500)
            if any(x in page.url.lower() for x in ['login', 'signin', 'auth']):
                inputs = page.query_selector_all('input')
                for inp in inputs:
                    try:
                        if inp.get_attribute('type') in ['email', 'text', None]:
                            inp.fill(self.username)
                            break
                    except:
                        pass
                
                for inp in inputs:
                    try:
                        if inp.get_attribute('type') == 'password':
                            inp.fill(self.password)
                            break
                    except:
                        pass
                
                page.wait_for_timeout(300)
                for btn in page.query_selector_all('button'):
                    try:
                        if btn.is_visible():
                            btn.click(timeout=3000)
                            page.wait_for_timeout(2000)
                            break
                    except:
                        pass
        except Exception as e:
            logger.debug(f"Auth: {e}")
    
    def _explore(self, page: Page, depth: int):
        if depth > 15:
            return
        
        url = page.url
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        logger.info(f"{'  '*depth}→ {url}")
        
        page.wait_for_timeout(500)
        
        screen_id = self._get_screen(page)
        if screen_id:
            extracted = self._extract(page, screen_id)
            logger.info(f"{'  '*depth}  ✓ {extracted} elements")
        
        self._interact(page, depth, url)
    
    def _extract(self, page: Page, screen_id: int) -> int:
        try:
            count = 0
            seen = set()
            
            for elem in page.query_selector_all('*'):
                try:
                    if not elem.is_visible():
                        continue
                    
                    tag = elem.evaluate("el => el.tagName.toLowerCase()")
                    text = (elem.text_content() or "").strip()[:500]
                    elem_id = elem.get_attribute('id') or ""
                    href = elem.get_attribute('href') or ""
                    
                    if not text and not elem_id and not href:
                        continue
                    
                    sig = f"{tag}:{elem_id}:{text}:{href}"
                    if sig in seen:
                        continue
                    seen.add(sig)
                    
                    name = text or elem_id or tag
                    name = name.replace(' ', '_').replace('\n', '_').lower()[:500]
                    
                    if elem_id:
                        css = f"#{elem_id}"
                        xpath = f"//*[@id='{elem_id}']"
                    elif href:
                        css = f"a[href='{href}']"
                        xpath = f"//a[@href='{href}']"
                    elif text:
                        css = f"{tag}:has-text('{text}')"
                        xpath = f"//{tag}[contains(text(), '{text}')]"
                    else:
                        css = tag
                        xpath = f"//{tag}"
                    
                    data = {
                        "screen_id": screen_id,
                        "element_name": name,
                        "element_type": tag,
                        "css_selector": css,
                        "xpath": xpath,
                        "verified": True
                    }
                    
                    if text:
                        data['text_content'] = text
                    if elem_id:
                        data['element_id'] = elem_id
                    
                    try:
                        resp = requests.post(f"{self.api_url}/add-locator", json=data, timeout=5)
                        if resp.status_code in [200, 201]:
                            if screen_id not in self.extracted_elements:
                                self.extracted_elements[screen_id] = set()
                            self.extracted_elements[screen_id].add(sig)
                            count += 1
                    except:
                        pass
                except:
                    pass
            
            return count
        except:
            return 0
    
    def _interact(self, page: Page, depth: int, url: str):
        try:
            skip = ['logout', 'delete', 'remove', 'unsubscribe', 'sign out']
            
            elems = page.query_selector_all('*')
            for idx in range(len(elems)):
                try:
                    current_elems = page.query_selector_all('*')
                    if idx >= len(current_elems):
                        continue
                    
                    elem = current_elems[idx]
                    if not elem.is_visible():
                        continue
                    
                    tag = elem.evaluate('el => el.tagName.toLowerCase()')
                    is_clickable = tag in ['a', 'button', 'input', 'select', 'textarea', 'label'] or \
                                   elem.evaluate('el => el.getAttribute("role")') in ['button', 'link', 'tab', 'menuitem'] or \
                                   elem.evaluate('el => el.onclick !== null')
                    
                    if not is_clickable:
                        continue
                    
                    text = (elem.text_content() or "").strip()[:50].lower()
                    if any(x in text for x in skip):
                        continue
                    
                    sig = f"{url}:{idx}:{tag}"
                    if sig in self.global_clicked:
                        continue
                    
                    self.global_clicked.add(sig)
                    
                    display_text = text[:30] if text else tag
                    logger.info(f"{'  '*depth}  → {display_text}")
                    
                    elem.scroll_into_view_if_needed()
                    page.wait_for_timeout(100)
                    
                    try:
                        with page.expect_navigation(timeout=2000):
                            elem.click(timeout=1500)
                    except:
                        try:
                            elem.click(timeout=1500)
                        except:
                            continue
                    
                    page.wait_for_timeout(800)
                    
                    new_url = page.url
                    if new_url != url and new_url not in self.visited_urls:
                        logger.info(f"{'  '*depth}  ✓ New: {new_url}")
                        self._explore(page, depth + 1)
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=8000)
                            page.wait_for_timeout(500)
                        except:
                            return
                except:
                    pass
        except:
            pass
    
    def _get_screen(self, page: Page) -> Optional[int]:
        try:
            url = page.url
            if url in self.screens:
                return self.screens[url]
            
            path = url.replace(self.base_url, '').strip('/')
            name = path.split('/')[-1] if path else 'home'
            name = name.split('?')[0].split('#')[0] or 'home'
            
            resp = requests.post(f"{self.api_url}/screens", json={
                "name": name,
                "url": url,
                "title": name,
                "session_id": self.session_id
            }, timeout=5)
            
            if resp.status_code in [200, 201]:
                sid = resp.json().get('id')
                self.screens[url] = sid
                return sid
            return None
        except:
            return None
    
    def _safe_navigate(self, page: Page, url: str):
        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise
