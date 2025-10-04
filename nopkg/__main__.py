"""Allow nopkg to be run as a module with python -m nopkg."""

from .cli import cli

if __name__ == "__main__":
    cli()