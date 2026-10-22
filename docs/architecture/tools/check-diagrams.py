#!/usr/bin/env python3
"""Checks that the generated diagrams match the model.

    check-diagrams.py <workspace.json> <diagrams-dir> <readme.md>

Fails when a view has no SVG, an SVG has no view, or the README does not show a view.
Export the workspace to JSON first: structurizr export -f json -w workspace.dsl -o <dir>
"""

import json
import pathlib
import sys


def view_keys(workspace: dict) -> set[str]:
    keys = set()
    for name, items in workspace["views"].items():
        if name != "configuration" and isinstance(items, list):
            keys.update(view["key"] for view in items if "key" in view)
    return keys


def main(workspace_json: str, diagrams: str, readme: str) -> int:
    keys = view_keys(json.load(open(workspace_json)))
    files = {path.stem for path in pathlib.Path(diagrams).glob("*.svg")}
    text = pathlib.Path(readme).read_text()

    problems = []
    problems += [f"view '{key}' has no diagrams/{key}.svg. Run export.sh." for key in sorted(keys - files)]
    problems += [f"diagrams/{name}.svg has no view. Delete it." for name in sorted(files - keys)]
    problems += [
        f"README.md does not show the view '{key}'." for key in sorted(keys) if f"diagrams/{key}.svg" not in text
    ]
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"{len(keys)} views, {len(files)} diagrams, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
