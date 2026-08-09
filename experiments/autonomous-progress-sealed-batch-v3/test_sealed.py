import importlib.util,pathlib,sys,tempfile
HERE=pathlib.Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location("sealed_v3",HERE/"run.py");m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_manifest_and_atomic_checkpoint():
 assert len(m.manifest()["targets"])==16 and m.manifest()["mechanism_commit"]=="16d2bb5"
 with tempfile.TemporaryDirectory() as root:
  path=pathlib.Path(root)/"x.json";m.atomic(path,{"ok":True});assert path.read_text().startswith('{') and not path.with_suffix('.json.tmp').exists()
