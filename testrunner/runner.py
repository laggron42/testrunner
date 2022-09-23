from __future__ import annotations

import subprocess
import multiprocessing
import time

from enum import IntEnum
from typing import Iterator
from dataclasses import dataclass
from rich import progress
from concurrent.futures import ProcessPoolExecutor

from testrunner.yaml import Config, Test, TestGroup
from testrunner.exceptions import (
    TestException,
    TestFailure,
    StdoutMismatch,
    StderrMismatch,
    ExitCodeMismatch,
)


class TestStatus(IntEnum):
    SUCCESS = 0
    FAILURE = 1  # exit code not specified and != 0
    WRONG_STDOUT = 2
    WRONG_STDERR = 3
    WRONG_EXIT_CODE = 4
    TIMED_OUT = 5


@dataclass
class TestResult:
    test: Test
    status: TestStatus
    exception: TestException | None
    time: float


class GroupRunner:
    """
    Runs tests from a single group.
    """

    def __init__(self, group: TestGroup):
        self.group = group
        self.results: list[TestResult] = []

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
        p = subprocess.Popen(
            [self.group.program] + self.group.args,
            cwd=self.group.path,
            #stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            shell=True,
        )
        if test.stdin:
            stdout, stderr = p.communicate(input=test.stdin, timeout=test.timeout)
        else:
            p.wait(timeout=test.timeout)
            stdout = p.stdout
            stderr = p.stderr

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

    def _run_tests(self, progress: dict, task_id: int):
        total = len(self.group.tests)
        for i, test in enumerate(self.group.tests):
            print(i)
            exc = None
            t1 = time.time()
            try:
                self.run_test(test)
            except TestFailure as e:
                status = TestStatus.FAILURE
                exc = e
            except StdoutMismatch as e:
                status = TestStatus.WRONG_STDOUT
                exc = e
            except StderrMismatch as e:
                status = TestStatus.WRONG_STDERR
                exc = e
            except ExitCodeMismatch as e:
                status = TestStatus.WRONG_EXIT_CODE
                exc = e
            except subprocess.TimeoutExpired:
                status = TestStatus.TIMED_OUT
            else:
                status = TestStatus.SUCCESS
            t2 = time.time()
            self.results.append(TestResult(test, status, exc, t2 - t1))
            progress[task_id] = {"progress": i + 1, "total": total}


class Runner:
    def __init__(self, config: Config):
        self.config = config
        self.progress = progress.Progress(
            progress.SpinnerColumn(),
            progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            progress.BarColumn(),
            progress.TextColumn("[progress.description]{task.description}"),
            progress.TimeRemainingColumn(),
            progress.TimeElapsedColumn(),
        )

    def init(self):
        futures = []
        self.progress.start()
        with multiprocessing.Manager() as manager:
            _progress = manager.dict()
            overall_progress_task = self.progress.add_task("[green]All jobs progress:")
            with ProcessPoolExecutor() as executor:
                for group in self.config.groups:
                    runner = GroupRunner(group)
                    task_id = self.progress.add_task(f"Group {group.name}", visible=False)
                    futures.append(
                        executor.submit(runner._run_tests, _progress, task_id)  # type: ignore
                    )
                while (n_finished := sum([future.done() for future in futures])) < len(
                    futures
                ):
                    self.progress.update(
                        overall_progress_task, completed=n_finished, total=len(futures)
                    )
                    for task_id, update_data in _progress.items():
                        latest = update_data["progress"]
                        total = update_data["total"]
                        # update the progress bar for this task:
                        self.progress.update(
                            task_id,
                            completed=latest,
                            total=total,
                            visible=latest < total,
                        )

                self.progress.stop()
                # raise any errors:
                for future in futures:
                    future.result()

