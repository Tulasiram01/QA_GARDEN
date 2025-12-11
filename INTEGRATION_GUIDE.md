# Integration Guide: Locator Extraction → LLM Test Generation

## Overview

**System 1 (You):** Extracts UI locators and stores in PostgreSQL via FastAPI  
**System 2 (Next Person):** Fetches locators and uses LLM to generate test cases

---

## New Endpoint Added

### `GET /export/llm-context`

Returns all screens and elements in LLM-optimized format.

**Response Structure:**
```json
{
  "screens": [
    {
      "name": "screen_name",
      "url": "https://app.com/page",
      "title": "Page Title",
      "elements": [
        {
          "name": "element_name",
          "type": "button|input|select|a",
          "css": "CSS selector",
          "xpath": "XPath selector",
          "id": "element ID",
          "testid": "data-testid value",
          "text": "visible text",
          "verified": false
        }
      ]
    }
  ]
}
```

---

## Integration Steps

### For Next Person (LLM Test Generation):

1. **Fetch Locators**
   ```python
   import requests
   data = requests.get("http://localhost:8000/export/llm-context").json()
   ```

2. **Format for LLM**
   ```python
   prompt = f"Generate tests for {screen['name']} with elements: {elements}"
   ```

3. **Send to LLM**
   - OpenAI API
   - Claude API
   - Local LLM (Ollama, etc.)

4. **Get Generated Tests**
   ```python
   def test_login(page):
       page.fill("#email", "user@test.com")
       page.click("#login-btn")
   ```

5. **Execute Tests**
   ```bash
   pytest tests/
   ```

6. **Mark Verified Locators**
   ```python
   requests.put("http://localhost:8000/verify-locator/1", json={"verified": True})
   ```

---

## Example Files

- `examples/llm_integration_example.py` - Python integration code
- `examples/sample_llm_output.md` - Complete flow example

---

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/export/llm-context` | GET | Get all locators for LLM |
| `/screens` | GET | List all screens |
| `/elements/{screen_id}` | GET | Get elements for specific screen |
| `/verify-locator/{element_id}` | PUT | Mark locator as verified |

---

## Workflow

```
┌─────────────────┐
│  Your Crawler   │
│  Extracts UI    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    FastAPI      │
│  Stores in DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /export/llm-    │
│   context       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Her System     │
│  Fetches Data   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      LLM        │
│ Generates Tests │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Test Execution │
│  Verify Results │
└─────────────────┘
```

---

## Benefits

✅ **No JSON files needed** - Real-time API access  
✅ **Always up-to-date** - Latest locators automatically available  
✅ **Bidirectional** - She can mark locators as verified  
✅ **Scalable** - Multiple people can use same locators  
✅ **Traceable** - Timestamps show when locators were extracted  

---

## Next Steps

1. ✅ Start your FastAPI server: `python backend/main.py`
2. ✅ Run crawler to extract locators: `python crawler/main.py`
3. ✅ Share API URL with next person: `http://localhost:8000`
4. ✅ She calls `/export/llm-context` to get locators
5. ✅ She generates tests using LLM
6. ✅ She marks working locators as verified
