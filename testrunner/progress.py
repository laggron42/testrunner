from typing import TYPE_CHECKING

from rich.progress_bar import ProgressBar
from rich.progress import BarColumn
from rich.segment import Segment

if TYPE_CHECKING:
    from rich.progress import Task
    from rich.console import Console, ConsoleOptions, RenderResult
    from rich.style import StyleType


class TestProgressBar(ProgressBar):
    """
    Adds support for the 'failed' field.
    """

    def __init__(
        self,
        total: float | None = 100,
        completed: float = 0,
        failed: float = 0,
        width: int | None = None,
        pulse: bool = False,
        style: "StyleType" = "bar.back",
        complete_style: "StyleType" = "bar.complete",
        finished_style: "StyleType" = "bar.finished",
        failed_style: "StyleType" = "yellow",
        pulse_style: "StyleType" = "bar.pulse",
        animation_time: float | None = None,
    ):
        super().__init__(
            total,
            completed,
            width,
            pulse,
            style,
            complete_style,
            finished_style,
            pulse_style,
            animation_time,
        )
        self.failed = failed
        self.failed_style = failed_style

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        width = min(self.width or options.max_width, options.max_width)
        ascii = options.legacy_windows or options.ascii_only
        should_pulse = self.pulse or self.total is None
        if should_pulse:
            yield from self._render_pulse(console, width, ascii=ascii)
            return

        completed: float | None = (
            min(self.total, max(0, self.completed)) if self.total is not None else None
        )

        bar = "-" if ascii else "━"
        half_bar_right = " " if ascii else "╸"
        half_bar_left = " " if ascii else "╺"
        complete_halves = (
            int(width * 2 * completed / self.total)
            if self.total and completed is not None
            else width * 2
        )
        bar_count = complete_halves // 2
        half_bar_count = complete_halves % 2
        style = console.get_style(self.style)
        is_finished = self.total is None or self.completed >= self.total
        if self.failed:
            complete_style = console.get_style(self.failed_style)
        else:
            complete_style = console.get_style(
                self.finished_style if is_finished else self.complete_style
            )
        _Segment = Segment
        if bar_count:
            yield _Segment(bar * bar_count, complete_style)
        if half_bar_count:
            yield _Segment(half_bar_right * half_bar_count, complete_style)

        if not console.no_color:
            remaining_bars = width - bar_count - half_bar_count
            if remaining_bars and console.color_system is not None:
                if not half_bar_count and bar_count:
                    yield _Segment(half_bar_left, style)
                    remaining_bars -= 1
                if remaining_bars:
                    yield _Segment(bar * remaining_bars, style)


class TestBarColumn(BarColumn):
    def render(self, task: "Task") -> TestProgressBar:
        return TestProgressBar(
            total=max(0, task.total) if task.total is not None else None,
            completed=max(0, task.completed),
            failed=task.fields.get("failed", 0),
            width=None if self.bar_width is None else max(1, self.bar_width),
            pulse=not task.started,
            animation_time=task.get_time(),
            style=self.style,
            complete_style=self.complete_style,
            finished_style=self.finished_style,
            pulse_style=self.pulse_style,
        )
