#!/usr/bin/env bash
# Locate / install Autodesk FBX Python SDK on macOS from a downloaded package dir.
# Accepts a directory containing any of: *.whl, *.pkg, *.tar.gz, *.tgz, *.zip
#
# Usage:
#   bash ci/install_fbx_macos.sh sdk              # find + pip install
#   bash ci/install_fbx_macos.sh sdk --find-only  # print path + python version only
set -euo pipefail

SDK_DIR=${1:-sdk}
FIND_ONLY=0
if [[ "${2:-}" == "--find-only" ]]; then
  FIND_ONLY=1
fi

if [[ ! -d "$SDK_DIR" ]]; then
  echo "SDK directory not found: $SDK_DIR" >&2
  exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

find_whl() {
  find "$1" -type f \( -name 'fbx-*-macosx*.whl' -o -name 'fbx-*macosx*.whl' \) 2>/dev/null | head -n 1
}

# Unpack archives into work/
while IFS= read -r -d '' archive; do
  case "$archive" in
    *.tar.gz|*.tgz)
      tar -xzf "$archive" -C "$work" 2>/dev/null || true
      ;;
    *.zip)
      unzip -q "$archive" -d "$work" 2>/dev/null || true
      ;;
  esac
done < <(find "$SDK_DIR" -maxdepth 3 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) -print0 2>/dev/null)

find "$SDK_DIR" -maxdepth 4 -type f \( -name '*.whl' -o -name '*.pkg' \) -print0 2>/dev/null |
  while IFS= read -r -d '' f; do
    cp -f "$f" "$work/" 2>/dev/null || true
  done

# Also copy oddly named downloads
for f in "$SDK_DIR"/*; do
  [[ -f "$f" ]] || continue
  cp -f "$f" "$work/" 2>/dev/null || true
done

WHL=$(find_whl "$work")
if [[ -z "$WHL" ]]; then
  WHL=$(find_whl "$SDK_DIR")
fi

if [[ -z "$WHL" ]]; then
  while IFS= read -r -d '' pkg; do
    echo "Expanding $(basename "$pkg")..." >&2
    expand_dir="$work/$(basename "$pkg").expand"
    mkdir -p "$expand_dir"
    if pkgutil --expand "$pkg" "$expand_dir/root" 2>/dev/null; then
      :
    else
      mkdir -p "$expand_dir/xar"
      (cd "$expand_dir/xar" && xar -xf "$pkg") 2>/dev/null || true
    fi
    while IFS= read -r -d '' payload; do
      payload_out=$(dirname "$payload")/payload_out
      mkdir -p "$payload_out"
      if gzip -t "$payload" 2>/dev/null; then
        (cd "$payload_out" && gzip -dc < "$payload" | cpio -id 2>/dev/null) || true
      else
        (cd "$payload_out" && cpio -id < "$payload" 2>/dev/null) || true
      fi
    done < <(find "$expand_dir" -type f -name 'Payload' -print0 2>/dev/null)
  done < <(find "$work" "$SDK_DIR" -type f -name '*.pkg' -print0 2>/dev/null)

  WHL=$(find_whl "$work")
  if [[ -z "$WHL" ]]; then
    WHL=$(find "$work" "$SDK_DIR" -type f -name 'fbx-*.whl' 2>/dev/null | head -n 1)
  fi
fi

if [[ -z "$WHL" ]]; then
  echo "Could not find an FBX macOS wheel under $SDK_DIR" >&2
  echo "Contents:" >&2
  find "$SDK_DIR" -maxdepth 4 -type f >&2 || true
  exit 1
fi

echo "Found wheel: $WHL" >&2
base=$(basename "$WHL")
PYVER=""
if [[ "$base" =~ cp([0-9])([0-9]+) ]]; then
  PYVER="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
  echo "PYTHON_VERSION=$PYVER" >&2
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "python_version=$PYVER" >> "$GITHUB_OUTPUT"
    echo "wheel_path=$WHL" >> "$GITHUB_OUTPUT"
  fi
fi

# Persist wheel where the workflow can find it after --find-only
mkdir -p "$SDK_DIR/resolved"
cp -f "$WHL" "$SDK_DIR/resolved/$(basename "$WHL")"
echo "$SDK_DIR/resolved/$(basename "$WHL")"

if [[ "$FIND_ONLY" -eq 1 ]]; then
  exit 0
fi

python3 -m pip install --upgrade pip
python3 -m pip install "$WHL"
python3 -c "import fbx; print('fbx ok:', fbx.__file__)"
