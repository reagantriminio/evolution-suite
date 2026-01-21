"""Browser automation module for evolution suite.

This module provides HTTP-based Playwright browser control for evaluator agents,
allowing multiple agents to run in parallel with isolated browser sessions.
"""

from evolution_suite.browser.service import PlaywrightService, BrowserSession

__all__ = ["PlaywrightService", "BrowserSession"]
