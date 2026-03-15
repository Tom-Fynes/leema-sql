"""Command-line interface for Leema SQL IDE."""
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from .app import run as run_app
from .config import LeemaConfig, ConnectionProfile
from .security import SecurityManager
from .drivers import get_available_drivers

app = typer.Typer(
    name="leema",
    help="Leema SQL IDE - Multi-engine TUI SQL client",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Connection profile to use",
    ),
) -> None:
    """Launch the Leema SQL IDE."""
    config_path = str(config) if config else None

    # Load config to check if it exists
    try:
        leema_config = LeemaConfig.load(config_path)

        # Set default profile if specified
        if profile:
            if profile not in leema_config.profiles:
                console.print(
                    f"[red]Error: Profile '{profile}' not found[/red]")
                raise typer.Exit(1)
            leema_config.default_profile = profile

        # Check if we have any profiles
        if not leema_config.profiles:
            console.print(
                "[yellow]No connection profiles found. Run 'leema configure' first.[/yellow]")
            if Confirm.ask("Would you like to configure now?"):
                configure(config)
                return
            else:
                raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[yellow]Configuration file not found.[/yellow]")
        if Confirm.ask("Would you like to create a configuration?"):
            configure(config)
            return
        else:
            raise typer.Exit(1)

    # Launch the app
    run_app(config_path)


