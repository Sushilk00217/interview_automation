"""
Code Execution Service
----------------------
Runs candidate source code inside isolated Docker containers.

Security model:
  - Network disabled (--network none)
  - Memory capped at 256 MB
  - CPU capped at 1 core
  - PID limit of 50
  - Container removed after execution (--rm)
  - Hard timeout of 10 seconds per run
"""

import os
import subprocess
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security limits
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 10
MEMORY_LIMIT = "256m"

# ---------------------------------------------------------------------------
# Per-language configuration
# ---------------------------------------------------------------------------
# Each entry defines:
#   image       – Docker image to use (must be pre-built on the host)
#   filename    – name given to the source file inside /code/
#   compile_cmd – shell tokens run before the program (None = interpreted)
#   run_cmd     – shell tokens used to execute the program
# ---------------------------------------------------------------------------
LANGUAGE_CONFIG: dict[str, dict] = {
    "python3": {
        "image": "code-runner-python",
        "filename": "solution.py",
        "compile_cmd": None,
        "run_cmd": ["python3", "/code/solution.py"],
    },
    "javascript": {
        "image": "code-runner-node",
        "filename": "solution.js",
        "compile_cmd": None,
        "run_cmd": ["node", "/code/solution.js"],
    },
    "java": {
        "image": "code-runner-java",
        "filename": "Solution.java",
        "compile_cmd": ["javac", "/code/Solution.java"],
        "run_cmd": ["java", "-cp", "/code", "Solution"],
    },
    "cpp": {
        "image": "code-runner-cpp",
        "filename": "solution.cpp",
        "compile_cmd": ["g++", "-O2", "-o", "/code/solution", "/code/solution.cpp"],
        "run_cmd": ["/code/solution"],
    },
}

# ---------------------------------------------------------------------------
# Base Docker flags applied to every container run
# ---------------------------------------------------------------------------
_DOCKER_BASE_FLAGS = [
    "--rm",
    "--network", "none",
    f"--memory={MEMORY_LIMIT}",
    "--cpus=1",
    "--pids-limit=50",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_subprocess(
    cmd: list[str],
    stdin_data: Optional[str] = None,
    timeout: int = TIMEOUT_SECONDS,
) -> dict:
    """
    Execute *cmd* as a subprocess and return a normalised result dict.

    Returns:
        {stdout, stderr, exit_code, timed_out, error}
    """
    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "timed_out": False,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        logger.warning("Subprocess timed out: %s", cmd)
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": True,
            "error": f"Execution timed out after {timeout} seconds.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error running subprocess: %s", exc)
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": False,
            "error": str(exc),
        }


def _docker_run_cmd(image: str, mount_dir: str, run_cmd: list[str]) -> list[str]:
    """Build the full ``docker run`` command list."""
    return [
        "docker", "run",
        *_DOCKER_BASE_FLAGS,
        "-v", f"{mount_dir}:/code:ro",  # mount source dir as read-only
        image,
        *run_cmd,
    ]


def _docker_compile_cmd(image: str, mount_dir: str, compile_cmd: list[str]) -> list[str]:
    """
    Build a ``docker run`` command for compilation.
    The volume is mounted read-write so the compiler can emit output artefacts.
    """
    return [
        "docker", "run",
        *_DOCKER_BASE_FLAGS,
        "-v", f"{mount_dir}:/code",  # read-write for compiler output
        image,
        *compile_cmd,
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_code(
    language: str,
    source_code: str,
    stdin_input: Optional[str] = None,
) -> dict:
    """
    Execute *source_code* written in *language* inside a Docker sandbox.

    Steps
    -----
    1. Validate the requested language.
    2. Write the source file to a temporary directory.
    3. If the language requires compilation, compile first.
    4. Run the program, piping *stdin_input* if provided.
    5. Return a result dict with stdout / stderr / exit_code / timed_out / error.

    Returns
    -------
    {
        "stdout"   : str,
        "stderr"   : str,
        "exit_code": int,
        "timed_out": bool,
        "error"    : str | None,
    }
    """
    # --- validate language -------------------------------------------------
    lang = language.lower().strip()
    if lang not in LANGUAGE_CONFIG:
        supported = ", ".join(LANGUAGE_CONFIG.keys())
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": False,
            "error": f"Unsupported language '{language}'. Supported: {supported}",
        }

    config = LANGUAGE_CONFIG[lang]
    image = config["image"]
    filename = config["filename"]
    compile_cmd = config["compile_cmd"]
    run_cmd = config["run_cmd"]

    # --- write source to temp dir -----------------------------------------
    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = os.path.join(tmp_dir, filename)
        try:
            with open(source_path, "w", encoding="utf-8") as fh:
                fh.write(source_code)
        except OSError as exc:
            return {
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "timed_out": False,
                "error": f"Failed to write source file: {exc}",
            }

        # --- compile (if required) ----------------------------------------
        if compile_cmd:
            compile_docker_cmd = _docker_compile_cmd(image, tmp_dir, compile_cmd)
            compile_result = _run_subprocess(compile_docker_cmd, timeout=TIMEOUT_SECONDS)

            if compile_result["timed_out"] or compile_result["exit_code"] != 0:
                # Surface compilation errors directly to the caller
                return {
                    "stdout": compile_result["stdout"],
                    "stderr": compile_result["stderr"] or compile_result["error"],
                    "exit_code": compile_result["exit_code"],
                    "timed_out": compile_result["timed_out"],
                    "error": "Compilation failed.",
                }

        # --- run -------------------------------------------------------------
        run_docker_cmd = _docker_run_cmd(image, tmp_dir, run_cmd)
        return _run_subprocess(run_docker_cmd, stdin_data=stdin_input, timeout=TIMEOUT_SECONDS)

        # tempfile.TemporaryDirectory context manager cleans up tmp_dir here


def run_test_cases(
    language: str,
    source_code: str,
    test_cases: list[dict],
) -> list[dict]:
    """
    Run *source_code* against a list of test cases and return pass/fail results.

    Parameters
    ----------
    language    : one of the keys in LANGUAGE_CONFIG
    source_code : the candidate's solution
    test_cases  : list of dicts, each with keys:
                    - id              (str | UUID)
                    - input           (str)
                    - expected_output (str)

    Returns
    -------
    List of result dicts:
    [
        {
            "test_case_id"    : ...,
            "input"           : str,
            "expected_output" : str,
            "actual_output"   : str,
            "passed"          : bool,
            "error"           : str | None,
        },
        ...
    ]
    """
    results = []

    for tc in test_cases:
        tc_id = tc.get("id")
        stdin_input: str = tc.get("input", "")
        expected_output: str = tc.get("expected_output", "")

        # Execute the code for this test case
        exec_result = execute_code(
            language=language,
            source_code=source_code,
            stdin_input=stdin_input,
        )

        # Normalise actual output: strip trailing whitespace for comparison
        actual_output: str = exec_result["stdout"]
        actual_stripped = actual_output.strip()
        expected_stripped = expected_output.strip()

        # Determine pass/fail
        execution_error = exec_result.get("error")
        timed_out = exec_result.get("timed_out", False)

        if timed_out:
            passed = False
            error_msg = exec_result["error"]  # timeout message
        elif execution_error:
            passed = False
            error_msg = execution_error
        elif exec_result["exit_code"] != 0:
            passed = False
            error_msg = exec_result["stderr"] or f"Non-zero exit code: {exec_result['exit_code']}"
        else:
            passed = actual_stripped == expected_stripped
            error_msg = None

        results.append({
            "test_case_id": tc_id,
            "input": stdin_input,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "passed": passed,
            "error": error_msg,
        })

    return results
