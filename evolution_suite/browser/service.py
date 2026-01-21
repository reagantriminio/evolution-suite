"""Playwright service for managing isolated browser sessions.

This service provides HTTP-based browser control for evaluator agents,
enabling parallel execution without session conflicts.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Error as PlaywrightError,
)


@dataclass
class BrowserSession:
    """Represents an isolated browser session for an agent."""

    session_id: str
    agent_id: str | None
    context: BrowserContext
    page: Page
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    screenshot_dir: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessionId": self.session_id,
            "agentId": self.agent_id,
            "createdAt": self.created_at.isoformat(),
            "lastActivity": self.last_activity.isoformat(),
            "url": self.page.url if self.page else None,
        }


class PlaywrightService:
    """Manages multiple isolated Playwright browser sessions.

    Each evaluator agent gets its own browser context with:
    - Isolated cookies, storage, and cache
    - Independent page state
    - Separate screenshot directory

    Supports headless mode for parallel execution without focus conflicts.
    """

    def __init__(
        self,
        headless: bool = True,
        screenshot_base_dir: Path | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.headless = headless
        self.screenshot_base_dir = screenshot_base_dir or Path("/tmp/evolution-suite-screenshots")
        self._on_event = on_event

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _emit_event(self, event_type: str, **data: Any) -> None:
        """Emit an event to listeners."""
        if self._on_event:
            self._on_event({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                **data,
            })

    async def initialize(self) -> None:
        """Initialize Playwright and browser."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            self._initialized = True

            self._emit_event("browser_initialized", headless=self.headless)

    async def shutdown(self) -> None:
        """Shutdown Playwright and close all sessions."""
        async with self._lock:
            # Close all sessions
            for session in list(self._sessions.values()):
                await self._close_session_internal(session)
            self._sessions.clear()

            # Close browser
            if self._browser:
                await self._browser.close()
                self._browser = None

            # Stop playwright
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._initialized = False
            self._emit_event("browser_shutdown")

    async def create_session(
        self,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> BrowserSession:
        """Create a new isolated browser session.

        Args:
            agent_id: Optional ID of the agent using this session
            session_id: Optional custom session ID (auto-generated if not provided)

        Returns:
            A new BrowserSession with isolated context
        """
        await self.initialize()

        if not self._browser:
            raise RuntimeError("Browser not initialized")

        session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"

        # Create isolated context with its own storage
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )

        # Create page in this context
        page = await context.new_page()

        # Set up screenshot directory
        screenshot_dir = self.screenshot_base_dir / session_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        session = BrowserSession(
            session_id=session_id,
            agent_id=agent_id,
            context=context,
            page=page,
            screenshot_dir=screenshot_dir,
        )

        async with self._lock:
            self._sessions[session_id] = session

        self._emit_event(
            "session_created",
            sessionId=session_id,
            agentId=agent_id,
        )

        return session

    async def get_session(self, session_id: str) -> BrowserSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def get_session_for_agent(self, agent_id: str) -> BrowserSession | None:
        """Get the session associated with an agent."""
        for session in self._sessions.values():
            if session.agent_id == agent_id:
                return session
        return None

    async def get_or_create_session(self, agent_id: str) -> BrowserSession:
        """Get existing session for agent or create new one."""
        session = await self.get_session_for_agent(agent_id)
        if session:
            return session
        return await self.create_session(agent_id=agent_id)

    async def close_session(self, session_id: str) -> bool:
        """Close a browser session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        async with self._lock:
            await self._close_session_internal(session)
            del self._sessions[session_id]

        self._emit_event("session_closed", sessionId=session_id)
        return True

    async def _close_session_internal(self, session: BrowserSession) -> None:
        """Internal method to close a session without lock."""
        try:
            if session.context:
                await session.context.close()
        except Exception:
            pass

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions."""
        return [s.to_dict() for s in self._sessions.values()]

    # === Browser Operations ===

    async def navigate(self, session_id: str, url: str) -> dict[str, Any]:
        """Navigate to a URL."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            response = await session.page.goto(url, wait_until="domcontentloaded")
            return {
                "success": True,
                "url": session.page.url,
                "status": response.status if response else None,
            }
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def navigate_back(self, session_id: str) -> dict[str, Any]:
        """Navigate back in history."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.go_back()
            return {"success": True, "url": session.page.url}
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def navigate_forward(self, session_id: str) -> dict[str, Any]:
        """Navigate forward in history."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.go_forward()
            return {"success": True, "url": session.page.url}
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def reload(self, session_id: str) -> dict[str, Any]:
        """Reload the current page."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.reload()
            return {"success": True, "url": session.page.url}
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        """Get accessibility snapshot of the page.

        This is the preferred method for agents to understand page content,
        as it provides structured information about interactive elements.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            # Get accessibility tree
            snapshot = await session.page.accessibility.snapshot()
            return {
                "success": True,
                "url": session.page.url,
                "title": await session.page.title(),
                "snapshot": snapshot,
            }
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def take_screenshot(
        self,
        session_id: str,
        full_page: bool = False,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Take a screenshot of the current page.

        Args:
            session_id: The session ID
            full_page: Whether to capture full scrollable page
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Screenshot info including path and base64 data
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                filename = f"screenshot-{timestamp}.png"

            # Ensure filename ends with .png
            if not filename.endswith(".png"):
                filename += ".png"

            # Full path
            filepath = session.screenshot_dir / filename if session.screenshot_dir else Path(filename)

            # Take screenshot
            screenshot_bytes = await session.page.screenshot(full_page=full_page)

            # Save to file
            filepath.write_bytes(screenshot_bytes)

            # Encode to base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return {
                "success": True,
                "path": str(filepath),
                "filename": filename,
                "base64": screenshot_b64,
                "fullPage": full_page,
            }
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def click(
        self,
        session_id: str,
        selector: str,
        button: str = "left",
        double_click: bool = False,
    ) -> dict[str, Any]:
        """Click on an element.

        Args:
            session_id: The session ID
            selector: CSS selector or text selector (e.g., "text=Submit")
            button: Mouse button (left, right, middle)
            double_click: Whether to double-click
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            if double_click:
                await session.page.dblclick(selector, button=button)
            else:
                await session.page.click(selector, button=button)
            return {"success": True, "selector": selector}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def fill(
        self,
        session_id: str,
        selector: str,
        value: str,
    ) -> dict[str, Any]:
        """Fill a text input.

        Args:
            session_id: The session ID
            selector: CSS selector for the input
            value: Text to fill
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.fill(selector, value)
            return {"success": True, "selector": selector}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def type_text(
        self,
        session_id: str,
        selector: str,
        text: str,
        delay: int = 50,
    ) -> dict[str, Any]:
        """Type text character by character (useful for triggering key handlers).

        Args:
            session_id: The session ID
            selector: CSS selector for the input
            text: Text to type
            delay: Delay between keystrokes in ms
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.type(selector, text, delay=delay)
            return {"success": True, "selector": selector}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def press_key(
        self,
        session_id: str,
        key: str,
        selector: str | None = None,
    ) -> dict[str, Any]:
        """Press a keyboard key.

        Args:
            session_id: The session ID
            key: Key to press (e.g., "Enter", "ArrowDown", "a")
            selector: Optional selector to focus first
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            if selector:
                await session.page.press(selector, key)
            else:
                await session.page.keyboard.press(key)
            return {"success": True, "key": key}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "key": key}

    async def select_option(
        self,
        session_id: str,
        selector: str,
        value: str | list[str],
    ) -> dict[str, Any]:
        """Select option(s) in a dropdown.

        Args:
            session_id: The session ID
            selector: CSS selector for the select element
            value: Option value(s) to select
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            values = [value] if isinstance(value, str) else value
            await session.page.select_option(selector, values)
            return {"success": True, "selector": selector, "values": values}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def hover(self, session_id: str, selector: str) -> dict[str, Any]:
        """Hover over an element."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.hover(selector)
            return {"success": True, "selector": selector}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def wait_for_selector(
        self,
        session_id: str,
        selector: str,
        state: str = "visible",
        timeout: int = 30000,
    ) -> dict[str, Any]:
        """Wait for an element to appear/disappear.

        Args:
            session_id: The session ID
            selector: CSS selector
            state: visible, hidden, attached, detached
            timeout: Timeout in milliseconds
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.wait_for_selector(selector, state=state, timeout=timeout)
            return {"success": True, "selector": selector, "state": state}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def wait_for_navigation(
        self,
        session_id: str,
        timeout: int = 30000,
    ) -> dict[str, Any]:
        """Wait for navigation to complete."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return {"success": True, "url": session.page.url}
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def evaluate(
        self,
        session_id: str,
        expression: str,
    ) -> dict[str, Any]:
        """Evaluate JavaScript in the page context.

        Args:
            session_id: The session ID
            expression: JavaScript expression to evaluate
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            result = await session.page.evaluate(expression)
            return {"success": True, "result": result}
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def get_page_content(self, session_id: str) -> dict[str, Any]:
        """Get the full HTML content of the page."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            content = await session.page.content()
            return {
                "success": True,
                "url": session.page.url,
                "title": await session.page.title(),
                "content": content,
            }
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def get_text_content(
        self,
        session_id: str,
        selector: str,
    ) -> dict[str, Any]:
        """Get text content of an element."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            text = await session.page.text_content(selector)
            return {"success": True, "selector": selector, "text": text}
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def get_attribute(
        self,
        session_id: str,
        selector: str,
        attribute: str,
    ) -> dict[str, Any]:
        """Get an attribute value from an element."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            value = await session.page.get_attribute(selector, attribute)
            return {
                "success": True,
                "selector": selector,
                "attribute": attribute,
                "value": value,
            }
        except PlaywrightError as e:
            return {"success": False, "error": str(e), "selector": selector}

    async def resize_viewport(
        self,
        session_id: str,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        """Resize the browser viewport."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        try:
            await session.page.set_viewport_size({"width": width, "height": height})
            return {"success": True, "width": width, "height": height}
        except PlaywrightError as e:
            return {"success": False, "error": str(e)}

    async def get_console_messages(self, session_id: str) -> dict[str, Any]:
        """Get console messages from the page.

        Note: This only captures messages after the listener was attached.
        For full console capture, call this at the start of your session.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Note: Would need to attach console listeners at session creation
        # for full support. For now, return empty.
        return {
            "success": True,
            "messages": [],
            "note": "Console listener needs to be attached at session start",
        }

    async def handle_dialog(
        self,
        session_id: str,
        accept: bool = True,
        prompt_text: str | None = None,
    ) -> dict[str, Any]:
        """Handle a dialog (alert, confirm, prompt).

        Note: This sets up a handler for the next dialog.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.last_activity = datetime.now()

        async def dialog_handler(dialog):
            if accept:
                if prompt_text:
                    await dialog.accept(prompt_text)
                else:
                    await dialog.accept()
            else:
                await dialog.dismiss()

        session.page.once("dialog", dialog_handler)
        return {"success": True, "accept": accept}

    def get_status(self) -> dict[str, Any]:
        """Get service status."""
        return {
            "initialized": self._initialized,
            "headless": self.headless,
            "activeSessions": len(self._sessions),
            "sessions": self.list_sessions(),
        }
