"""MCP Server for Evolution Suite agent management.

This MCP server exposes tools for spawning and managing evolution-suite agents,
allowing the master coordinator to delegate work to workers and evaluators.

The server communicates with the evolution-suite backend via HTTP API.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel


# Default API URL - can be overridden via environment variable
API_BASE_URL = os.environ.get("EVOLUTION_SUITE_API_URL", "http://localhost:8000/api")


class SpawnWorkerArgs(BaseModel):
    """Arguments for spawn_worker tool."""
    task_description: str
    files_to_modify: list[str] | None = None
    acceptance_criteria: str | None = None


class SpawnEvaluatorArgs(BaseModel):
    """Arguments for spawn_evaluator tool."""
    review_scope: str
    files_to_review: list[str] | None = None
    criteria: str | None = None


class GetAgentStatusArgs(BaseModel):
    """Arguments for get_agent_status tool."""
    agent_id: str


class GetAgentOutputArgs(BaseModel):
    """Arguments for get_agent_output tool."""
    agent_id: str
    limit: int = 50


class WaitForAgentArgs(BaseModel):
    """Arguments for wait_for_agent tool."""
    agent_id: str
    timeout_seconds: int = 300


def create_mcp_server(api_base_url: str | None = None) -> Server:
    """Create an MCP server with agent management tools."""

    base_url = api_base_url or API_BASE_URL
    server = Server("evolution-suite-agents")

    # HTTP client for API calls
    client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="spawn_worker",
                description="""Spawn a new WORKER agent to implement code changes.

Workers are execution agents that:
- Write code and implement features
- Fix bugs and issues
- Run tests and build commands
- Make changes to files

Use this when you need code to be written or modified.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "Clear description of what the worker should implement or fix"
                        },
                        "files_to_modify": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of files the worker should focus on (optional)"
                        },
                        "acceptance_criteria": {
                            "type": "string",
                            "description": "What success looks like for this task (optional)"
                        }
                    },
                    "required": ["task_description"]
                }
            ),
            Tool(
                name="spawn_evaluator",
                description="""Spawn a new EVALUATOR agent to review code changes.

Evaluators are review agents that:
- Review code for bugs and issues
- Check code quality and best practices
- Verify test coverage
- Suggest improvements

Use this after workers complete their tasks to validate the changes.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "review_scope": {
                            "type": "string",
                            "description": "What the evaluator should review"
                        },
                        "files_to_review": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of files to review (optional)"
                        },
                        "criteria": {
                            "type": "string",
                            "description": "Specific criteria to evaluate against (optional)"
                        }
                    },
                    "required": ["review_scope"]
                }
            ),
            Tool(
                name="list_agents",
                description="""List all current agents and their status.

Returns information about all spawned agents including:
- Agent ID and type (coordinator/worker/evaluator)
- Current status (idle/running/paused/stopped/failed)
- Current task or goal
- Output statistics""",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_agent_status",
                description="""Get detailed status of a specific agent.

Returns the agent's current state, task, and recent activity.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent to check"
                        }
                    },
                    "required": ["agent_id"]
                }
            ),
            Tool(
                name="get_agent_output",
                description="""Get recent output from an agent.

Useful for checking what an agent has been doing and whether it encountered issues.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent output lines to return (default 50)",
                            "default": 50
                        }
                    },
                    "required": ["agent_id"]
                }
            ),
            Tool(
                name="wait_for_agent",
                description="""Wait for an agent to complete its task.

Blocks until the agent reaches a terminal state (stopped/failed) or timeout.
Use this when you need to wait for a worker to finish before spawning evaluators.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent to wait for"
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Maximum time to wait (default 300 seconds)",
                            "default": 300
                        }
                    },
                    "required": ["agent_id"]
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        try:
            if name == "spawn_worker":
                args = SpawnWorkerArgs(**arguments)
                return await _spawn_worker(client, args)

            elif name == "spawn_evaluator":
                args = SpawnEvaluatorArgs(**arguments)
                return await _spawn_evaluator(client, args)

            elif name == "list_agents":
                return await _list_agents(client)

            elif name == "get_agent_status":
                args = GetAgentStatusArgs(**arguments)
                return await _get_agent_status(client, args)

            elif name == "get_agent_output":
                args = GetAgentOutputArgs(**arguments)
                return await _get_agent_output(client, args)

            elif name == "wait_for_agent":
                args = WaitForAgentArgs(**arguments)
                return await _wait_for_agent(client, args)

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"API error: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def _spawn_worker(client: httpx.AsyncClient, args: SpawnWorkerArgs) -> list[TextContent]:
    """Spawn a worker agent via HTTP API."""
    # Spawn the agent
    response = await client.post("/agents", json={"type": "worker"})
    response.raise_for_status()
    agent = response.json()
    agent_id = agent["id"]

    # Build the prompt
    prompt_parts = [
        f"WORKER TASK: {args.task_description}",
    ]

    if args.files_to_modify:
        prompt_parts.append(f"\nFiles to modify: {', '.join(args.files_to_modify)}")

    if args.acceptance_criteria:
        prompt_parts.append(f"\nAcceptance criteria: {args.acceptance_criteria}")

    prompt_parts.append("\n\nComplete this task thoroughly. When done, summarize what you accomplished.")

    prompt = "\n".join(prompt_parts)

    # Start the agent
    response = await client.post(f"/agents/{agent_id}/start", json={"content": prompt})
    response.raise_for_status()

    return [TextContent(
        type="text",
        text=f"Worker spawned and started.\nAgent ID: {agent_id}\nTask: {args.task_description}"
    )]


