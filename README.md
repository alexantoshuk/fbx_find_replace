# FBX Find & Replace

Find and replace text in FBX node names, then save to a new file.

## Requirements:

Install Autodesk FBX SDK Python binding:

https://aps.autodesk.com/developer/overview/fbx-sdk

## Examples:

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
