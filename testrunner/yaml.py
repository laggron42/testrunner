from __future__ import annotations

import sys
import yaml
import logging

from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

log = logging.getLogger("testrunner.yaml")


@dataclass(kw_only=True)
class Test:
    """
    A single test in the suite.
    """
    stdin: bytes | None = None
    stdout: bytes | None = None
    stderr: bytes | None = None
    exit_code: int = 0
    description: str | None = None
    skip: bool = False


@dataclass(kw_only=True)
class TestGroup(Test):
    """
    A group of tests.
    """
    name: str
    path: Path | None = Path(".")
    program: str | None = None
    teardown: str | None = None
    args: list[str] = field(default_factory=list)
    tests: list[Test] = field(default_factory=list)
    groups: list[TestGroup] = field(default_factory=list)


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

    def _read_test_group(self, name: str, group: dict[str, Any]) -> TestGroup:
        if "pwd" in group:
            path = Path(group["pwd"])
        else:
            path = None

        return TestGroup(
            name=name,
            path=path,
            program=group.get("program", None),
            args=group.get("args", None),
            description=group.get("description", None),
            skip=group.get("skip", False),
            stdout=group.get("out", None),
            stderr=group.get("err", None),
            exit_code=group.get("exit-code", None),
            tests=[self._read_test(x) for x in group["tests"]],
            groups=[self._read_test_group(x, y) for x, y in group.get("groups", {}).items()],
        )

    def _read_test(self, test: dict[str, Any]) -> Test:
        return Test(
            stdin=test["in"],
            stdout=test.get("out", None),
            stderr=test.get("err", None),
            exit_code=test.get("exit-code", None),
            description=test.get("description", None),
            skip=test.get("skip", False),
        )

