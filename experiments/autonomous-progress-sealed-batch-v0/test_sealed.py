import importlib.util,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("sealed_batch_test_module",HERE/"run.py")
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)

def test_manifest_is_exact_and_stable():
    first=module.manifest();second=module.manifest()
    assert first==second
    assert len(first["targets"])==16
    assert not set(first["targets"])&set(first["development_exclusions"])
