import argparse
import sys

from pathlib import Path

from testrunner import __version__ as program_version
from testrunner.yaml import Config
from testrunner.runner import GroupRunner


class CLIFlags(argparse.Namespace):
    version: bool


def parse_cli_flags() -> CLIFlags:
    parser = argparse.ArgumentParser(prog="testrunner", description="Functional test runner")
    parser.add_argument("--version", action="store_true", help="Show the program's version")
    return parser.parse_args(sys.argv[1:], namespace=CLIFlags())


def main():
    cli_flags = parse_cli_flags()

    if cli_flags.version:
        print(f"Testrunner version {program_version}")
        sys.exit(0)

    config = Config(Path("tests.yml"))
    runner = GroupRunner(config.groups[0])
    print(list(runner._run_tests()))


if __name__ == "__main__":
    main()
