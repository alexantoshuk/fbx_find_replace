#!/usr/bin/env python3

import argparse
import glob
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
    os.makedirs(out_dir, exist_ok=True)

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


def glob_to_capture_regex(pattern):
    """Translate a glob pattern into a regex whose groups capture each
    wildcard's matched text. Returns (compiled_regex, wildcard_count)."""
    pattern = os.path.normpath(pattern)
    out = []
    wildcard_count = 0
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            out.append("(.*)")
            wildcard_count += 1
            i += 1
        elif c == "?":
            out.append("(.)")
            wildcard_count += 1
            i += 1
        elif c == "[":
            j = i + 1
            if j < n and pattern[j] == "!":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:
                out.append(re.escape(c))
                i += 1
            else:
                stuff = pattern[i + 1 : j]
                if stuff.startswith("!"):
                    stuff = "^" + stuff[1:]
                out.append("([" + stuff + "])")
                wildcard_count += 1
                i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    regex = re.compile("^" + "".join(out) + "$", re.IGNORECASE)
    return regex, wildcard_count


def substitute_output_wildcards(output_pattern, captures):
    """Replace each '*' in the output pattern with the next captured wildcard
    text from the matched input path, in order."""
    result = []
    idx = 0
    for c in output_pattern:
        if c == "*":
            if idx < len(captures):
                result.append(captures[idx])
                idx += 1
            else:
                result.append("*")
        else:
            result.append(c)
    return "".join(result)


def resolve_output_path(input_path, input_pattern, output_pattern):
    """Compute the output path for a single matched input file."""
    if glob.has_magic(output_pattern):
        regex, _ = glob_to_capture_regex(input_pattern)
        match = regex.match(os.path.normpath(input_path))
        captures = list(match.groups()) if match else []
        return substitute_output_wildcards(output_pattern, captures)
    # No wildcard in output: treat it as a target directory.
    return os.path.join(output_pattern, os.path.basename(input_path))


def process_file(input_path, output_path, args):
    """Run find/replace on a single FBX file. Returns True on success."""
    manager = None
    try:
        manager, scene = create_sdk_objects()
        is_ascii = load_scene(manager, scene, input_path)
        print(f"\n=== {input_path} -> {output_path} ===")
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
            save_scene(manager, scene, output_path, is_ascii)
            print(f"Saved: {output_path}")
        else:
            print("Dry run only; nothing saved.")

        return True

    except Exception as exc:
        print(f"Error processing {input_path}: {exc}", file=sys.stderr)
        return False

    finally:
        if manager is not None:
            manager.Destroy()


def main():
    # print( sys.argv)
    if not sys.argv[1:]:
        gui()
        return 0
    run()

def run():
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

    # Remove first namespace (omit replacement to delete the match)
    fbx_find_replace input.fbx output.fbx "^[^:]*:" --regex

    # Remove all namespaces
    fbx_find_replace input.fbx output.fbx "^.*:" --regex

    # Preview only
    fbx_find_replace input.fbx output.fbx "Bone" "Joint" --dry-run

    # Batch: process every .fbx, writing renamed copies (the output '*'
    # is replaced by the text matched by the input '*')
    fbx_find_replace "in/*.fbx" "out/*.fbx" Armature Skeleton

    # Batch into a directory (output has no wildcard, original names kept)
    fbx_find_replace "in/*.fbx" out_dir Armature Skeleton
