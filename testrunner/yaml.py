from __future__ import annotations

import sys
import yaml
import logging

from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

log = logging.getLogger("testrunner.yaml")


@dataclass(kw_only=True)
class BaseTest:
    group: TestGroup
    stdout: bytes | None
    stderr: bytes | None
    exit_code: int | None
    description: str | None
    skip: bool
    timeout: int | None

    def __post_init__(self):
        # inherit values from group if not set
        self.stdout = self.stdout or self.group.stdout
        self.stderr = self.stderr or self.group.stderr
        self.exit_code = self.exit_code or self.group.exit_code
        self.timeout = self.timeout or self.group.timeout


@dataclass(kw_only=True)
class Test(BaseTest):
    """
    A single test in the suite.
    """

    stdin: bytes


@dataclass(kw_only=True)
class TestGroup(BaseTest):
    """
    A group of tests.
    """

    name: str
    group: TestGroup | None
    path: Path
    program: str
    args: list[str]
    init: str | None
    teardown: str | None
    group_timeout: int | None
    timeout: int | None
    tests: list[Test] = field(default_factory=list)
    groups: list[TestGroup] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        # inherit values from parent groups
        if self.group:
            self.path = self.path or self.group.path
            self.program = self.program or self.group.program
            # None values for init, teardown and group_teardown are to be kept, not inherited


class Config:
    name: str
    pwd: Path
    program: str
    teardown: str | None
    args: list[str]
    groups: list[TestGroup]

    def __init__(self, path: Path):
        try:
            with path.open("r") as file:
                content: dict[str, Any] = yaml.full_load(file)
        except Exception:
            log.error("Failed to load YAML file", exc_info=True)
            sys.exit(1)

        self.name = content["name"]
        self.pwd = Path(content.pop("pwd", "."))
        self.program = content["program"]
        self.teardown = content.pop("teardown", None)
        self.args = content.pop("args", [])
        self.groups = [self._read_test_group(x, y) for x, y in content.items()]

    def _read_test_group(
        self, name: str, group: dict[str, Any], parent_group: TestGroup | None = None
    ) -> TestGroup:
        if "pwd" in group:
            path = Path(group["pwd"])
        else:
            path = Path(".")

        test_group = TestGroup(
            name=name,
            group=parent_group,
            path=path,
            program=group.get("program", None),
            args=group.get("args", None),
            init=group.get("init", None),
            teardown=group.get("teardown", None),
            group_timeout=group.get("group-timeout", None),
            timeout=group.get("test-timeout", None),
            stdout=group.get("out", None),
            stderr=group.get("err", None),
            exit_code=group.get("exit-code", None),
            description=group.get("description", None),
            skip=group.get("skip", False),
        )
        test_group.tests = [self._read_test(test_group, x) for x in group["tests"]]
        test_group.groups = [
            self._read_test_group(x, y, test_group) for x, y in group.get("groups", {}).items()
        ]
        return test_group

    def _read_test(self, group: TestGroup, test: dict[str, Any]) -> Test:
        return Test(
            group=group,
            stdin=test["in"],
            stdout=test.get("out", None),
            stderr=test.get("err", None),
            exit_code=test.get("exit-code", None),
            description=test.get("description", None),
            skip=test.get("skip", False),
            timeout=test.get("timeout", None),
        )
