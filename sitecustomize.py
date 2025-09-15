# Automatically ensure local 'src' directory is on sys.path for local executions (tests, python -m ...)
import sys, os
from pathlib import Path
root = Path(__file__).resolve().parent
src = root / 'src'
if src.exists() and str(src) not in sys.path:
    sys.path.insert(0, str(src))
