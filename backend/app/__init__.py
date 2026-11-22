"""API de MineSight. El pipeline y sus artefactos se comparten con Streamlit."""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
