import yaml

from dataclasses import dataclass


@dataclass
class AbstractTest:
    description: str | None
    skip: bool = False
    stdin: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int = 1


@dataclass
class Test(AbstractTest):
    ...

