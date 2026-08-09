from pathlib import Path
import importlib.util
import json
import sys

PATH = Path(__file__).with_name("selector.py")
SPEC = importlib.util.spec_from_file_location("progress_cross_selector", PATH)
S = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = S
SPEC.loader.exec_module(S)


def test_metadata_only_selection(tmp_path):
    for game, tags in (("tr87", ["keyboard"]), ("wa30", ["keyboard"]), ("other", ["click"])):
        path = tmp_path / game / "v" / "metadata.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"game_id": game + "-v", "tags": tags}))
    receipt = S.select(tmp_path)
    assert receipt["selected"]["game"] == "tr87"
    assert "wa30" in receipt["excluded"]