""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Input FBX file, or a glob pattern (e.g. \"in/*.fbx\") for batch mode",
    )
    parser.add_argument(
        "output",
        help=(
            "Output FBX file. In batch mode, use a pattern with '*' (replaced by "
            "each input's matched text) or a target directory"
        ),
    )
    parser.add_argument("find", help="Text or regex pattern to find")
    parser.add_argument(
        "replace",
        nargs="?",
        default="",
        help="Replacement text (defaults to an empty string, i.e. delete the match)",
    )
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

    if args.find == "":
        print("Error: find text/pattern must not be empty", file=sys.stderr)
        return 1

    if args.regex:
        try:
            re.compile(args.find, re.IGNORECASE if args.ignore_case else 0)
        except re.error as exc:
            print(f"Error: invalid regex pattern: {exc}", file=sys.stderr)
            return 1

    if glob.has_magic(args.input):
        input_files = sorted(f for f in glob.glob(args.input) if os.path.isfile(f))
        if not input_files:
            print(
                f"Error: no files match input pattern: {args.input}", file=sys.stderr
            )
            return 1
    else:
        if not os.path.isfile(args.input):
            print(f"Error: input file does not exist: {args.input}", file=sys.stderr)
            return 1
        input_files = [args.input]

    is_batch = glob.has_magic(args.input) or len(input_files) > 1
    if is_batch:
        print(f"Batch mode: {len(input_files)} file(s) matched.")

    failures = 0
    for input_path in input_files:
        if is_batch:
            output_path = resolve_output_path(input_path, args.input, args.output)
        else:
            output_path = args.output
        if not process_file(input_path, output_path, args):
            failures += 1

    if is_batch:
        print(
            f"\nDone: {len(input_files) - failures} succeeded, {failures} failed."
        )

    return 1 if failures else 0


