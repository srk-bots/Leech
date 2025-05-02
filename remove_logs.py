#!/usr/bin/env python3
import os
import re


def process_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Count original occurrences for reporting
    debug_count = len(re.findall(r"LOGGER\.debug\(", content))
    warning_count = len(re.findall(r"LOGGER\.warning\(", content))

    if debug_count == 0 and warning_count == 0:
        return 0, 0  # No changes needed

    # Pattern for single-line debug/warning logs
    content = re.sub(
        r"(\s*)LOGGER\.(debug|warning)\(.*?\)(\s*)", r"\1pass\3", content
    )

    # Pattern for multi-line debug/warning logs
    content = re.sub(
        r"(\s*)LOGGER\.(debug|warning)\([\s\S]*?\)(\s*)",
        r"\1pass\3",
        content,
        flags=re.MULTILINE,
    )

    # Special case for if-else blocks with only LOGGER statements
    content = re.sub(
        r"(\s*)if\s+.*?:\s*\n\s*LOGGER\.(debug|warning)\(.*?\)\s*\n(\s*)else\s*:\s*\n\s*LOGGER\.(debug|warning)\(.*?\)",
        r"\1pass",
        content,
    )

    # Write the modified content back to the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return debug_count, warning_count


def main():
    total_debug = 0
    total_warning = 0
    modified_files = 0

    # Walk through all Python files in the repository
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                debug, warning = process_file(file_path)

                if debug > 0 or warning > 0:
                    modified_files += 1
                    print(
                        f"Modified {file_path}: removed {debug} debug and {warning} warning logs"
                    )
                    total_debug += debug
                    total_warning += warning

    print(
        f"\nSummary: Modified {modified_files} files, removed {total_debug} debug logs and {total_warning} warning logs"
    )


if __name__ == "__main__":
    main()
