"""Small, fail-closed Python sandbox for ephemeral Executor computation."""

from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
from typing import Any, Mapping

# Isolated mode removes the script directory from ``sys.path``.  Add only this
# preregistered experiment directory so the child can load the frozen primitive
# surface; generated code still has no import statement or import builtin.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import executor_primitives


class SandboxError(RuntimeError):
    pass


FORBIDDEN_NODES = (
    ast.Import, ast.ImportFrom, ast.AsyncFunctionDef, ast.Await, ast.ClassDef,
    ast.Delete, ast.Global, ast.Lambda, ast.Nonlocal, ast.With, ast.AsyncWith,
)
FORBIDDEN_NAMES = {
    "__builtins__", "breakpoint", "compile", "eval", "exec", "exit",
    "getattr", "globals", "help", "input", "locals", "memoryview", "open",
    "quit", "setattr", "vars",
}
SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "iter": iter, "len": len, "list": list, "map": map, "max": max,
    "min": min, "next": next, "print": print, "range": range,
    "reversed": reversed, "round": round, "set": set, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "zip": zip,
}


def validate_source(source: str, *, max_source_chars: int) -> ast.Module:
    if len(source) > int(max_source_chars):
        raise SandboxError("source-length-bound")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as error:
        raise SandboxError(f"syntax-error:{error.msg}") from error
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise SandboxError(f"forbidden-syntax:{type(node).__name__}")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise SandboxError(f"forbidden-name:{node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise SandboxError(f"forbidden-attribute:{node.attr}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            raise SandboxError(f"forbidden-call:{node.func.id}")
    return tree


def _child(payload: Mapping[str, Any]) -> int:
    limits = payload["limits"]
    memory = int(limits["memory_bytes"])
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (max(1, int(float(limits["timeout_seconds"]))), max(2, int(float(limits["timeout_seconds"])) + 1)))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    tree = validate_source(str(payload["code"]), max_source_chars=int(limits["max_source_chars"]))
    namespace: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "snapshot": payload["snapshot"],
        "result": None,
    }
    namespace.update(executor_primitives.bound_namespace(payload["snapshot"]))
    stream = io.StringIO()
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            exec(compile(tree, "<executor-analysis>", "exec"), namespace, namespace)
        result = namespace.get("result")
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        document = {
            "status": "ok",
            "stdout": stream.getvalue(),
            "stderr": "",
            "return_value": result,
            "execution_time_s": time.perf_counter() - started,
        }
    except BaseException as error:
        document = {
            "status": "runtime-failure",
            "stdout": stream.getvalue(),
            "stderr": f"{type(error).__name__}: {error}",
            "return_value": None,
            "execution_time_s": time.perf_counter() - started,
        }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(document["stdout"].encode("utf-8")) > int(limits["max_stdout_bytes"]):
        document.update(status="stdout-bound", stdout=document["stdout"].encode("utf-8")[: int(limits["max_stdout_bytes"])].decode("utf-8", errors="replace"), return_value=None)
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > int(limits["max_return_bytes"]):
        document.update(status="return-bound", return_value=None)
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write(encoded)
    return 0


def run_analysis(code: str, snapshot: Mapping[str, Any], limits: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one validated program in a fresh isolated Python process."""

    validate_source(code, max_source_chars=int(limits["max_source_chars"]))
    payload = json.dumps({"code": code, "snapshot": snapshot, "limits": dict(limits)}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", str(Path(__file__).resolve()), "--child"],
            input=payload,
            text=True,
            capture_output=True,
            timeout=float(limits["timeout_seconds"]),
            check=False,
            env={},
        )
    except subprocess.TimeoutExpired as error:
        return {
            "status": "timeout", "stdout": (error.stdout or "")[: int(limits["max_stdout_bytes"])],
            "stderr": (error.stderr or "")[: int(limits["max_stdout_bytes"])],
            "return_value": None, "execution_time_s": time.perf_counter() - started,
        }
    if completed.returncode != 0:
        return {
            "status": "runtime-failure", "stdout": completed.stdout[: int(limits["max_stdout_bytes"])],
            "stderr": completed.stderr[: int(limits["max_stdout_bytes"])],
            "return_value": None, "execution_time_s": time.perf_counter() - started,
        }
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "status": "runtime-failure", "stdout": completed.stdout[: int(limits["max_stdout_bytes"])],
            "stderr": "invalid child result", "return_value": None,
            "execution_time_s": time.perf_counter() - started,
        }
    document["execution_time_s"] = time.perf_counter() - started
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if not args.child:
        parser.error("analysis_sandbox is an internal tool")
    return _child(json.loads(sys.stdin.read()))


if __name__ == "__main__":
    raise SystemExit(main())
