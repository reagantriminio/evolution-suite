"""Evolution Suite CLI - Command line interface for managing evolution agents."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from evolution_suite import __version__

app = typer.Typer(
    name="evolution",
    help="RTS-style command center for autonomous AI agent pools",
    no_args_is_help=True,
)
console = Console()

CONFIG_FILENAME = "evolution.yaml"


def get_project_root() -> Path:
    """Find project root by looking for evolution.yaml."""
    current = Path.cwd()
    while current != current.parent:
        if (current / CONFIG_FILENAME).exists():
            return current
        current = current.parent
    return Path.cwd()


@app.command()
def init(
    path: Optional[Path] = typer.Argument(None, help="Project path (default: current directory)"),
):
    """Initialize evolution-suite in a project."""
    project_path = path or Path.cwd()
    config_path = project_path / CONFIG_FILENAME
    state_dir = project_path / "evolution"

    if config_path.exists():
        console.print(f"[yellow]Config already exists:[/] {config_path}")
        raise typer.Exit(1)

    # Create default config
    default_config = '''# Evolution Suite Configuration
project:
  name: "{name}"
  description: "Add your project description here"
  branch: "main"

# Custom prompts (optional - leave commented to use defaults)
# prompts:
#   coordinator: "./evolution/prompts/coordinator.md"
#   worker: "./evolution/prompts/worker.md"
#   evaluator: "./evolution/prompts/evaluator.md"

state:
  directory: "./evolution"

agents:
  coordinator:
    timeout_minutes: 15
  worker:
    timeout_minutes: 45
  evaluator:
    timeout_minutes: 30

server:
  port: 8420
  host: "127.0.0.1"

protection:
  forbidden_files:
    - ".env"
    - ".env.local"
    - ".env.production"
  dangerous_patterns:
    - "DROP DATABASE"
    - "DETACH DELETE"
'''

    config_path.write_text(default_config.format(name=project_path.name))
    console.print(f"[green]Created:[/] {config_path}")

    # Create state directory
    state_dir.mkdir(exist_ok=True)
    (state_dir / ".guidance").mkdir(exist_ok=True)
    (state_dir / ".agent-state").mkdir(exist_ok=True)
    (state_dir / "cycle_logs").mkdir(exist_ok=True)

    # Create initial state file
    state_file = state_dir / "EVOLUTION_STATE.md"
    if not state_file.exists():
        state_file.write_text("""# Evolution State

**Cycle**: 0
**Phase**: IDLE
**Last Updated**: Never

## Current Status

Evolution suite initialized. Run `evolution start` to begin.
""")
        console.print(f"[green]Created:[/] {state_file}")

    # Create log file
    log_file = state_dir / "EVOLUTION_LOG.md"
    if not log_file.exists():
        log_file.write_text("# Evolution Log\n\n")
        console.print(f"[green]Created:[/] {log_file}")

    console.print()
    console.print(Panel(
        "[green]Evolution suite initialized![/]\n\n"
        "Next steps:\n"
        "  1. Edit [cyan]evolution.yaml[/] to configure your project\n"
        "  2. Run [cyan]evolution start[/] to launch the dashboard",
        title="Success",
        border_style="green",
    ))


@app.command()
def start(
    port: int = typer.Option(8420, "--port", "-p", help="Server port"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Server host"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
):
    """Start the evolution dashboard and orchestrator."""
    import asyncio

    from evolution_suite.server import run_server

    project_root = get_project_root()
    config_path = project_root / CONFIG_FILENAME

    if not config_path.exists():
        console.print("[red]No evolution.yaml found.[/] Run [cyan]evolution init[/] first.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[cyan]Project:[/] {project_root.name}\n"
        f"[cyan]Dashboard:[/] http://{host}:{port}",
        title="Evolution Suite",
        border_style="cyan",
    ))

    asyncio.run(run_server(
        project_root=project_root,
        host=host,
        port=port,
        open_browser=not no_browser,
    ))


@app.command()
def run(
    max_cycles: Optional[int] = typer.Option(None, "--max-cycles", "-n", help="Maximum cycles"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print prompts without executing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run evolution headless (no dashboard)."""
    import asyncio

    from evolution_suite.core.orchestrator import Orchestrator
    from evolution_suite.core.config import load_config

    project_root = get_project_root()
    config_path = project_root / CONFIG_FILENAME

    if not config_path.exists():
        console.print("[red]No evolution.yaml found.[/] Run [cyan]evolution init[/] first.")
        raise typer.Exit(1)

    config = load_config(config_path)
    orchestrator = Orchestrator(config, project_root)

    console.print(Panel(
        f"[cyan]Project:[/] {project_root.name}\n"
        f"[cyan]Max Cycles:[/] {max_cycles or 'unlimited'}",
        title="Evolution Suite - Headless",
        border_style="cyan",
    ))

    try:
        asyncio.run(orchestrator.run(
            max_cycles=max_cycles,
            dry_run=dry_run,
            verbose=verbose,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/]")


@app.command()
def status():
    """Show current evolution status."""
    project_root = get_project_root()
    state_file = project_root / "evolution" / "EVOLUTION_STATE.md"

    if not state_file.exists():
        console.print("[red]No state file found.[/] Run [cyan]evolution init[/] first.")
        raise typer.Exit(1)

    content = state_file.read_text()
    console.print(Panel(content, title="Evolution State", border_style="cyan"))


@app.command()
def agents():
    """List running agents."""
    # TODO: Connect to running server to get agent list
    table = Table(title="Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Task", style="white")

    console.print(table)
    console.print("[dim]No agents running. Start with [cyan]evolution start[/][/]")


@app.command()
def version():
    """Show version information."""
    console.print(f"Evolution Suite v{__version__}")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
