"""Compatibility wrapper for the packaged CLI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin_fit_analyzer.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