def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    class FileFolderDialog:
        def __init__(self, root):
            self.root = root
            self.root.title("Search and replace node names in FBX file(s)")
            self.root.geometry("460x260")
            self.root.resizable(True, False)

            # Variables for storing values
            self.path_var = tk.StringVar()
            self.from_var = tk.StringVar()
            self.to_var = tk.StringVar()
            self.selection_type = tk.StringVar(value="files")  # 'file', 'files', or 'folder'

            self.create_widgets()

        def create_widgets(self):
            # Main frame
            main_frame = ttk.Frame(self.root, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            main_frame.columnconfigure(0, weight=1)  # Path entry expands
            main_frame.columnconfigure(1, weight=0)  # Browse button stays fixed
            main_frame.columnconfigure(2, weight=0)
            # First field - file or folder path
            ttk.Label(main_frame, text="Path to FBX file(s) or folder:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

            # Radio buttons for selection type
            type_frame = ttk.Frame(main_frame)
            type_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

            ttk.Radiobutton(type_frame, text="File(s)", variable=self.selection_type,
                           value="files").pack(side=tk.LEFT, padx=(0, 10))
            ttk.Radiobutton(type_frame, text="Folder", variable=self.selection_type,
                           value="folder").pack(side=tk.LEFT)

            # Path input field
            path_frame = ttk.Frame(main_frame)
            path_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
            path_frame.columnconfigure(0, weight=1)

            self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
            self.path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

            browse_btn = ttk.Button(path_frame, text="Browse...", command=self.browse_with_type)
            browse_btn.grid(row=0, column=1)

            # Info label showing number of selected files
            self.info_label = ttk.Label(main_frame, text="File name can be a glob pattern and supports wildcards (*, ?)", foreground="gray")
            self.info_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

            # Second section - "From" and "To" with labels above
            options_frame = ttk.Frame(main_frame)
            options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
            options_frame.columnconfigure(0, weight=1)  # From column
            options_frame.columnconfigure(1, weight=1)  # To column

            # "From" field with label above
            from_frame = ttk.Frame(options_frame)
            from_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
            from_frame.columnconfigure(0, weight=1)

            ttk.Label(from_frame, text="From:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

            self.options_regexp = [
                r"^.*:",
                r"^[^:]*:",
                r"myMesh_(\d+)",
                r"myMesh_(.*)$",
                r"(.*)_Left$",
            ]

            self.options = [
                'All namespaces',
                "First Namespace",
                "Name with any numeric suffix",
                "Name with any suffix",
                "Name with any prefix",
            ]

            self.options_map = {k:v for k,v in zip(self.options, self.options_regexp)}

            self.from_combo = ttk.Combobox(
                from_frame,
                textvariable=self.from_var,
                values=self.options,
                state="normal",  # Editable mode - user can type custom text
                width=30
            )
            self.from_combo.grid(row=1, column=0, sticky=(tk.W, tk.E))
            self.from_combo.set("")  # Empty by default

            # "To" field with label above
            to_frame = ttk.Frame(options_frame)
            to_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
            to_frame.columnconfigure(0, weight=1)

            ttk.Label(to_frame, text="To:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))


            self.to_combo = ttk.Combobox(
                to_frame,
                textvariable=self.to_var,
                values=self.options,
                state="normal",  # Editable mode - user can type custom text
                width=30
            )
            self.to_combo.grid(row=1, column=0, sticky=(tk.W, tk.E))
            self.to_combo.set("")  # Empty by default

            # Bind selection events (optional)
            self.from_combo.bind('<<ComboboxSelected>>', self.on_from_selected)
            self.to_combo.bind('<<ComboboxSelected>>', self.on_to_selected)

            # OK and Cancel buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))

            ok_btn = ttk.Button(button_frame, text="OK", command=self.on_ok, width=10)
            ok_btn.pack(side=tk.LEFT, padx=(0, 10))

            cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.on_cancel, width=10)
            cancel_btn.pack(side=tk.LEFT)

            # Keyboard shortcuts
            self.root.bind('<Return>', lambda event: self.on_ok())  # Enter key
            self.root.bind('<Escape>', lambda event: self.on_cancel())  # Escape key

        def on_from_selected(self, event):
            """Triggered when an option is selected from the 'From' dropdown"""
            selected = self.from_var.get()
            val = self.options_map[selected]
            self.from_var.set(val)


        def on_to_selected(self, event):
            """Triggered when an option is selected from the 'To' dropdown"""
            selected = self.to_var.get()
            val = self.options_map[selected]
            self.to_var.set(val)


        def browse_with_type(self):
            """Browse for file(s) or folder based on selected radio button"""
            selection_type = self.selection_type.get()

            if selection_type == "files":
                # Multiple files selection
                paths = filedialog.askopenfilenames(
                    title="Select FBX file(s)",
                    filetypes=[
                        ("FBX files", "*.fbx *.FBX"),
                    ]
                )
                if paths:
                    # Join paths with semicolon for display
                    path_str = "; ".join(paths)
                    self.path_var.set(path_str.replace("\\", "/"))

            else:  # folder
                # Folder selection
                path = filedialog.askdirectory(
                    title="Select a folder containing FBX files",
                    mustexist=True
                )
                if path:
                    self.path_var.set(path.replace("\\", "/") + "/*.fbx" )


        def on_ok(self):
            """OK button handler"""
            path = self.path_var.get().strip()
            from_text = self.from_var.get().strip()
            to_text = self.to_var.get().strip()
            selection_type = self.selection_type.get()

            # Validation
            if not path:
                messagebox.showwarning("Warning", "Please select a file, files, or folder!")
                return

            for p in path.split(";"):
                p = p.strip()
                if not p:
                    continue
                sys.argv = sys.argv[:1]
                sys.argv.append(p)
                sys.argv.append(p)
                sys.argv.append(from_text)
                sys.argv.append(to_text)
                sys.argv.append("--regex")

                run()

            # Close the dialog
            self.root.destroy()
            input("Press Enter to continue...")

        def on_cancel(self):
            """Cancel button handler"""
            self.root.destroy()
            return

        def get_values(self):
            """Method to retrieve values from the dialog"""
            path = self.path_var.get().strip()
            selection_type = self.selection_type.get()

            # Parse paths for multiple files
            if selection_type == "files":
                paths = [p.strip() for p in path.split(";") if p.strip()]
            else:
                paths = [path] if path else []

            return {
                'type': selection_type,
                'path': path,
                'paths': paths,  # List of individual paths (useful for multiple files)
                'from': self.from_var.get().strip(),
                'to': self.to_var.get().strip()
            }


    root = tk.Tk()
    app = FileFolderDialog(root)
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
