# FBX Find & Replace

Find and replace text in FBX node names, then save to a new file.

Works on **Windows**, **Linux**, and **macOS** (Python 3.10+).

## Requirements

Install Autodesk FBX SDK Python binding for your OS and Python version:

https://aps.autodesk.com/developer/overview/fbx-sdk

Download the **FBX Python SDK** package for your platform, then install the
included wheel, for example:

```bash
# Linux (example; use the wheel name from your download)
pip install ./fbx-*-cp310-*-manylinux*.whl

# Windows (example)
pip install .\fbx-*-cp310-*-win_amd64.whl
```

Verify:

```bash
python -c "import fbx; print('ok')"
```

On Linux you may also need system libraries used by the SDK:

```bash
sudo apt install libxml2 zlib1g   # Debian/Ubuntu
```

## Install this project

From the repo root:

```bash
pip install .
```

Or run the scripts directly without installing:

```bash
python fbx_find_replace.py ...
python fbx_find_replace_gui.py
```

## Examples

    # Plain text replace
    fbx_find_replace input.fbx output.fbx Armature Skeleton

    # Regex replace
    fbx_find_replace input.fbx output.fbx "^L_(.*)$" "Left_\\1" --regex

    # Case-insensitive regex replace
    fbx_find_replace input.fbx output.fbx "mesh_(\\d+)" "geo_\\1" --regex --ignore-case

    # Remove first namespace (omit replacement to delete the match)
    fbx_find_replace input.fbx output.fbx "^[^:]*:" --regex

    # Remove all namespaces
    fbx_find_replace input.fbx output.fbx "^.*:" --regex

    # Preview only
    fbx_find_replace input.fbx output.fbx "Bone" "Joint" --dry-run

## Batch processing with glob patterns

Pass a glob pattern (e.g. `"in/*.fbx"`) as the input to process multiple files
at once. Quote the pattern so the shell does not expand it.

The output controls where each result is written:

- If the output contains `*`, each `*` is replaced (in order) by the text the
  corresponding input `*` matched. For example, `in/*.fbx` -> `out/*.fbx` turns
  `in/hero.fbx` into `out/hero.fbx`.
- If the output has no wildcard, it is treated as a target directory and each
  file keeps its original name.

Examples:

    # Rename in every file, writing renamed copies alongside a mirror layout
    fbx_find_replace "in/*.fbx" "out/*.fbx" Armature Skeleton

    # Add a suffix to each output file name
    fbx_find_replace "models/*.fbx" "models/*_clean.fbx" "Bone" "Joint"

    # Write all results into a directory, keeping original names
    fbx_find_replace "models/*.fbx" cleaned_dir Armature Skeleton

    # Preview a batch run without saving
    fbx_find_replace "in/*.fbx" "out/*.fbx" "Bone" "Joint" --dry-run

## GUI

Run without arguments (or use the `fbx_find_replace_gui` entry point):

```bash
fbx_find_replace_gui
# or
python fbx_find_replace_gui.py
```

Requires Tk (`python3-tk` on Debian/Ubuntu).

## Portable binary (like a Windows .exe)

PyInstaller cannot cross-compile: build the Linux binary **on Linux** (or WSL),
and the Windows `.exe` on Windows. The FBX SDK for that OS must already be
importable (`python -c "import fbx"`).

```bash
pip install pyinstaller
python build_portable.py          # CLI + GUI → dist/
python build_portable.py --cli    # only fbx_find_replace
python build_portable.py --gui    # only fbx_find_replace_gui
```

| Platform | Output |
|----------|--------|
| Windows  | `dist/fbx_find_replace.exe`, `dist/fbx_find_replace_gui.exe` |
| Linux    | `dist/fbx_find_replace`, `dist/fbx_find_replace_gui` |

On Linux, make it executable and run:

```bash
chmod +x dist/fbx_find_replace
./dist/fbx_find_replace input.fbx output.fbx Armature Skeleton
```

The binary is self-contained (Python + script + FBX extension), but may still
need common system libs such as `libxml2` / `zlib`.

**Windows alternative (py2exe, CLI only):**

```bash
pip install py2exe
python build_windows.py
```
