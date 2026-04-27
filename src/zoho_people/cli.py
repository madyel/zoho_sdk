"""
CLI entrypoint for zoho-people-sdk.

Invoke as: zoho-people <command> [options]
Or:        python -m zoho_people <command> [options]

For the full interactive menu run without arguments.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Delegate to the top-level main.py CLI."""
    cli_path = Path(__file__).parent.parent / "main.py"
    if not cli_path.exists():
        print("main.py not found. Run from the project root.", file=sys.stderr)
        sys.exit(1)

    import runpy
    sys.argv[0] = str(cli_path)
    runpy.run_path(str(cli_path), run_name="__main__")


if __name__ == "__main__":
    main()
