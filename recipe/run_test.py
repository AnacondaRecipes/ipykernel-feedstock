import json
import os
import platform
import sys
import pytest
import typing
from pathlib import Path

# TODO: investigate upstream interrupt regression in 6.5.0
test_skips = ["flaky", "interrupt"]

# Add tests requiring ipyparallel (cyclic dependency)
test_skips.extend([
    "test_do_apply",
    "test_no_closure", 
    "test_generator_closure",
    "test_nested_closure",
    "test_closure"
])

py_major = sys.version_info[0]
py_impl = platform.python_implementation().lower()
machine = platform.machine().lower()
system = platform.system().lower()

is_aarch = "aarch64" in machine
is_ppc = "ppc" in machine
is_pypy = py_impl == "pypy"
is_win = system == "windows"

prefix = Path(os.environ["PREFIX"])


def check_kernel() -> int:
    print(f"Python implementation: {py_impl}")
    print(f"              Machine: {machine}")
    print(f"               System: {system}")

    specfile = prefix / f"share/jupyter/kernels/python{py_major}/kernel.json"

    print(f"Checking Kernelspec at:     {specfile}...")

    raw_spec = specfile.read_text(encoding="utf-8")

    print(raw_spec)

    spec = json.loads(raw_spec)

    print(f"""Checking python executable: {spec["argv"][0]}""")

    if spec["argv"][0].replace("\\", "/") != sys.executable.replace("\\", "/"):
        print(
            "The kernelspec seems to have the wrong prefix. \n"
            f"""    Specfile: {spec["argv"][0]}"""
            "\n"
            f"""    Expected: {sys.executable}"""
        )
        return 1

    return 0


def build_pytest_args() -> typing.List[str]:
    pytest_args = [
        "--color=no",
        "--tb=long",
        "-vv",
        "-W", "ignore::DeprecationWarning",
        "--timeout=300",
        "--asyncio-mode=auto",
    ]

        # Ignore entire test files with Windows IOPub threading issues
    if is_win:
        pytest_args.extend([
            "--ignore=tests/test_jsonutil.py",    # JSON parsing issues
            "--ignore=tests/test_kernel.py",      # Multiple flaky tests
            "--ignore=tests/test_io.py",          # IOPub cleanup issues
            "--ignore=tests/test_zmq_shell.py",   # ZMQ teardown issues
        ])

    # Skip coverage on PyPy (slow) and Windows (C extension issues)
    if py_impl != "pypy" and not is_win:
        pytest_args += [
            "--cov=ipykernel",
            "--cov-branch",
            "--cov-report=term-missing:skip-covered",
            "--no-cov-on-fail",
        ]

    if is_win:
        test_skips.extend(
            [
                # test_pickleutil fails on windows, `pickleutil` deprecated anyway,
                "pickleutil",
                # ERROR tests/test_io.py::test_event_pipe_gc - Windows socket cleanup race.
                # Windows uses different socket APIs (Winsock vs BSD sockets) and different asyncio event loop implementations (SelectorEventLoop), 
                # causing different timing/cleanup behavior for background threads compared to Unix systems.
                "test_event_pipe_gc",
                # ERROR tests/test_io.py::test_echo_watch - pytest.PytestUnhandledThreadExceptionWarning: Exception in thread IOPub
                # E   Enable tracemalloc to get traceback where the object was allocated.
                # E   See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
                "test_echo_watch",
                # FAILED tests/test_zmq_shell.py::test_magics - exceptiongroup.ExceptionGroup: multiple unraisable exception warnings (3 sub-exceptions)
                # FAILED tests/test_zmq_shell.py::test_zmq_interactive_shell - exceptiongroup.ExceptionGroup: multiple unraisable exception warnings (3 sub-exceptions)
                "test_magics",
                "test_zmq_interactive_shell",

            ]
        )

    if len(test_skips) == 1:
        # single-term parens work unexpectedly
        pytest_args += ["-k", f"not {test_skips[0]}"]
    elif len(test_skips) > 1:
        pytest_args += ["-k", f"""not ({" or ".join(test_skips)})"""]

    return pytest_args


def run_pytest():
    if is_pypy and (is_aarch or is_ppc):
        print(f"Skipping pytest on {machine} for {py_impl}")
        return 0

    pytest_args = build_pytest_args()

    print("Final pytest args:", pytest_args, flush=True)

    # actually run the tests
    rc = int(pytest.main(pytest_args))

    if json.loads(os.environ.get("MIGRATING", "0").lower()):
        print("Ignoring pytest failure due to on-going migration...")
        return 0

    return rc


def main() -> int:
    return check_kernel() or run_pytest()


if __name__ == "__main__":
    sys.exit(main())