async def _spawn_evaluator(client: httpx.AsyncClient, args: SpawnEvaluatorArgs) -> list[TextContent]:
    """Spawn an evaluator agent via HTTP API."""
    # Spawn the agent
    response = await client.post("/agents", json={"type": "evaluator"})
    response.raise_for_status()
    agent = response.json()
    agent_id = agent["id"]

    # Build the prompt
    prompt_parts = [
        f"EVALUATOR TASK: Review and evaluate the following:\n{args.review_scope}",
    ]

    if args.files_to_review:
        prompt_parts.append(f"\nFiles to review: {', '.join(args.files_to_review)}")

    if args.criteria:
        prompt_parts.append(f"\nEvaluation criteria: {args.criteria}")

    prompt_parts.append("""

Your evaluation should check:
1. Code correctness - Does it work as intended?
2. Code quality - Is it clean, readable, maintainable?
3. Test coverage - Are there adequate tests?
4. Edge cases - Are edge cases handled?
5. Security - Any potential security issues?

Provide a clear summary of findings with specific issues and recommendations.""")

    prompt = "\n".join(prompt_parts)

    # Start the agent
    response = await client.post(f"/agents/{agent_id}/start", json={"content": prompt})
    response.raise_for_status()

    return [TextContent(
        type="text",
        text=f"Evaluator spawned and started.\nAgent ID: {agent_id}\nReview scope: {args.review_scope}"
    )]


