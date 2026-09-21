"""
FR-14 Code Sandbox.

Runs generated Python in a separate subprocess with:
  - python -I (isolated mode: no user site-packages, no PYTHONSTARTUP)
  - cwd = fresh temp directory (deleted after execution)
  - AST-level check rejecting dangerous imports and calls
  - Network guard preamble
  - Resource limits on POSIX (CPU time, memory)
  - Hard timeout + output cap

HONEST LIMITATION: This is best-effort subprocess isolation suitable for
a demo/hackathon. It is NOT a true sandbox.  For production, swap in
`docker run --rm --network none --memory=512m python:3.11-slim` — the
call signature below is unchanged either way.
"""
import subprocess
import sys
import tempfile
import os
import ast
import shutil
from ..core.config import settings

GUARD_PREAMBLE = (
    "import socket\n"
    "def _blocked(*a, **k): raise ConnectionError('network access disabled in sandbox')\n"
    "socket.create_connection = _blocked\n"
    "socket.socket.connect = _blocked\n"
    "socket.socket.connect_ex = _blocked\n"
)

# Modules that user code must NOT import
FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "ctypes",
    "importlib", "pathlib", "signal", "multiprocessing", "threading",
}

# Built-in calls that user code must NOT use
FORBIDDEN_CALLS = {"open", "eval", "exec", "__import__", "compile", "globals", "locals"}


class SandboxSecurityError(Exception):
    pass


def _check_ast_safety(code: str):
    """Parse code AST and reject dangerous imports/calls."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxSecurityError(f"Syntax error in generated code: {e}")

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    raise SandboxSecurityError(f"Forbidden import: '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    raise SandboxSecurityError(f"Forbidden import from: '{node.module}'")
        # Check calls to forbidden builtins
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise SandboxSecurityError(f"Forbidden call: '{node.func.id}()'")


def run_python(code: str, timeout: int = None):
    timeout = timeout or settings.SANDBOX_TIMEOUT_SECONDS

    # AST safety check
    try:
        _check_ast_safety(code)
    except SandboxSecurityError as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Security check failed: {e}",
            "returncode": -2,
        }

    # Create isolated temp directory for execution
    tmpdir = tempfile.mkdtemp(prefix="trustforge_sandbox_")
    script_path = os.path.join(tmpdir, "script.py")

    try:
        with open(script_path, "w") as f:
            f.write(GUARD_PREAMBLE + "\n" + code)

        # Build environment: minimal PATH only
        env = {"PATH": os.environ.get("PATH", "")}

        # POSIX resource limits via ulimit-style preexec
        preexec = None
        if sys.platform != "win32":
            def preexec():
                import resource
                # CPU time limit: timeout + 5s grace
                resource.setrlimit(resource.RLIMIT_CPU, (timeout + 5, timeout + 10))
                # Memory limit: 256MB
                mem_limit = 256 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))

        proc = subprocess.run(
            [sys.executable, "-I", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=tmpdir,
            preexec_fn=preexec,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Execution timed out after {timeout}s", "returncode": -1}
    finally:
        # Clean up temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)
