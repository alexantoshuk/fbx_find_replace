# fbx_find_replace

Find and replace text in FBX node names, then save to a new file.

Examples:

    # Plain text replace
    python fbx_find_replace.py input.fbx output.fbx Armature Skeleton

    # Regex replace
    python fbx_find_replace.py input.fbx output.fbx "^L_(.*)$" "Left_\\1" --regex

    # Case-insensitive regex replace
    python fbx_find_replace.py input.fbx output.fbx "mesh_(\\d+)" "geo_\\1" --regex --ignore-case

    # Preview only
    python fbx_find_replace.py input.fbx output.fbx "Bone" "Joint" --dry-run