async def _list_agents(client: httpx.AsyncClient) -> list[TextContent]:
    """List all agents via HTTP API."""
    response = await client.get("/agents")
    response.raise_for_status()
    agents = response.json()

    if not agents:
        return [TextContent(type="text", text="No agents currently spawned.")]

    lines = ["Current agents:\n"]

    for agent in agents:
        status = agent.get("status", "unknown")
        status_emoji = {
            "idle": "⚪",
            "running": "🟢",
            "paused": "🟡",
            "stopped": "⚫",
            "failed": "🔴",
        }.get(status, "❓")

        agent_type = agent.get("type", "unknown")
        agent_id = agent.get("id", "unknown")
        goal = agent.get("goal")
        current_task = agent.get("currentTask")

        lines.append(f"{status_emoji} [{agent_type.upper()}] {agent_id}")
        lines.append(f"   Status: {status}")
        if goal:
            lines.append(f"   Goal: {goal[:100]}...")
        if current_task:
            lines.append(f"   Task: {current_task[:100]}...")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _get_agent_status(client: httpx.AsyncClient, args: GetAgentStatusArgs) -> list[TextContent]:
    """Get status of a specific agent via HTTP API."""
    response = await client.get(f"/agents/{args.agent_id}")

    if response.status_code == 404:
        return [TextContent(type="text", text=f"Agent not found: {args.agent_id}")]

    response.raise_for_status()
    agent = response.json()

    lines = [
        f"Agent: {agent.get('id')}",
        f"Type: {agent.get('type')}",
        f"Status: {agent.get('status')}",
        f"Goal: {agent.get('goal') or 'None'}",
        f"Current Task: {agent.get('currentTask') or 'None'}",
        f"Tools Used: {agent.get('toolsUsed', 0)}",
        f"Files Modified: {len(agent.get('filesModified', []))}",
        f"Output Lines: {agent.get('outputLines', 0)}",
    ]

    files_modified = agent.get("filesModified", [])
    if files_modified:
        lines.append(f"Modified Files: {', '.join(files_modified[:5])}")
        if len(files_modified) > 5:
            lines.append(f"   ... and {len(files_modified) - 5} more")

    return [TextContent(type="text", text="\n".join(lines))]


async def _get_agent_output(client: httpx.AsyncClient, args: GetAgentOutputArgs) -> list[TextContent]:
    """Get recent output from an agent via HTTP API."""
    response = await client.get(f"/agents/{args.agent_id}/output", params={"limit": args.limit})

    if response.status_code == 404:
        return [TextContent(type="text", text=f"Agent not found: {args.agent_id}")]

    response.raise_for_status()
    data = response.json()
    output = data.get("lines", [])

    if not output:
        return [TextContent(type="text", text=f"No output from agent {args.agent_id}")]

    lines = [f"Recent output from {args.agent_id}:\n"]

    for line in output:
        line_type = line.get("type", "text")
        prefix = {
            "text": "",
            "thinking": "[thinking] ",
            "tool_use": "[tool] ",
            "result": "[result] ",
            "error": "[ERROR] ",
        }.get(line_type, "")

        content = line.get("content", "")
        content = content[:200] + "..." if len(content) > 200 else content
        lines.append(f"{prefix}{content}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _wait_for_agent(client: httpx.AsyncClient, args: WaitForAgentArgs) -> list[TextContent]:
    """Wait for an agent to complete via HTTP API."""
    terminal_states = {"stopped", "failed", "idle"}

    # Get initial status
    response = await client.get(f"/agents/{args.agent_id}")
    if response.status_code == 404:
        return [TextContent(type="text", text=f"Agent not found: {args.agent_id}")]

    response.raise_for_status()
    agent = response.json()
    status = agent.get("status")

    if status in terminal_states:
        return [TextContent(
            type="text",
            text=f"Agent {args.agent_id} already in terminal state: {status}"
        )]

    # Poll for completion
    elapsed = 0
    poll_interval = 2  # seconds

    while elapsed < args.timeout_seconds:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        response = await client.get(f"/agents/{args.agent_id}")
        if response.status_code == 404:
            return [TextContent(type="text", text=f"Agent {args.agent_id} was removed")]

        response.raise_for_status()
        agent = response.json()
        status = agent.get("status")

        if status in terminal_states:
            # Get final output
            output_response = await client.get(
                f"/agents/{args.agent_id}/output",
                params={"limit": 10}
            )
            output_summary = ""
            if output_response.status_code == 200:
                output_data = output_response.json()
                output_lines = output_data.get("lines", [])[-5:]
                if output_lines:
                    output_summary = "\n\nFinal output:\n" + "\n".join(
                        line.get("content", "")[:100] for line in output_lines
                    )

            return [TextContent(
                type="text",
                text=f"Agent {args.agent_id} completed with status: {status}{output_summary}"
            )]

    return [TextContent(
        type="text",
        text=f"Timeout waiting for agent {args.agent_id}. Current status: {status}"
    )]
