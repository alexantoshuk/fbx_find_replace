"""
Windows-only: build a standalone console exe with py2exe.

  py -3.10 -m pip install py2exe
  py -3.10 build_windows.py

Output:
  dist/Windows/fbx_find_replace.exe
"""

import glob
import os
import site
import sys

if sys.platform != "win32":
    sys.exit("build_windows.py is only supported on Windows (uses py2exe).")

import py2exe

site_packages = site.getsitepackages()[0]

data_files = []

# Collect FBX binary module / DLLs if they exist in site-packages
fbx_candidates = []
for dll_dir in site.getsitepackages():
    ffi = os.path.join(dll_dir, "libffi-7.dll")
    if os.path.isfile(ffi):
        fbx_candidates.append(ffi)
    # Some Python installs keep DLLs next to the interpreter
    dlls = os.path.join(os.path.dirname(sys.executable), "DLLs", "libffi-7.dll")
    if os.path.isfile(dlls):
        fbx_candidates.append(dlls)

for pattern in [
    os.path.join(site_packages, "fbx*.pyd"),
    os.path.join(site_packages, "fbx*.dll"),
]:
    fbx_candidates.extend(glob.glob(pattern))

# De-dupe while preserving order
seen = set()
fbx_candidates = [p for p in fbx_candidates if not (p in seen or seen.add(p))]

if fbx_candidates:
    data_files.append((".", fbx_candidates))

dist_dir = os.path.join("dist", "Windows")
os.makedirs(dist_dir, exist_ok=True)

py2exe.freeze(
    console=[{"script": "fbx_find_replace.py", "dest_base": "fbx_find_replace"}],
    options={
        "dist_dir": dist_dir,
        "bundle_files": 0,
        "compressed": True,
        "optimize": 2,
        "includes": ["fbx"],
        "excludes": [
            "tkinter",
            "unittest",
            "email",
            "http",
            "xmlrpc",
            "pydoc",
        ],
    },
    zipfile=None,
    data_files=data_files,
    version_info={
        "version": "1.1.0",
        "product_name": "fbx_find_replace",
    },
)

print(f"Done: {os.path.join(dist_dir, 'fbx_find_replace.exe')}")
