#!/usr/bin/env python3
"""GitHub Roast & Rescue — CLI entry point.

Launches the Neo-Brutalist web dashboard or prints system status.

Usage:
    python main.py              # Start web server on port 8080
    python main.py --port 9090  # Custom port
    python main.py --status     # Print system health
"""

import argparse
import server


def main():
    """Parse arguments and launch the server or print status."""
    parser = argparse.ArgumentParser(
        description="GitHub Roast & Rescue — Brutally honest profile feedback"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind (default: $PORT or 8080)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print system status and exit",
    )
    args = parser.parse_args()

    if args.status:
        print("\n⚡ SYSTEM STATUS: ACTIVE ⚡")
        print("Neo-Brutalist Dashboard ready.")
        print("Stack: Python · GitHub REST API · Google Cloud Run\n")
        return

    server.run_server(port=args.port)


if __name__ == "__main__":
    main()