#!/usr/bin/env python3
"""
Build portable one-file binaries with PyInstaller (Windows / Linux / macOS).

Prerequisites:
  pip install pyinstaller
  # plus Autodesk FBX Python SDK so `import fbx` works

Usage:
  python build_portable.py          # CLI + GUI
  python build_portable.py --cli    # CLI only
  python build_portable.py --gui    # GUI only

Outputs land in dist/:
  dist/fbx_find_replace[.exe]
  dist/fbx_find_replace_gui[.exe]
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import os
import site
import sys


def _site_dirs():
    dirs = []
    try:
        dirs.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        user = site.getusersitepackages()
        if user:
            dirs.append(user)
    except Exception:
        pass
    # venv
    if sys.prefix not in dirs:
        dirs.append(os.path.join(sys.prefix, "Lib", "site-packages"))
        dirs.append(os.path.join(sys.prefix, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"))
    return [d for d in dirs if d and os.path.isdir(d)]


def collect_fbx_artifacts():
    """Return (binaries, datas) tuples for PyInstaller: list of (src, dest_dir)."""
    spec = importlib.util.find_spec("fbx")
    if spec is None or not spec.origin:
        sys.exit(
            "Error: cannot import 'fbx'. Install Autodesk FBX Python SDK first,\n"
            "then re-run this script with the same Python interpreter."
        )

    binaries = []
    datas = []
    origin = os.path.abspath(spec.origin)
    root = os.path.dirname(origin)

    def add_binary(path):
        path = os.path.abspath(path)
        entry = (path, ".")
        if entry not in binaries and os.path.isfile(path):
            binaries.append(entry)

    def add_data(path):
        path = os.path.abspath(path)
        entry = (path, ".")
        if entry not in datas and os.path.isfile(path):
            datas.append(entry)

    if origin.endswith((".pyd", ".so", ".dll")) or ".so." in os.path.basename(origin):
        add_binary(origin)
    elif origin.endswith(".py"):
        add_data(origin)

    patterns = [
        "fbx*.pyd",
        "fbx*.dll",
        "fbx*.so",
        "fbx*.so.*",
        "libfbxsdk*",
        "FbxCommon.py",
        "fbx.py",
    ]
    search_roots = [root] + _site_dirs()
    for search_root in search_roots:
        for pattern in patterns:
            for path in glob.glob(os.path.join(search_root, pattern)):
                if path.endswith(".py"):
                    add_data(path)
                else:
                    add_binary(path)

    print(f"fbx module: {origin}")
    for src, _ in binaries:
        print(f"  binary: {src}")
    for src, _ in datas:
        print(f"  data:   {src}")
    return binaries, datas


def build(name: str, script: str, binaries, datas) -> None:
    # Import here so --help works without PyInstaller installed.
    import PyInstaller.__main__

    args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        name,
        "--hidden-import",
        "fbx",
    ]
    for src, dest in binaries:
        args.extend(["--add-binary", f"{src}{os.pathsep}{dest}"])
    for src, dest in datas:
        args.extend(["--add-data", f"{src}{os.pathsep}{dest}"])
    args.append(script)

    print("\nRunning:", " ".join(args))
    PyInstaller.__main__.run(args)


def main():
    parser = argparse.ArgumentParser(description="Build portable fbx_find_replace binaries")
    parser.add_argument("--cli", action="store_true", help="Build CLI only")
    parser.add_argument("--gui", action="store_true", help="Build GUI only")
    args = parser.parse_args()

    if args.cli or args.gui:
        build_cli = args.cli
        build_gui = args.gui
    else:
        build_cli = True
        build_gui = True

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("Error: PyInstaller is not installed. Run: pip install pyinstaller")

    binaries, datas = collect_fbx_artifacts()
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    if build_cli:
        build("fbx_find_replace", "fbx_find_replace.py", binaries, datas)
    if build_gui:
        build("fbx_find_replace_gui", "fbx_find_replace_gui.py", binaries, datas)

    ext = ".exe" if sys.platform == "win32" else ""
    print("\nDone. Portable binaries:")
    if build_cli:
        print(f"  {os.path.join(root, 'dist', 'fbx_find_replace' + ext)}")
    if build_gui:
        print(f"  {os.path.join(root, 'dist', 'fbx_find_replace_gui' + ext)}")
    if sys.platform.startswith("linux"):
        print(
            "\nOn the target Linux machine you may still need system libs, e.g.:\n"
            "  sudo apt install libxml2 zlib1g\n"
            "Make the binary executable: chmod +x dist/fbx_find_replace"
        )


if __name__ == "__main__":
    main()
