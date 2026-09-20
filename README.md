# FBX Find & Replace

Find and replace text in FBX node names, then save to a new file.

Works on **Windows**, **Linux**, and **macOS** (Python 3.10+; Autodesk’s current
FBX Python wheels are often **3.11** — match the wheel’s `cp3xx` tag).

## Requirements

Install Autodesk FBX SDK Python binding for your OS and Python version:

https://aps.autodesk.com/developer/overview/fbx-sdk

Download the **FBX Python SDK** package for your platform, then install the
included wheel, for example:

```bash
# Linux
pip install ./fbx-*-cp311-*-manylinux*.whl

# macOS
pip install ./fbx-*-cp311-*-macosx*.whl

# Windows
pip install .\fbx-*-cp311-*-win_amd64.whl
```

Verify:

```bash
python -c "import fbx; print('ok')"
```

System libraries (CLI):

```bash
# Debian/Ubuntu
sudo apt install libxml2 zlib1g

# Fedora
sudo dnf install libxml2 zlib

# macOS — usually already present; if import fails:
brew install libxml2
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

PyInstaller **cannot cross-compile**. Build on the same OS (and CPU arch) you
target:

| Build machine | Output |
|---------------|--------|
| Windows       | `dist/fbx_find_replace.exe` |
| Linux         | `dist/fbx_find_replace` |
| macOS         | `dist/fbx_find_replace` |

The FBX SDK for that OS must already be importable (`python -c "import fbx"`).

```bash
pip install pyinstaller
python build_portable.py --cli    # recommended (CLI only)
python build_portable.py          # CLI; GUI only if tkinter works
python build_portable.py --gui    # GUI only (optional)
```

### Linux

```bash
chmod +x dist/fbx_find_replace
./dist/fbx_find_replace input.fbx output.fbx Armature Skeleton
```

May still need `libxml2` / `zlib`. A binary built on Ubuntu 22.04 (glibc 2.35)
usually runs on Fedora with equal or newer glibc.

### No Mac? Build with GitHub Actions

You do not need a Mac. A hosted `macos-14` runner builds the CLI binary using
the private SDK repo [`alexantoshuk/mac_fbx_sdk`](https://github.com/alexantoshuk/mac_fbx_sdk).

1. Download **FBX Python SDK for macOS** from Autodesk (on Windows is fine).
2. Upload it to a release on the private repo (tag `fbx-sdk`):

```bash
gh release create fbx-sdk ./path/to/fbx*_macos* \
  --repo alexantoshuk/mac_fbx_sdk \
  --title "FBX Python SDK macOS" \
  --notes "CI only"
```

3. In `fbx_find_replace`: secret `MAC_FBX_SDK_TOKEN` = GitHub PAT with read
   access to `mac_fbx_sdk` (already set if you used the setup helper).
4. **Actions → Build macOS portable → Run workflow**
5. Download artifact `fbx_find_replace-macos-arm64`
   (optionally enable Intel for `…-x86_64`).

On the Mac that will run it:

```bash
chmod +x fbx_find_replace
xattr -dr com.apple.quarantine fbx_find_replace
./fbx_find_replace input.fbx output.fbx Armature Skeleton
```


### Windows alternative (py2exe, CLI only)

```bash
pip install py2exe
python build_windows.py
```
