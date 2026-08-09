import importlib.util,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location("sealed_v2",HERE/"run.py");m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_manifest():assert len(m.manifest()["targets"])==16 and m.manifest()["mechanism_commit"]=="6a60ddd"
