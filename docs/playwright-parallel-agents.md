# Playwright Parallel Agents Configuration

This document outlines solutions for running multiple evaluator agents with Playwright without session conflicts or focus limitations.

## Problems

### 1. Session Conflicts
Multiple agents sharing the same Playwright MCP server instance fight over the same browser tab/window, producing inconsistent results.

### 2. Window Focus Limitation
Only 2 windows can be in focus at a time in headed mode, limiting parallel agent capabilities.

## Solutions

### Recommended: Headless + Isolated Mode

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--headless",
        "--isolated"
      ]
    }
  }
}
```

| Flag | Purpose |
|------|---------|
| `--headless` | No GUI - eliminates focus conflicts entirely |
| `--isolated` | Each session uses in-memory profile, no shared state |

### Alternative: Multiple MCP Server Instances

For complete isolation, configure separate Playwright MCP servers:

```json
{
  "mcpServers": {
    "playwright-agent1": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless", "--user-data-dir=/tmp/playwright-agent1"]
    },
    "playwright-agent2": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless", "--user-data-dir=/tmp/playwright-agent2"]
    },
    "playwright-agent3": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless", "--user-data-dir=/tmp/playwright-agent3"]
    }
  }
}
```

Each agent gets its own:
- Browser instance
- User data directory
- Session state

### Alternative: Browser Contexts (Programmatic)

If controlling Playwright directly (not via MCP), use separate `BrowserContext` objects:

```javascript
const browser = await chromium.launch({ headless: true });

// Each agent gets its own context - fully isolated
const context1 = await browser.newContext();
const context2 = await browser.newContext();
const context3 = await browser.newContext();

// Contexts have separate cookies, cache, storage
const page1 = await context1.newPage();
const page2 = await context2.newPage();
const page3 = await context3.newPage();
```

## Headless Mode Details

### Functionality Comparison

| Aspect | Headless | Headed |
|--------|----------|--------|
| DOM interaction | ✅ Full | ✅ Full |
| JavaScript execution | ✅ Full | ✅ Full |
| Network requests | ✅ Full | ✅ Full |
| Screenshots | ✅ Yes | ✅ Yes |
| Video recording | ✅ Yes | ✅ Yes |
| File uploads/downloads | ✅ Yes | ✅ Yes |
| Performance | ~20-30% faster | Slower |

### How Screenshots Work in Headless Mode

Headless browsers fully render pages to an in-memory pixel buffer - they just don't output to a physical display.

```
┌─────────────────────────────────────────────────┐
│  Browser Engine (same in both modes)            │
├─────────────────────────────────────────────────┤
│  1. Parse HTML → DOM tree                       │
│  2. Parse CSS → Style rules                     │
│  3. Execute JavaScript                          │
│  4. Layout calculation (positions, sizes)       │
│  5. Paint (rasterize to pixel buffer in memory) │
└─────────────────────────────────────────────────┘
          │                         │
          ▼                         ▼
    ┌──────────┐             ┌──────────────┐
    │ Headed   │             │  Headless    │
    │ Output → │             │  Buffer stays│
    │ Monitor  │             │  in memory   │
    └──────────┘             └──────────────┘
```

When `page.screenshot()` is called:
1. Browser renders page to internal buffer (happens in both modes)
2. Playwright reads buffer directly from memory
3. Encodes as PNG/JPEG

**No physical display needed** - screenshots come from the browser's internal rendering.

### Minor Differences

- **Timing**: Headless can expose race conditions masked by GUI rendering delays
- **PDF rendering**: PDFs render in-page (instead of downloading)
- **Screenshot pixels**: Minor differences (2-5 pixels) possible between modes
- **Bot detection**: Some sites detect headless differently (usually not an issue for internal apps)

## Configuration Reference

### Playwright MCP Flags

| Flag | Description |
|------|-------------|
| `--headless` | Run without GUI |
| `--isolated` | Use in-memory profile (no disk persistence) |
| `--user-data-dir=<path>` | Custom profile directory for persistence |
| `--storage-state=<path>` | Load initial cookies/storage from file |
| `--port=<port>` | SSE transport port |
| `--host=<host>` | Binding address (default: localhost) |
| `--shared-browser-context` | Reuse context across HTTP clients |

### JSON Config File

Create a config file and reference with `--config path/to/config.json`:

```json
{
  "browser": {
    "isolated": true,
    "headless": true,
    "userDataDir": "/path/to/profile"
  },
  "server": {
    "port": 3000,
    "host": "localhost"
  }
}
```

## Implementation Checklist

- [x] Create HTTP-based PlaywrightService for browser session management
- [x] Add API routes for browser operations (`/api/browser/*`)
- [x] Configure headless and isolated browser instances
- [x] Update configuration to support Playwright settings
- [ ] Test single evaluator agent in headless mode to verify functionality
- [ ] Test multiple evaluator agents running in parallel
- [ ] Verify screenshots are captured correctly

## HTTP API Implementation

Instead of using MCP servers, evolution-suite uses a direct HTTP API for Playwright control. This provides:

1. **Full control over session isolation** - Each evaluator agent gets its own browser session
2. **Centralized browser management** - Single service manages all browser instances
3. **Simplified architecture** - No MCP server configuration needed

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/browser/status` | GET | Get browser service status |
| `/api/browser/sessions` | GET | List all active sessions |
| `/api/browser/sessions` | POST | Create new browser session |
| `/api/browser/sessions/{id}` | DELETE | Close browser session |
| `/api/browser/sessions/{id}/navigate` | POST | Navigate to URL |
| `/api/browser/sessions/{id}/snapshot` | GET | Get accessibility snapshot |
| `/api/browser/sessions/{id}/screenshot` | POST | Take screenshot |
| `/api/browser/sessions/{id}/click` | POST | Click element |
| `/api/browser/sessions/{id}/fill` | POST | Fill form field |
| `/api/browser/sessions/{id}/type` | POST | Type text |

### Configuration

Add to `evolution.yaml`:

```yaml
playwright:
  enabled: true
  headless: true
  screenshot_dir: "/tmp/evolution-suite-screenshots"
```

## References

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
- [Issue #893: Multiple parallel agents interference](https://github.com/microsoft/playwright-mcp/issues/893)
- [Playwright Browser Contexts](https://playwright.dev/docs/browser-contexts)
- [Playwright Visual Comparisons](https://playwright.dev/docs/test-snapshots)
