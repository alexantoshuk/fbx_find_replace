# fbx_find_replace

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
