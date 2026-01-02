from playwright.sync_api import Page, Browser
import requests
from datetime import datetime

class SmartCrawler:
    def __init__(self, base_url, username, password, api_url, skip_patterns=None, framework_patterns=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_url = api_url
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.clicked = {}
        self.extracted = set()
        self.screens = {}
        self.visited_urls = set()
        
        self.skip_patterns = skip_patterns or ['logout', 'sign out', 'log out', 'sign-out']
        self.framework_patterns = framework_patterns or ['react-select', 'rc_select', 'rc-select']
        
    def crawl(self, browser: Browser):
        page = browser.new_page()
        page.goto(self.base_url)
        page.wait_for_load_state("networkidle")
        
        print(f"\n{'='*60}")
        print(f"Session: {self.session_id}")
        print(f"{'='*60}\n")
        
        if self._is_login_page(page):
            if self._auto_login(page):
                print("✓ Login\n")
            else:
                return {"error": "Login failed"}
        
        self._explore_screen(page, 0, 10)
        
        print(f"\n{'='*60}")
        print(f"Done! Elements: {len(self.extracted)}")
        print(f"{'='*60}\n")
        
        return {
            "session_id": self.session_id,
            "screens_discovered": len(self.screens),
            "total_elements": len(self.extracted),
            "total_clicked": len(self.clicked)
        }
    
    def _get_element_id(self, elem_info):
        return elem_info.get('id') or elem_info.get('name') or elem_info.get('aria_label') or f"{elem_info.get('tag')}_{elem_info.get('text', '')[:20]}"
    
    def _explore_screen(self, page: Page, depth: int, max_depth: int):
        if depth > max_depth:
            return
        
        url = page.url.split('?')[0].split('#')[0]
        
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)
        
        print(f"{'  '*depth}→ {url}")
        
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        self._extract_all_elements(page)
        
        count = 0
        while True:
            inputs = page.locator('input:visible:not([type="hidden"]), textarea:visible, select:visible').all()
            inputs = [inp for inp in inputs if not self._is_framework_hidden_input_strict(inp)]
            
            print(f"{'  '*depth}  Found {len(inputs)} inputs")
            
            input_count = 0
            for locator in inputs:
                try:
                    if not locator.is_visible():
                        continue
                    
                    elem_info = locator.evaluate("""
                        el => ({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            name: el.name || null,
                            text: (el.innerText || '').trim().substring(0, 50),
                            type: el.type || null,
                            aria_label: el.getAttribute('aria-label') || null
                        })
                    """)
                    
                    elem_id = self._get_element_id(elem_info)
                    if elem_id in self.clicked:
                        continue
                    
                    if self._interact_with_locator(page, locator, elem_info, depth):
                        self.clicked[elem_id] = True
                        input_count += 1
                        count += 1
                except:
                    continue
            
            if input_count == 0:
                break
            
            page.wait_for_timeout(500)
        
        buttons = page.locator('button:visible, a:visible, [role="button"]:visible, [role="link"]:visible, div[style*="cursor"]:visible, span[aria-label]:visible, li[role]:visible').all()
        
        print(f"{'  '*depth}  Found {len(buttons)} buttons")
        
        for locator in buttons:
            try:
                if not locator.is_visible():
                    continue
                
                is_disabled = locator.evaluate('el => el.disabled || el.getAttribute("aria-disabled") === "true" || el.style.opacity === "0.5"')
                if is_disabled:
                    continue
                
                elem_info = locator.evaluate("""
                    el => ({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        name: el.name || null,
                        text: (el.innerText || '').trim().substring(0, 50),
                        type: el.type || null,
                        aria_label: el.getAttribute('aria-label') || null
                    })
                """)
                
                elem_id = self._get_element_id(elem_info)
                if elem_id in self.clicked:
                    continue
                
                text = elem_info.get('text', '').lower()
                if self._should_skip_element(text):
                    continue
                
                saved_url = page.url
                
                if self._interact_with_locator(page, locator, elem_info, depth):
                    self.clicked[elem_id] = True
                    count += 1
                    
                    if page.url != saved_url:
                        print(f"{'  '*depth}  → Navigated to {page.url}")
                        self._explore_screen(page, depth + 1, max_depth)
                        try:
                            page.goto(saved_url)
                            page.wait_for_load_state("networkidle")
                        except:
                            break
                    else:
                        page.wait_for_timeout(500)
            except:
                continue
        
        print(f"{'  '*depth}  ✓ {count} interactions")
    
    def _interact_with_locator(self, page: Page, locator, elem_info: dict, depth: int):
        tag = elem_info.get('tag')
        text = elem_info.get('text', '')[:30]
        elem_id = elem_info.get('id', '')
        
        if self._is_framework_select(elem_id):
            label = self._get_framework_select_label(page, elem_id)
            name = label or text or elem_id or 'element'
        else:
            name = text or elem_id or 'element'
        
        try:
            print(f"{'  '*depth}  [{tag}] {name}")
            
            if tag == 'select':
                return self._handle_select_locator(page, locator, depth)
            elif tag in ['input', 'textarea']:
                return self._handle_input_locator(page, locator, elem_info, depth)
            elif tag in ['button', 'a', 'div', 'span', 'li'] or elem_info.get('role') in ['button', 'link', 'menuitem']:
                return self._handle_click_locator(page, locator, depth)
            
            return False
        except Exception as e:
            print(f"{'  '*depth}    ✗ {str(e)[:50]}")
            return False
    
    def _handle_select_locator(self, page: Page, locator, depth: int):
        try:
            options = locator.locator('option').all()
            print(f"{'  '*depth}    Found {len(options)} options")
            
            for opt in options:
                opt_text = opt.inner_text()
                if opt_text:
                    self._save_option(opt_text, page.url)
            
            if len(options) > 1:
                locator.select_option(index=1, timeout=3000)
                page.wait_for_timeout(500)
            
            self._extract_all_elements(page)
            return True
        except Exception as e:
            print(f"{'  '*depth}    ✗ Select: {str(e)[:30]}")
            return False
    
    def _handle_input_locator(self, page: Page, locator, elem_info: dict, depth: int):
        try:
            itype = elem_info.get('type', 'text')
            elem_id = elem_info.get('id', '')
            
            if self._is_framework_hidden_input_by_id(elem_id):
                return False
            
            if itype in ['text', 'email', 'search', 'tel', 'url'] or elem_info['tag'] == 'textarea':
                is_framework = self._is_framework_select(elem_id)
                
                if is_framework:
                    try:
                        container = page.locator(f'#{elem_id}').locator('..').first
                        container.click(timeout=3000)
                    except:
                        locator.click(timeout=3000)
                else:
                    locator.click(timeout=3000)
                
                page.wait_for_timeout(1500)
                
                options = page.locator('[role="option"]:visible, .ant-select-item:visible, .rc-virtual-list-holder-inner [class*="item"]:visible').all()
                
                if options:
                    print(f"{'  '*depth}    Found {len(options)} dropdown options")
                    for opt in options[:10]:
                        try:
                            opt_text = opt.inner_text()
                            if opt_text:
                                self._save_option(opt_text, page.url)
                        except:
                            pass
                    
                    try:
                        options[0].click(timeout=3000)
                        page.wait_for_timeout(800)
                        print(f"{'  '*depth}    Selected option")
                    except:
                        pass
                else:
                    try:
                        locator.fill("Test Input", timeout=3000)
                        page.wait_for_timeout(500)
                        print(f"{'  '*depth}    Filled input")
                    except:
                        pass
                
                self._extract_all_elements(page)
                return True
            
            elif itype == 'checkbox':
                locator.check(timeout=3000)
                page.wait_for_timeout(500)
                self._extract_all_elements(page)
                return True
            
            return False
        except Exception as e:
            print(f"{'  '*depth}    Input error: {str(e)[:50]}")
            return False
    
    def _handle_click_locator(self, page: Page, locator, depth: int):
        try:
            saved_url = page.url
            locator.click(timeout=5000)
            page.wait_for_timeout(2500)
            
            if page.url != saved_url:
                self._extract_all_elements(page)
                return True
            
            modal = page.locator('[role="dialog"]:visible, .modal:visible, [class*="modal"]:visible, [class*="Modal"]:visible, .ant-modal:visible, [class*="drawer"]:visible').first
            if modal.count() > 0:
                print(f"{'  '*depth}    Modal detected")
                page.wait_for_timeout(1500)
                
                self._extract_all_elements(page)
                
                modal_elements = modal.locator('button:visible, a:visible, input:visible:not([type="hidden"]), select:visible, textarea:visible, [role="button"]:visible, [role="tab"]:visible, li[role]:visible').all()
                print(f"{'  '*depth}    Found {len(modal_elements)} elements in modal")
                
                interacted = 0
                for elem in modal_elements:
                    try:
                        if not elem.is_visible():
                            continue
                        
                        elem_text = elem.inner_text()[:30] if elem.inner_text() else "element"
                        
                        if any(skip in elem_text.lower() for skip in ['pod gallery', 'upgrade', 'home', 'back']):
                            continue
                        
                        elem.click(timeout=2000)
                        page.wait_for_timeout(1000)
                        print(f"{'  '*depth}    Clicked: {elem_text}")
                        self._extract_all_elements(page)
                        interacted += 1
                        
                        if interacted >= 5:
                            break
                    except:
                        continue
                
                self._close_modal(page, depth)
            
            self._extract_all_elements(page)
            return True
        except Exception as e:
            print(f"{'  '*depth}    Click error: {str(e)[:50]}")
            return False
    
    def _close_modal(self, page: Page, depth: int):
        close_selectors = [
            'button:has-text("×"):visible',
            'button:has-text("✕"):visible',
            '[aria-label*="close" i]:visible',
            'button:has-text("Close"):visible',
            'button:has-text("Cancel"):visible',
            '[class*="close"]:visible button:visible',
            '.ant-modal-close:visible',
            'svg[data-icon="close"]:visible',
            '[class*="Close"]:visible'
        ]
        
        for selector in close_selectors:
            try:
                close_btn = page.locator(selector).first
                if close_btn.count() > 0:
                    close_btn.click(timeout=2000)
                    page.wait_for_timeout(800)
                    print(f"{'  '*depth}    Closed modal")
                    return True
            except:
                continue
        
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
            print(f"{'  '*depth}    Closed with Escape")
            return True
        except:
            pass
        
        return False
    
    def _should_skip_element(self, text: str) -> bool:
        return any(pattern in text for pattern in self.skip_patterns)
    
    def _is_framework_hidden_input(self, locator) -> bool:
        try:
            elem_id = locator.evaluate('el => el.id || ""')
            return self._is_framework_hidden_input_by_id(elem_id)
        except:
            return False
    
    def _is_framework_hidden_input_strict(self, locator) -> bool:
        try:
            elem_id = locator.evaluate('el => el.id || ""')
            if not elem_id:
                return False
            return any(pattern in elem_id and '-input' in elem_id for pattern in self.framework_patterns)
        except:
            return False
    
    def _is_framework_hidden_input_by_id(self, elem_id: str) -> bool:
        if not elem_id:
            return False
        return any(pattern in elem_id and '-input' in elem_id for pattern in self.framework_patterns)
    
    def _is_framework_select(self, elem_id: str) -> bool:
        if not elem_id:
            return False
        return any(pattern in elem_id for pattern in self.framework_patterns)
    
    def _get_framework_select_label(self, page: Page, elem_id: str) -> str:
        try:
            label = page.evaluate(f"""
                () => {{
                    const el = document.getElementById('{elem_id}');
                    if (!el) return '';
                    let current = el;
                    for (let i = 0; i < 10; i++) {{
                        current = current.parentElement;
                        if (!current) break;
                        const labelEl = current.querySelector('label');
                        if (labelEl) return labelEl.textContent.trim();
                        let sibling = current.previousElementSibling;
                        while (sibling) {{
                            if (sibling.tagName === 'LABEL') return sibling.textContent.trim();
                            const sibLabel = sibling.querySelector('label');
                            if (sibLabel) return sibLabel.textContent.trim();
                            sibling = sibling.previousElementSibling;
                        }}
                    }}
                    return el.getAttribute('aria-label') || el.placeholder || '';
                }}
            """)
            return label
        except:
            return ''
    
    def _extract_all_elements(self, page: Page):
        try:
            page.wait_for_timeout(500)
            elems = page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('button, a, input, select, textarea, [role="button"], [role="link"], [role="tab"], [onclick], [class*="button"], [class*="btn"], [class*="Button"], [class*="Btn"], [class*="avatar"], [class*="profile"], [class*="guest"], [class*="speaker"], [class*="user"], [class*="clickable"], [class*="interactive"]').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width === 0 || rect.height === 0) return;
                        if (style.display === 'none' || style.visibility === 'hidden') return;
                        if (el.type === 'hidden') return;
                        if (style.opacity === '0') return;
                        if (el.id && el.id.includes('react-select') && el.id.includes('-input')) return;
                        if (el.id && el.id.includes('rc_select') && el.id.includes('-input')) return;
                        let label = '';
                        if (el.id && (el.id.includes('select') || el.id.includes('Select') || el.id.includes('rc_select'))) {
                            let current = el;
                            for (let i = 0; i < 10 && !label; i++) {
                                current = current.parentElement;
                                if (!current) break;
                                const labelEl = current.querySelector('label');
                                if (labelEl) {
                                    label = labelEl.textContent.trim();
                                    break;
                                }
                                let sibling = current.previousElementSibling;
                                while (sibling && !label) {
                                    if (sibling.tagName === 'LABEL') {
                                        label = sibling.textContent.trim();
                                        break;
                                    }
                                    const sibLabel = sibling.querySelector('label');
                                    if (sibLabel) {
                                        label = sibLabel.textContent.trim();
                                        break;
                                    }
                                    sibling = sibling.previousElementSibling;
                                }
                            }
                            if (!label) {
                                label = el.getAttribute('aria-label') || el.placeholder || '';
                            }
                        }
                        items.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            name: el.name || null,
                            type: el.type || null,
                            text: (el.textContent || '').trim().substring(0, 200),
                            ariaLabel: el.getAttribute('aria-label') || null,
                            dataTestId: el.getAttribute('data-testid') || null,
                            placeholder: el.placeholder || null,
                            role: el.getAttribute('role') || null,
                            label: label
                        });
                    });
                    return items;
                }
            """)
            print(f"  Extracted {len(elems)} elements from DOM")
            for elem in elems:
                self._save_element(elem, page.url)
        except Exception as e:
            print(f"Extract failed: {str(e)[:80]}")
    
    def _save_element(self, elem: dict, url: str):
        try:
            text = elem.get('text', '') or ''
            sig = f"{elem['tag']}::{elem.get('id')}::{text[:20]}::{url}"
            
            if sig in self.extracted:
                return
            self.extracted.add(sig)
            
            screen_id = self._get_screen_id(url)
            if not screen_id:
                return
            
            label = elem.get('label', '').strip()
            if label:
                name = label
            else:
                name = (elem.get('ariaLabel') or elem.get('placeholder') or 
                       elem.get('dataTestId') or text or elem.get('name') or elem.get('id') or 
                       f"{elem['tag']}_element")
            name = name.replace(' ', '_').replace('\n', '_').replace('*', '').lower()[:100]
            
            css, xpath, priority = self._build_selectors(elem, text)
            
            data = {
                "screen_id": screen_id,
                "element_name": name,
                "element_type": elem['tag'],
                "css_selector": css,
                "xpath": xpath,
                "text_content": text[:500] if text else None,
                "stability_score": 75,
                "verified": True,
                "selector_priority": priority
            }
            
            if elem.get('id'):
                data['element_id'] = elem['id']
            if elem.get('name'):
                data['element_name_attr'] = elem['name']
            if elem.get('dataTestId'):
                data['data_testid'] = elem['dataTestId']
            if elem.get('ariaLabel'):
                data['aria_label'] = elem['ariaLabel']
            if elem.get('role'):
                data['role'] = elem['role']
            
            requests.post(f"{self.api_url}/add-locator", json=data, timeout=5)
        except requests.exceptions.RequestException:
            pass
        except Exception as e:
            print(f"Save element failed: {name[:30]} - {str(e)[:50]}")
    
    def _save_option(self, text: str, url: str):
        try:
            sig = f"option::{text}::{url}"
            if sig in self.extracted:
                return
            self.extracted.add(sig)
            
            screen_id = self._get_screen_id(url)
            if not screen_id:
                return
            
            data = {
                "screen_id": screen_id,
                "element_name": text.replace(' ', '_').lower()[:100],
                "element_type": "option",
                "css_selector": "option",
                "xpath": f"//option[contains(text(), '{text[:30]}')]",
                "text_content": text,
                "stability_score": 70,
                "verified": True,
                "role": "option"
            }
            
            requests.post(f"{self.api_url}/add-locator", json=data, timeout=5)
        except requests.exceptions.RequestException:
            pass
    
    def _build_selectors(self, elem: dict, text: str):
        tag = elem['tag']
        
        if elem.get('dataTestId'):
            return f"[data-testid='{elem['dataTestId']}']", f"//*[@data-testid='{elem['dataTestId']}']", 1
        elif elem.get('id'):
            return f"#{elem['id']}", f"//*[@id='{elem['id']}']", 2
        elif elem.get('ariaLabel'):
            return f"{tag}[aria-label='{elem['ariaLabel'][:30]}']", f"//{tag}[@aria-label='{elem['ariaLabel'][:30]}']", 2
        elif elem.get('name'):
            return f"{tag}[name='{elem['name']}']", f"//{tag}[@name='{elem['name']}']", 3
        elif text.strip():
            txt = text[:30].replace("'", "\\'")
            return tag, f"//{tag}[contains(text(), '{txt}')]", 4
        else:
            return tag, f"//{tag}", 5
    
    def _get_screen_id(self, url: str):
        try:
            clean_url = url.split('?')[0].split('#')[0]
            
            if clean_url in self.screens:
                return self.screens[clean_url]
            
            path = clean_url.replace(self.base_url, '').strip('/')
            screen_name = path.split('/')[-1] if path else 'home'
            
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
            
            return None
        except requests.exceptions.RequestException:
            return None
        except Exception as e:
            print(f"Get screen ID failed: {str(e)[:50]}")
            return None
    
    def _is_login_page(self, page: Page):
        url = page.url.lower()
        if 'login' in url or 'signin' in url:
            return True
        try:
            return page.locator('input[type="password"]').count() > 0
        except:
            return False
    
    def _auto_login(self, page: Page):
        try:
            page.wait_for_timeout(2000)
            
            try:
                page.locator('input[type="email"]').first.fill(self.username, timeout=3000)
            except:
                try:
                    page.locator('input[name="email"]').first.fill(self.username, timeout=3000)
                except:
                    inputs = page.locator('input[type="text"], input:not([type])').all()
                    if inputs:
                        inputs[0].fill(self.username, timeout=3000)
                    else:
                        return False
            
            page.locator('input[type="password"]').first.fill(self.password, timeout=3000)
            
            try:
                with page.expect_navigation(timeout=15000):
                    page.locator('button[type="submit"]').first.click(timeout=5000)
            except:
                page.locator('input[type="password"]').first.press('Enter')
                page.wait_for_timeout(5000)
            
            page.wait_for_load_state("networkidle", timeout=10000)
            return 'login' not in page.url.lower()
        except:
            return False
