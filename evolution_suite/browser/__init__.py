"""Browser automation module for evolution suite.

This module provides HTTP-based Playwright browser control for evaluator agents,
allowing multiple agents to run in parallel with isolated browser sessions.
"""

try:
    from evolution_suite.browser.service import PlaywrightService, BrowserSession
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PlaywrightService = None  # type: ignore
    BrowserSession = None  # type: ignore
    PLAYWRIGHT_AVAILABLE = False

__all__ = ["PlaywrightService", "BrowserSession", "PLAYWRIGHT_AVAILABLE"]
