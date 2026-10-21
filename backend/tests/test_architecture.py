"""The layer rules from ADR 0005, enforced. A forbidden import fails the build.

domain          pure Python. Imports nothing but the standard library and itself.
application     use cases and ports. May import domain. No framework, no outer layers.
infrastructure  Django, Celery, ORM. May import domain and application.
interface       DRF views. May import everything inward.
"""

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
FRAMEWORKS = {"django", "rest_framework", "celery"}

FORBIDDEN = {
    "domain": FRAMEWORKS | {"application", "infrastructure", "interface", "config"},
    "application": FRAMEWORKS | {"infrastructure", "interface", "config"},
    "infrastructure": {"interface", "rest_framework"},
    "interface": set(),
}


def imported_roots(source: str):
    """Yield (line, top-level module) for every absolute import in `source`."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module.split(".")[0]


def violations(source: str, forbidden: set[str]) -> list[tuple[int, str]]:
    return [(line, root) for line, root in imported_roots(source) if root in forbidden]


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_imports_only_inward(layer):
    found = []
    for path in sorted((BACKEND / layer).rglob("*.py")):
        if "migrations" in path.parts:
            continue
        for line, root in violations(path.read_text(), FORBIDDEN[layer]):
            found.append(f"{path.relative_to(BACKEND)}:{line} imports {root}")
    assert not found, f"{layer} breaks the dependency rule:\n" + "\n".join(found)


def test_the_checker_catches_a_violation():
    source = "import os\nfrom django.db import models\nfrom infrastructure.db import models as m\n"
    assert violations(source, FORBIDDEN["application"]) == [(2, "django"), (3, "infrastructure")]


def test_the_checker_ignores_relative_and_allowed_imports():
    source = "from .dto import Result\nfrom domain.workshops.entities import Workshop\n"
    assert violations(source, FORBIDDEN["application"]) == []
