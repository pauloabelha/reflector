"""Architecture tests for the canonical package dependency direction."""

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[2] / "reflector"
LAYERS = ("core", "runtime", "research", "evolution")
ALLOWED_INTERNAL_IMPORTS = {
    "core": {"core"},
    "runtime": {"core", "runtime"},
    "research": {"core", "runtime", "research"},
    "evolution": {"core", "runtime", "research", "evolution"},
}


def _absolute_import(
    module_path: Path,
    node: ast.ImportFrom,
) -> tuple[str, ...]:
    package = ("reflector", module_path.parent.name)
    if node.level:
        retained = len(package) - (node.level - 1)
        prefix = package[:retained]
    else:
        prefix = ()
    suffix = tuple((node.module or "").split(".")) if node.module else ()
    return (*prefix, *suffix)


def test_canonical_packages_only_depend_inward() -> None:
    violations: list[str] = []
    for layer in LAYERS:
        for module_path in sorted((PACKAGE_ROOT / layer).glob("*.py")):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                imported = _absolute_import(module_path, node)
                if len(imported) < 2 or imported[0] != "reflector":
                    continue
                imported_layer = imported[1]
                if (
                    imported_layer in LAYERS
                    and imported_layer not in ALLOWED_INTERNAL_IMPORTS[layer]
                ):
                    violations.append(
                        f"{module_path.relative_to(PACKAGE_ROOT)} imports "
                        f"{'.'.join(imported)}"
                    )
    assert not violations, "\n".join(violations)


def test_legacy_imports_alias_canonical_types() -> None:
    from reflector.core.mind import MindConfig
    from reflector.mind import MindConfig as LegacyMindConfig
    from reflector.policy import SymbolicPolicy as LegacyPolicy
    from reflector.runtime.policy import SymbolicPolicy

    assert LegacyMindConfig is MindConfig
    assert LegacyPolicy is SymbolicPolicy
