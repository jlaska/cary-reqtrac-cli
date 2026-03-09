#!/usr/bin/env python3
"""
Cary ReqTrac CLI - Standalone entry point

kubectl-style CLI for interacting with the Cary ReqTrac recreation program registration system.
"""

import sys
from pathlib import Path

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cli.main import main

if __name__ == '__main__':
    main()
