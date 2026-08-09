import importlib.util,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location("sealed_v1_test",HERE/"run.py");module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
def test_manifest_is_frozen_and_complete():
    assert module.manifest()==module.manifest()
    assert len(module.manifest()["targets"])==16
    assert module.manifest()["mechanism_commit"]=="594037e"
