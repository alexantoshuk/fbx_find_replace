#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import sys
import tempfile

import fbx


def create_sdk_objects():
    manager = fbx.FbxManager.Create()
    if not manager:
        raise RuntimeError("Failed to create FbxManager")

    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ios)

    scene = fbx.FbxScene.Create(manager, "Scene")
    if not scene:
        manager.Destroy()
        raise RuntimeError("Failed to create FbxScene")

    return manager, scene


def load_scene(manager, scene, filename):
    FBX_BINARY_MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
    with open(filename, "rb") as f:
        is_ascii = f.read(len(FBX_BINARY_MAGIC)) != FBX_BINARY_MAGIC

    importer = fbx.FbxImporter.Create(manager, "")
    try:
        if not importer.Initialize(filename, -1, manager.GetIOSettings()):
            raise RuntimeError(
                f"FBX importer init failed: {importer.GetStatus().GetErrorString()}"
            )
        if not importer.Import(scene):
            raise RuntimeError(
                f"FBX import failed: {importer.GetStatus().GetErrorString()}"
            )
    finally:
        importer.Destroy()

    return is_ascii


def save_scene(manager, scene, filename, is_ascii=False):
    out_dir = os.path.dirname(os.path.abspath(filename))
    if not os.path.isdir(out_dir):
        raise RuntimeError(f"Output directory does not exist: {out_dir}")

    if is_ascii:
        registry = manager.GetIOPluginRegistry()
        format_index = -1
        for i in range(registry.GetWriterFormatCount()):
            if (
                registry.WriterIsFBX(i)
                and "ascii" in registry.GetWriterFormatDescription(i).lower()
            ):
                format_index = i
                break
    else:
        format_index = -1

    # FBX SDK's C++ layer cannot write to paths with spaces (e.g. network
    # drives like "P:\Shared drives\..."). Write to a local temp file first,
    # then move it to the real destination with Python's shutil.
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".fbx")
    os.close(tmp_fd)
    try:
        exporter = fbx.FbxExporter.Create(manager, "")
        try:
            if not exporter.Initialize(tmp_path, format_index, manager.GetIOSettings()):
                raise RuntimeError(
                    f"FBX exporter init failed: {exporter.GetStatus().GetErrorString()}"
                )
            if not exporter.Export(scene):
                raise RuntimeError(
                    f"FBX export failed: {exporter.GetStatus().GetErrorString()}"
                )
        finally:
            exporter.Destroy()

        shutil.move(tmp_path, filename)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def plain_replace(name, find_text, replace_text, ignore_case=False):
    if not ignore_case:
        new_name = name.replace(find_text, replace_text)
        count = name.count(find_text)
        return new_name, count

    lower_name = name.lower()
    lower_find = find_text.lower()

    if lower_find == "":
        return name, 0

    result = []
    count = 0
    i = 0
    step = len(find_text)

    while i < len(name):
        if lower_name[i : i + step] == lower_find:
            result.append(replace_text)
            count += 1
            i += step
        else:
            result.append(name[i])
            i += 1

    return "".join(result), count


def regex_replace(name, pattern, replace_text, ignore_case=False):
    flags = re.IGNORECASE if ignore_case else 0
    compiled = re.compile(pattern, flags)
    new_name, count = compiled.subn(replace_text, name)
    return new_name, count


def rename_object(obj, find_text, replace_text, ignore_case, use_regex, changes):
    old_name = obj.GetName()
    if use_regex:
        new_name, replace_count = regex_replace(
            old_name, find_text, replace_text, ignore_case=ignore_case
        )
    else:
        new_name, replace_count = plain_replace(
            old_name, find_text, replace_text, ignore_case=ignore_case
        )
    if new_name != old_name:
        obj.SetName(new_name)
        changes.append(
            {"old_name": old_name, "new_name": new_name, "replacements": replace_count}
        )


def process_all_objects(
    scene, find_text, replace_text, ignore_case=False, use_regex=False
):
    """Rename every object in the scene regardless of type."""
    changes = []
    for i in range(scene.GetSrcObjectCount()):
        obj = scene.GetSrcObject(i)
        rename_object(obj, find_text, replace_text, ignore_case, use_regex, changes)
    return changes


def main():
    parser = argparse.ArgumentParser(
        description="""
Find and replace text in FBX node names, then save to a new file.

Examples:

    # Plain text replace
    fbx_find_replace input.fbx output.fbx Armature Skeleton

    # Regex replace
    fbx_find_replace input.fbx output.fbx "^L_(.*)$" "Left_\\1" --regex

    # Case-insensitive regex replace
    fbx_find_replace input.fbx output.fbx "mesh_(\\d+)" "geo_\\1" --regex --ignore-case

    # Remove first namespace
    fbx_find_replace input.fbx output.fbx "^[^:]*:" "" --regex

    # Remove all namespaces
    fbx_find_replace input.fbx output.fbx "^.*:" "" --regex

    # Preview only
    fbx_find_replace input.fbx output.fbx "Bone" "Joint" --dry-run
""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input", help="Input FBX file")
    parser.add_argument("output", help="Output FBX file")
    parser.add_argument("find", help="Text or regex pattern to find")
    parser.add_argument("replace", help="Replacement text")
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Case-insensitive replacement",
    )
    parser.add_argument(
        "--regex",
        action="store_true",
        help="Treat 'find' as a regular expression",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not save; only print changes",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: input file does not exist: {args.input}", file=sys.stderr)
        return 1

    if args.find == "":
        print("Error: find text/pattern must not be empty", file=sys.stderr)
        return 1

    if args.regex:
        try:
            re.compile(args.find, re.IGNORECASE if args.ignore_case else 0)
        except re.error as exc:
            print(f"Error: invalid regex pattern: {exc}", file=sys.stderr)
            return 1

    manager = None
    try:
        manager, scene = create_sdk_objects()
        is_ascii = load_scene(manager, scene, args.input)
        print(f"Source format: {'ASCII' if is_ascii else 'Binary'} FBX")

        changes = process_all_objects(
            scene,
            args.find,
            args.replace,
            ignore_case=args.ignore_case,
            use_regex=args.regex,
        )

        if changes:
            total_replacements = sum(item["replacements"] for item in changes)
            print(
                f"Changed {len(changes)} name(s), "
                f"{total_replacements} replacement(s) total:"
            )
            for item in changes:
                print(
                    f'  "{item["old_name"]}" -> "{item["new_name"]}" '
                    f"({item['replacements']} replacement(s))"
                )
        else:
            print("No names matched.")

        if not args.dry_run:
            save_scene(manager, scene, args.output, is_ascii)
            print(f"Saved: {args.output}")
        else:
            print("Dry run only; nothing saved.")

        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    finally:
        if manager is not None:
            manager.Destroy()


if __name__ == "__main__":
    sys.exit(main())
