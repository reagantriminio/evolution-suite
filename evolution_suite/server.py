"""FastAPI server for evolution suite dashboard."""

from __future__ import annotations

import asyncio
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from evolution_suite.api.routes import create_router
from evolution_suite.comms.file_channel import FileChannel
from evolution_suite.comms.websocket import WebSocketManager
from evolution_suite.core.config import Config, load_config
from evolution_suite.core.orchestrator import Orchestrator


def create_app(config: Config, project_root: Path) -> FastAPI:
    """Create the FastAPI application."""

    # Initialize components
    ws_manager = WebSocketManager()
    file_channel = FileChannel(config.get_state_dir())
    orchestrator = Orchestrator(
        config=config,
        project_root=project_root,
        on_event=ws_manager.create_event_callback(),
    )

    # Register WebSocket message handlers
    async def handle_inject_guidance(data: dict) -> dict:
        agent_id = data.get("agentId")
        content = data.get("content")
        if not agent_id or not content:
            return {"type": "error", "error": "Missing agentId or content"}
        await orchestrator.agent_manager.inject_guidance(agent_id, content)
        return {"type": "guidance_injected", "agentId": agent_id}

    async def handle_update_prompt(data: dict) -> dict:
        name = data.get("name")
        content = data.get("content")
        if not name or not content:
            return {"type": "error", "error": "Missing name or content"}
        prompts_dir = config.get_state_dir() / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / f"{name}.md").write_text(content)
        await ws_manager.broadcast({"type": "prompt_updated", "name": name})
        return {"type": "prompt_updated", "name": name}

    ws_manager.register_handler("inject_guidance", handle_inject_guidance)
    ws_manager.register_handler("update_prompt", handle_update_prompt)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        """Application lifespan handler."""
        yield
        # Cleanup on shutdown
        await orchestrator.force_stop()
        file_channel.cleanup()

    app = FastAPI(
        title="Evolution Suite",
        description="RTS-style command center for autonomous AI agent pools",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    api_router = create_router(orchestrator, file_channel, ws_manager, config)
    app.include_router(api_router)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        await ws_manager.listen(websocket)

    # Static files (frontend)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(static_dir / "index.html")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            # Try to serve the exact file
            file_path = static_dir / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            # Fall back to index.html for SPA routing
            return FileResponse(static_dir / "index.html")
    else:
        @app.get("/")
        async def no_frontend():
            return {
                "message": "Evolution Suite API",
                "note": "Frontend not built. Run 'npm run build' in frontend/ directory.",
                "docs": "/docs",
            }

    return app


async def run_server(
    project_root: Path,
    host: str = "127.0.0.1",
    port: int = 8420,
    open_browser: bool = True,
) -> None:
    """Run the evolution suite server."""
    import uvicorn

    config_path = project_root / "evolution.yaml"
    config = load_config(config_path)

    app = create_app(config, project_root)

    # Open browser after short delay
    if open_browser:
        async def open_browser_delayed():
            await asyncio.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")

        asyncio.create_task(open_browser_delayed())

    # Run server
    server_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()
