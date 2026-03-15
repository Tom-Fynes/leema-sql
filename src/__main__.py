"""Entry point for running Leema SQL IDE as a module."""

from src.app import LeemaApp


def main():
    """Run the Leema SQL IDE application."""
    app = LeemaApp()
    app.run()


if __name__ == "__main__":
    main()
