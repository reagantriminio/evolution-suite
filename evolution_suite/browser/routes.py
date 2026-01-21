"""API routes for browser automation.

These endpoints provide HTTP-based Playwright control for evaluator agents,
enabling parallel execution with isolated browser sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from evolution_suite.browser.service import PlaywrightService


# === Request/Response Models ===


class CreateSessionRequest(BaseModel):
    """Request to create a new browser session."""

    agentId: str | None = Field(None, description="ID of the agent using this session")
    sessionId: str | None = Field(None, description="Optional custom session ID")


class SessionResponse(BaseModel):
    """Response containing session information."""

    sessionId: str
    agentId: str | None
    createdAt: str
    lastActivity: str
    url: str | None


class NavigateRequest(BaseModel):
    """Request to navigate to a URL."""

    url: str


class ClickRequest(BaseModel):
    """Request to click on an element."""

    selector: str = Field(..., description="CSS selector or text selector")
    button: str = Field("left", description="Mouse button: left, right, middle")
    doubleClick: bool = Field(False, description="Whether to double-click")


class FillRequest(BaseModel):
    """Request to fill a text input."""

    selector: str
    value: str


class TypeRequest(BaseModel):
    """Request to type text character by character."""

    selector: str
    text: str
    delay: int = Field(50, description="Delay between keystrokes in ms")


class PressKeyRequest(BaseModel):
    """Request to press a keyboard key."""

    key: str = Field(..., description="Key to press: Enter, ArrowDown, Tab, etc.")
    selector: str | None = Field(None, description="Optional selector to focus first")


class SelectOptionRequest(BaseModel):
    """Request to select dropdown option(s)."""

    selector: str
    value: str | list[str]


class HoverRequest(BaseModel):
    """Request to hover over an element."""

    selector: str


class WaitForSelectorRequest(BaseModel):
    """Request to wait for an element."""

    selector: str
    state: str = Field("visible", description="visible, hidden, attached, detached")
    timeout: int = Field(30000, description="Timeout in milliseconds")


class WaitForNavigationRequest(BaseModel):
    """Request to wait for navigation."""

    timeout: int = Field(30000, description="Timeout in milliseconds")


class EvaluateRequest(BaseModel):
    """Request to evaluate JavaScript."""

    expression: str


class GetTextContentRequest(BaseModel):
    """Request to get text content."""

    selector: str


class GetAttributeRequest(BaseModel):
    """Request to get an attribute value."""

    selector: str
    attribute: str


class ResizeViewportRequest(BaseModel):
    """Request to resize the viewport."""

    width: int
    height: int


class ScreenshotRequest(BaseModel):
    """Request to take a screenshot."""

    fullPage: bool = Field(False, description="Capture full scrollable page")
    filename: str | None = Field(None, description="Optional filename")


class HandleDialogRequest(BaseModel):
    """Request to handle a dialog."""

    accept: bool = Field(True, description="Whether to accept the dialog")
    promptText: str | None = Field(None, description="Text for prompt dialogs")


class BrowserStatusResponse(BaseModel):
    """Response containing browser service status."""

    initialized: bool
    headless: bool
    activeSessions: int
    sessions: list[dict]


class OperationResponse(BaseModel):
    """Generic operation response."""

    success: bool
    error: str | None = None
    data: dict | None = None


def create_browser_router(playwright_service: PlaywrightService) -> APIRouter:
    """Create the browser API router."""

    router = APIRouter(prefix="/api/browser", tags=["browser"])

    # === Service Status ===

    @router.get("/status", response_model=BrowserStatusResponse)
    async def get_browser_status() -> BrowserStatusResponse:
        """Get browser service status."""
        status = playwright_service.get_status()
        return BrowserStatusResponse(**status)

    # === Session Management ===

    @router.get("/sessions", response_model=list[SessionResponse])
    async def list_sessions():
        """List all active browser sessions."""
        sessions = playwright_service.list_sessions()
        return [SessionResponse(**s) for s in sessions]

    @router.post("/sessions", response_model=SessionResponse)
    async def create_session(request: CreateSessionRequest):
        """Create a new isolated browser session."""
        try:
            session = await playwright_service.create_session(
                agent_id=request.agentId,
                session_id=request.sessionId,
            )
            return SessionResponse(**session.to_dict())
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str):
        """Get a specific browser session."""
        session = await playwright_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionResponse(**session.to_dict())

    @router.delete("/sessions/{session_id}")
    async def close_session(session_id: str):
        """Close a browser session."""
        success = await playwright_service.close_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True, "message": f"Session {session_id} closed"}

    @router.get("/sessions/agent/{agent_id}", response_model=SessionResponse)
    async def get_session_for_agent(agent_id: str):
        """Get or create a session for an agent."""
        session = await playwright_service.get_or_create_session(agent_id)
        return SessionResponse(**session.to_dict())

    # === Navigation ===

    @router.post("/sessions/{session_id}/navigate", response_model=OperationResponse)
    async def navigate(session_id: str, request: NavigateRequest):
        """Navigate to a URL."""
        try:
            result = await playwright_service.navigate(session_id, request.url)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/back", response_model=OperationResponse)
    async def navigate_back(session_id: str):
        """Navigate back in history."""
        try:
            result = await playwright_service.navigate_back(session_id)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/forward", response_model=OperationResponse)
    async def navigate_forward(session_id: str):
        """Navigate forward in history."""
        try:
            result = await playwright_service.navigate_forward(session_id)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/reload", response_model=OperationResponse)
    async def reload(session_id: str):
        """Reload the current page."""
        try:
            result = await playwright_service.reload(session_id)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # === Page Content ===

    @router.get("/sessions/{session_id}/snapshot", response_model=OperationResponse)
    async def get_snapshot(session_id: str):
        """Get accessibility snapshot of the page.

        This is the preferred method for agents to understand page content.
        """
        try:
            result = await playwright_service.get_snapshot(session_id)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/screenshot", response_model=OperationResponse)
    async def take_screenshot(session_id: str, request: ScreenshotRequest):
        """Take a screenshot of the current page."""
        try:
            result = await playwright_service.take_screenshot(
                session_id,
                full_page=request.fullPage,
                filename=request.filename,
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/sessions/{session_id}/content", response_model=OperationResponse)
    async def get_page_content(session_id: str):
        """Get the full HTML content of the page."""
        try:
            result = await playwright_service.get_page_content(session_id)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/text-content", response_model=OperationResponse)
    async def get_text_content(session_id: str, request: GetTextContentRequest):
        """Get text content of an element."""
        try:
            result = await playwright_service.get_text_content(session_id, request.selector)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/attribute", response_model=OperationResponse)
    async def get_attribute(session_id: str, request: GetAttributeRequest):
        """Get an attribute value from an element."""
        try:
            result = await playwright_service.get_attribute(
                session_id, request.selector, request.attribute
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # === Interactions ===

    @router.post("/sessions/{session_id}/click", response_model=OperationResponse)
    async def click(session_id: str, request: ClickRequest):
        """Click on an element."""
        try:
            result = await playwright_service.click(
                session_id,
                request.selector,
                button=request.button,
                double_click=request.doubleClick,
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/fill", response_model=OperationResponse)
    async def fill(session_id: str, request: FillRequest):
        """Fill a text input."""
        try:
            result = await playwright_service.fill(session_id, request.selector, request.value)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/type", response_model=OperationResponse)
    async def type_text(session_id: str, request: TypeRequest):
        """Type text character by character."""
        try:
            result = await playwright_service.type_text(
                session_id, request.selector, request.text, delay=request.delay
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/press-key", response_model=OperationResponse)
    async def press_key(session_id: str, request: PressKeyRequest):
        """Press a keyboard key."""
        try:
            result = await playwright_service.press_key(
                session_id, request.key, selector=request.selector
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/select-option", response_model=OperationResponse)
    async def select_option(session_id: str, request: SelectOptionRequest):
        """Select option(s) in a dropdown."""
        try:
            result = await playwright_service.select_option(
                session_id, request.selector, request.value
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/hover", response_model=OperationResponse)
    async def hover(session_id: str, request: HoverRequest):
        """Hover over an element."""
        try:
            result = await playwright_service.hover(session_id, request.selector)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # === Waiting ===

    @router.post("/sessions/{session_id}/wait-for-selector", response_model=OperationResponse)
    async def wait_for_selector(session_id: str, request: WaitForSelectorRequest):
        """Wait for an element to appear/disappear."""
        try:
            result = await playwright_service.wait_for_selector(
                session_id,
                request.selector,
                state=request.state,
                timeout=request.timeout,
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/wait-for-navigation", response_model=OperationResponse)
    async def wait_for_navigation(session_id: str, request: WaitForNavigationRequest):
        """Wait for navigation to complete."""
        try:
            result = await playwright_service.wait_for_navigation(
                session_id, timeout=request.timeout
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # === Advanced ===

    @router.post("/sessions/{session_id}/evaluate", response_model=OperationResponse)
    async def evaluate(session_id: str, request: EvaluateRequest):
        """Evaluate JavaScript in the page context."""
        try:
            result = await playwright_service.evaluate(session_id, request.expression)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/resize", response_model=OperationResponse)
    async def resize_viewport(session_id: str, request: ResizeViewportRequest):
        """Resize the browser viewport."""
        try:
            result = await playwright_service.resize_viewport(
                session_id, request.width, request.height
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/sessions/{session_id}/handle-dialog", response_model=OperationResponse)
    async def handle_dialog(session_id: str, request: HandleDialogRequest):
        """Set up a handler for the next dialog."""
        try:
            result = await playwright_service.handle_dialog(
                session_id,
                accept=request.accept,
                prompt_text=request.promptText,
            )
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/sessions/{session_id}/console", response_model=OperationResponse)
    async def get_console_messages(session_id: str):
        """Get console messages from the page."""
        try:
            result = await playwright_service.get_console_messages(session_id)
            return OperationResponse(
                success=result.get("success", False),
                error=result.get("error"),
                data=result,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    return router
