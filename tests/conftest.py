"""
pytest configuration for kuromi-browser tests.
"""

import sys
from pathlib import Path

# Add kuromi_browser to path
sys.path.insert(0, str(Path(__file__).parent.parent))
