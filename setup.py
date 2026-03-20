"""
python setup.py py2exe
"""

import glob
import os
import site
from distutils.core import setup

import py2exe

site_packages = site.getsitepackages()[0]

data_files = []

# Try to collect FBX binary module / DLLs if they exist in site-packages
fbx_candidates = ["c:\\Python310\\DLLs\\libffi-7.dll"]
for pattern in [
    os.path.join(site_packages, "fbx*.pyd"),
    os.path.join(site_packages, "fbx*.dll"),
]:
    fbx_candidates.extend(glob.glob(pattern))

if fbx_candidates:
    data_files.append((".", fbx_candidates))

setup(
    name="fbx_find_replace",
    version="1.0.0",
    console=[{"script": "fbx_find_replace.py", "dest_base": "fbx_find_replace"}],
    options={
        "py2exe": {
            "bundle_files": 0,
            "compressed": True,
            "optimize": 2,
            "includes": ["fbx", "re"],
            "excludes": [
                "tkinter",
                "unittest",
                "email",
                "http",
                "xmlrpc",
                "pydoc",
            ],
        }
    },
    zipfile=None,
    data_files=data_files,
)
