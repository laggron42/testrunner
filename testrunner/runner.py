from __future__ import annotations

import subprocess

from enum import IntEnum
from typing import Iterator

from testrunner.yaml import Test, TestGroup
from testrunner.exceptions import TestFailure, StdoutMismatch, StderrMismatch, ExitCodeMismatch


class TestStatus(IntEnum):
    SUCCESS = 0
    FAILURE = 1  # exit code not specified and != 0
    WRONG_STDOUT = 2
    WRONG_STDERR = 3
    WRONG_EXIT_CODE = 4


class GroupRunner:
    """
    Runs tests from a single group.
    """

    def __init__(self, group: TestGroup):
        self.group = group

    @classmethod
    def recursive_init(cls, group: TestGroup) -> Iterator[GroupRunner]:
        """
        Since groups can hold groups themselves, this function returns the list of generated
        GroupRunner objects from the given group and its children.
        """
        yield cls(group)
        for child_group in group.groups:
            yield from cls.recursive_init(child_group)

    def run_test(self, test: Test):
        p = subprocess.Popen(self.group.args, cwd=self.group.path)
        stdout, stderr = p.communicate(input=test.stdin)  # TODO: timeout

        # exit code check
        if self.group.exit_code is None:
            if p.returncode != 0:
                raise TestFailure(p.returncode)
        elif p.returncode != self.group.exit_code:
            raise ExitCodeMismatch(p.returncode, self.group.exit_code)

        # output check
        expected_stdout = test.stdout or self.group.stdout
        expected_stderr = test.stderr or self.group.stderr
        if expected_stdout and stdout != expected_stdout:
            raise StdoutMismatch(stdout, expected_stdout)
        if expected_stderr and stderr != expected_stderr:
            raise StderrMismatch(stderr, expected_stderr)

