class TestException(Exception):
    """
    Base class for test exceptions.
    """

    ...


class TestFailure(TestException):
    """
    Program returned non-zero exit code when no specific exit code was expected.
    """

    def __init__(self, exit_code: int):
        super().__init__(f"Got exit code {exit_code} when running test")


class StdoutMismatch(TestException):
    def __init__(self, output: str, expected: str):
        super().__init__(f"stdout mismatch:\nOutput: {output}\nExpected: {expected}")


class StderrMismatch(TestException):
    def __init__(self, output: str, expected: str):
        super().__init__(f"stderr mismatch:\nOutput: {output}\nExpected: {expected}")


class ExitCodeMismatch(TestException):
    def __init__(self, output: int, expected: int):
        super().__init__(f"exit code mismatch: expected {expected}, got {output}")
