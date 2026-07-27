import ast
import base64
import io
import json
import zipfile

from reflector.kaggle import OVERLAY_FILES, build_overlay, export_submission
from reflector.mind import MindConfig


def test_overlay_contains_only_inference_path() -> None:
    with zipfile.ZipFile(io.BytesIO(build_overlay())) as archive:
        assert set(archive.namelist()) == set(OVERLAY_FILES)
        names = " ".join(archive.namelist()).lower()
        for development_module in (
            "reflector/evolver.py",
            "reflector/experiments.py",
            "reflector/mutations.py",
            "reflector/population.py",
            "reflector/sandbox.py",
            "reflector/transforms.py",
            "reflector/web_api.py",
        ):
            assert development_module not in archive.namelist()
        assert "openai" not in names
        assert "web" not in names
        assert "database" not in names


def test_overlay_import_closure_excludes_development_services() -> None:
    forbidden = {"openai", "langchain", "flask", "sqlite3", "requests"}
    with zipfile.ZipFile(io.BytesIO(build_overlay())) as archive:
        for name in archive.namelist():
            if not name.endswith(".py"):
                continue
            tree = ast.parse(archive.read(name), filename=name)
            imports = {
                alias.name.split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            imports.update(
                node.module.split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            )
            assert not imports & forbidden, (name, imports & forbidden)


def test_export_preserves_kaggle_contract(tmp_path) -> None:
    overlay, notebook = export_submission(tmp_path)
    assert overlay.is_file()
    payload = json.loads(notebook.read_text())
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in payload["cells"]
    )
    assert "KAGGLE_IS_COMPETITION_RERUN" in source
    assert "gateway:8001/api/games" in source
    assert "ARC-AGI-3-Agents" in source
    assert "--agent\", \"reflector" in source
    assert "submission.parquet" in source


def test_export_embeds_selected_symbolic_genome(tmp_path) -> None:
    config = MindConfig(
        planner_max_expansions=17,
        information_weight=2.5,
    )
    overlay, notebook = export_submission(tmp_path, config)
    payload = json.loads(notebook.read_text())
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in payload["cells"]
    )
    encoded_config = json.dumps(
        config.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert f"os.environ[\"REFLECTOR_CONFIG_JSON\"] = {encoded_config!r}" in source

    embedded = source.split('base64.b64decode("', 1)[1].split('")', 1)[0]
    assert base64.b64decode(embedded) == overlay.read_bytes()
