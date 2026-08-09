from __future__ import annotations
import importlib.util,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("conditional_route_v3_base",HERE.parent/"progress-drive-conditional-route-v1"/"run.py");assert spec and spec.loader
BASE=importlib.util.module_from_spec(spec);sys.modules[spec.name]=BASE;spec.loader.exec_module(BASE)
BASE.HERE=HERE;BASE.ART=HERE/"artifacts"/"fresh-1";BASE.B.ARTIFACTS=BASE.ART
if __name__=="__main__":raise SystemExit(BASE.main())
