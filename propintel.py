#!/usr/bin/env python3
"""
PropIntel CLI Launcher

Quick launcher for the PropIntel command-line interface.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cli.propintel_cli import main

if __name__ == "__main__":
    main()