@app.command()
def configure(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Interactive configuration wizard."""
    console.print(
        "\n[bold cyan]🔧 Leema SQL IDE Configuration Wizard[/bold cyan]\n")

    config_path = str(config) if config else None

    # Load existing config or create new
    try:
        leema_config = LeemaConfig.load(config_path)
        console.print(
            f"[green]Loaded existing configuration from {leema_config.config_path}[/green]\n")
    except FileNotFoundError:
        leema_config = LeemaConfig()
        console.print("[yellow]Creating new configuration[/yellow]\n")

    # Main menu
    while True:
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print("1. Add new connection profile")
        console.print("2. Edit existing profile")
        console.print("3. Delete profile")
        console.print("4. List profiles")
        console.print("5. Set default profile")
        console.print("6. Save and exit")
        console.print("7. Exit without saving")

        choice = Prompt.ask("Choose an option", choices=[
                            "1", "2", "3", "4", "5", "6", "7"])

        if choice == "1":
            _add_profile_wizard(leema_config)
        elif choice == "2":
            _edit_profile_wizard(leema_config)
        elif choice == "3":
            _delete_profile_wizard(leema_config)
        elif choice == "4":
            _list_profiles(leema_config)
        elif choice == "5":
            _set_default_profile(leema_config)
        elif choice == "6":
            leema_config.save(config_path)
            console.print(
                f"\n[green]✓ Configuration saved to {leema_config.config_path}[/green]")
            break
        elif choice == "7":
            console.print("[yellow]Exiting without saving[/yellow]")
            break


def _add_profile_wizard(config: LeemaConfig) -> None:
    """Add a new connection profile."""
    console.print("\n[bold cyan]Add New Connection Profile[/bold cyan]\n")

    # Show available drivers
    available_drivers = get_available_drivers()
    console.print("[bold]Available database engines:[/bold]")
    for driver_name in available_drivers.keys():
        console.print(f"  • {driver_name}")
    console.print()

    # Collect profile information
    name = Prompt.ask("Profile name")

    if name in config.profiles:
        console.print(f"[red]Profile '{name}' already exists[/red]")
        return

    engine = Prompt.ask(
        "Database engine",
        choices=list(available_drivers.keys()),
        default="postgres"
    )

    host = Prompt.ask("Host", default="localhost")
    port = Prompt.ask("Port", default=_get_default_port(engine))
    database = Prompt.ask("Database name")
    username = Prompt.ask("Username", default="")

    # Password handling
    store_password = Confirm.ask(
        "Store password securely in system keyring?", default=True)

    password = None
    if store_password:
        password = Prompt.ask("Password", password=True)

    # SSL options
    use_ssl = Confirm.ask("Use SSL/TLS?", default=False)
    ssl_config = {}
    if use_ssl:
        ssl_config["sslmode"] = Prompt.ask(
            "SSL mode",
            choices=["require", "verify-ca", "verify-full"],
            default="require"
        )

    # Create profile
    profile = ConnectionProfile(
        name=name,
        engine=engine,
        host=host,
        port=int(port),
        database=database,
        username=username,
        password=None,  # Don't store in config
        ssl=use_ssl,
        options=ssl_config
    )

    config.profiles[name] = profile

    # Store password in keyring
    if store_password and password:
        security = SecurityManager()
        security.set_password(engine, host, username, password)
        console.print(
            "[green]✓ Password stored securely in system keyring[/green]")

    console.print(f"\n[green]✓ Profile '{name}' added successfully[/green]")

    # Set as default if first profile
    if len(config.profiles) == 1:
        config.default_profile = name
        console.print(f"[green]✓ Set '{name}' as default profile[/green]")


def _edit_profile_wizard(config: LeemaConfig) -> None:
    """Edit an existing profile."""
    if not config.profiles:
        console.print("[yellow]No profiles to edit[/yellow]")
        return

    _list_profiles(config)

    name = Prompt.ask("Profile name to edit",
                      choices=list(config.profiles.keys()))
    profile = config.profiles[name]

    console.print(f"\n[bold]Editing profile: {name}[/bold]")
    console.print("(Press Enter to keep current value)\n")

    # Edit fields
    profile.host = Prompt.ask("Host", default=profile.host)
    profile.port = int(Prompt.ask("Port", default=str(profile.port)))
    profile.database = Prompt.ask("Database", default=profile.database)
    profile.username = Prompt.ask("Username", default=profile.username or "")

    if Confirm.ask("Update password?", default=False):
        password = Prompt.ask("New password", password=True)
        security = SecurityManager()
        security.set_password(profile.engine, profile.host,
                              profile.username, password)
        console.print("[green]✓ Password updated[/green]")

    console.print(f"[green]✓ Profile '{name}' updated[/green]")


def _delete_profile_wizard(config: LeemaConfig) -> None:
    """Delete a profile."""
    if not config.profiles:
        console.print("[yellow]No profiles to delete[/yellow]")
        return

    _list_profiles(config)

    name = Prompt.ask("Profile name to delete",
                      choices=list(config.profiles.keys()))

    if Confirm.ask(f"Delete profile '{name}'?", default=False):
        del config.profiles[name]

        # Clear default if it was deleted
        if config.default_profile == name:
            config.default_profile = None

        console.print(f"[green]✓ Profile '{name}' deleted[/green]")


def _list_profiles(config: LeemaConfig) -> None:
    """List all profiles."""
    if not config.profiles:
        console.print("[yellow]No profiles configured[/yellow]")
        return

    table = Table(title="Connection Profiles")
    table.add_column("Name", style="cyan")
    table.add_column("Engine", style="magenta")
    table.add_column("Host", style="green")
    table.add_column("Database", style="yellow")
    table.add_column("Default", style="bold red")

    for name, profile in config.profiles.items():
        is_default = "✓" if name == config.default_profile else ""
        table.add_row(
            name,
            profile.engine,
            f"{profile.host}:{profile.port}",
            profile.database,
            is_default
        )

    console.print(table)


def _set_default_profile(config: LeemaConfig) -> None:
    """Set the default profile."""
    if not config.profiles:
        console.print("[yellow]No profiles configured[/yellow]")
        return

    _list_profiles(config)

    name = Prompt.ask("Set default profile",
                      choices=list(config.profiles.keys()))
    config.default_profile = name
    console.print(f"[green]✓ Default profile set to '{name}'[/green]")


def _get_default_port(engine: str) -> str:
    """Get default port for database engine."""
    ports = {
        "postgres": "5432",
        "mysql": "3306",
        "mssql": "1433",
        "trino": "8080",
        "snowflake": "443",
        "duckdb": "0",
    }
    return ports.get(engine, "5432")


@app.command()
def list_drivers() -> None:
    """List available database drivers."""
    drivers = get_available_drivers()

    console.print("\n[bold cyan]Available Database Drivers[/bold cyan]\n")

    for driver_name in sorted(drivers.keys()):
        console.print(f"  [green]✓[/green] {driver_name}")

    console.print(f"\n[dim]Total: {len(drivers)} drivers available[/dim]\n")


@app.command()
def version() -> None:
    """Show version information."""
    console.print("\n[bold cyan]Leema SQL IDE[/bold cyan]")
    console.print("Version: 1.0.0")
    console.print("Python: 3.12+")
    console.print(
        "\n[dim]A multi-engine TUI SQL development environment[/dim]\n")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
