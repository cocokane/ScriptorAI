#!/usr/bin/env python3
"""Run Scriptor Local as a macOS menu bar app."""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from scriptor_local.menubar import run_menubar

if __name__ == "__main__":
    run_menubar()
