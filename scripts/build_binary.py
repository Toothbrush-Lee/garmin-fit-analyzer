#!/usr/bin/env python3
"""Build a standalone executable for the FIT analyzer."""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a standalone fit-analyzer executable.")
    parser.add_argument(
        "--name",
        default="fit-analyzer",
        help="Executable name. Windows will add .exe automatically.",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build a directory bundle instead of a single executable file.",
    )
    parser.add_argument(
        "--distpath",
        type=Path,
        default=Path("dist"),
        help="Directory where the executable is written.",
    )
    parser.add_argument(
        "--workpath",
        type=Path,
        default=Path("build/pyinstaller"),
        help="Directory for temporary PyInstaller build files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    entrypoint = project_root / "src" / "garmin_fit_analyzer" / "cli.py"
    distpath = (project_root / args.distpath).resolve()
    workpath = (project_root / args.workpath).resolve()
    specpath = workpath / "spec"
    os.environ.setdefault("PYINSTALLER_CONFIG_DIR", str(workpath / "pyinstaller-config"))

    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError:
        print(
            "PyInstaller is not installed. Run:\n"
            "  uv run --group build python scripts/build_binary.py",
            file=sys.stderr,
        )
        raise SystemExit(2) from None

    pyinstaller_args = [
        str(entrypoint),
        "--name",
        args.name,
        "--distpath",
        str(distpath),
        "--workpath",
        str(workpath),
        "--specpath",
        str(specpath),
        "--clean",
        "--noconfirm",
        "--collect-data",
        "tzdata",
    ]
    pyinstaller_args.append("--onedir" if args.onedir else "--onefile")

    print(f"Building {args.name} for {platform.system()} {platform.machine()}...")
    pyinstaller.run(pyinstaller_args)
    print(f"Build complete. See: {distpath}")


if __name__ == "__main__":
    main()
