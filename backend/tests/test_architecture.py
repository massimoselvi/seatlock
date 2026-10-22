"""workshops/rules.py must stay pure: standard library only."""

import ast
import sys
from pathlib import Path

RULES = Path(__file__).resolve().parent.parent / "workshops" / "rules.py"


def imported_roots(source: str):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            yield node.lineno, "." * node.level + (node.module or "").split(".")[0]


def impure(source: str) -> list[tuple[int, str]]:
    return [(n, root) for n, root in imported_roots(source) if root not in sys.stdlib_module_names]


def test_rules_module_imports_only_the_standard_library():
    assert impure(RULES.read_text()) == []


def test_the_checker_catches_django_and_relative_imports():
    source = "import enum\nfrom django.db import models\nfrom .models import Registration\n"
    assert impure(source) == [(2, "django"), (3, ".models")]
