"""
Make exe
c:/Python310/python.exe -m pip install pyinstaller
c:/Python310/python.exe -m PyInstaller --onefile --console --name fbx_find_replace_gui fbx_find_replace_gui.py
"""
import sys
import fbx_find_replace

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

                fbx_find_replace.run()

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


def main():
    # print( sys.argv)
    if not sys.argv[1:]:
        gui()
        return 0
    fbx_find_replace.run()

if __name__ == "__main__":
    sys.exit(main())
