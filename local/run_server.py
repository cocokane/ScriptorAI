#!/usr/bin/env python3
"""Run Scriptor Local server directly (dev mode)."""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from scriptor_local import run_server

if __name__ == "__main__":
    print("Starting Scriptor Local server...")
    print("Press Ctrl+C to stop")
    run_server()
