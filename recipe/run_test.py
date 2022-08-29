import json
import os
import pkgutil
import platform
import sys
import tempfile

import pytest


def go():
    py_major = sys.version_info[0]
    py_impl = platform.python_implementation().lower()
    machine = platform.machine().lower()

    print("Python implementation:", py_impl)
    print("              Machine:", machine)
    specfile = os.path.join(
        os.environ["PREFIX"],
        "share",
        "jupyter",
        "kernels",
        "python{}".format(py_major),
        "kernel.json",
    )

    print("Checking Kernelspec at:     ", specfile, "...\n")

    with open(specfile, "r") as fh:
        raw_spec = fh.read()

    print(raw_spec)

    spec = json.loads(raw_spec)

    print("\nChecking python executable", spec["argv"][0], "...")

    if spec["argv"][0].replace("\\", "/") != sys.executable.replace("\\", "/"):
        print(
            "The kernelspec seems to have the wrong prefix. \n"
            "Specfile: {}\n"
            "Expected: {}"
            "".format(spec["argv"][0], sys.executable)
        )
        sys.exit(1)

    loader = pkgutil.get_loader("ipykernel.tests")
    pytest_args = [os.path.dirname(loader.path), "-vv", "--timeout", "300"]

    # coverage options
    pytest_args += [
        "--cov",
        "ipykernel",
        "--cov-report",
        "term-missing:skip-covered",
        "--no-cov-on-fail",
    ]

    skips = ["flaky"]

    if len(skips) == 1:
        # 2022/8/29: CI issues on Prefect for linux platforms:
        # The test_shutdown_subprocesses is failing has to do 
        # with shutting down the system using process groups. 
        # We put the entire build into a process group.
        # It looks that the test is checking to see 
        # that a child process or process group is shutdown after it’s requested to, but it’s not.
        if platform.system() == "Linux":
            skips += ["test_shutdown_subprocesses"]
            pytest_args += ["-k", "not ({})".format(" or ".join(skips))]
        else:
            pytest_args += ["-k", "not {}".format(*skips)]
    else:
        pytest_args += ["-k", "not ({})".format(" or ".join(skips))]

    print("Final pytest args:", pytest_args)

    # actually run the tests
    sys.exit(pytest.main(pytest_args))


if __name__ == "__main__":
    if platform.system() == "Windows":
        with tempfile.TemporaryDirectory() as appdata:
            # prevent concurrent tests runs from overlapping Jupyter configs
            os.environ["APPDATA"] = appdata
            go()
    else:
        go()
