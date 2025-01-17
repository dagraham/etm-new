from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.strip import Strip
from textual.scroll_view import ScrollView
from textual.screen import Screen
from rich.segment import Segment
from textual.widgets import Static, Footer, Header
from rich.table import Table
from rich import box
from prompt_toolkit.styles.named_colors import NAMED_COLORS


FRAME_COLOR = NAMED_COLORS["Khaki"]
DAY_COLOR = NAMED_COLORS["LemonChiffon"]
HEADER_COLOR = NAMED_COLORS["CornflowerBlue"]


class ScrollableList(ScrollView):
    """A scrollable list widget."""

    def __init__(self, lines: list[str]) -> None:
        super().__init__()
        self.lines = lines
        self.virtual_size = Size(
            40, len(lines)
        )  # Width 40, height equals number of lines

    def render_line(self, y: int) -> Strip:
        """Render a single line of the list."""
        scroll_x, scroll_y = self.scroll_offset  # Current scroll position
        y += scroll_y  # Adjust for the current vertical scroll offset

        # If the line index is out of bounds, return an empty line
        if y < 0 or y >= len(self.lines):
            return Strip.blank(self.size.width)

        # Get the line text and create a segment for it
        line_text = self.lines[y]
        segment = Segment(line_text.ljust(self.size.width))  # Left-align and pad
        return Strip([segment], self.size.width)


class WeeksTable:
    CSS = """
    Screen {
        background: #2e2e2e; /* Dark grey  near perfect */
    }
    """

    def __init__(self) -> None:
        self.table = self.get_table()

    # def get_table(self, title="Calendar", dates: list[tuple[int, bool, str]]) -> Static:
    def get_table(
        self,
        grouped_events,
        start_date,
    ) -> Static:
        # Create a Rich Table
        self.table = Table(
            # title="[bold]Calendar[/bold]",
            title="December 28, 2024 - January 24, 2025",
            title_justify="center",
            title_style="bold yellow",
            caption="Items for January 13 - 19, 2025",
            caption_style="bold yellow",
            caption_justify="center",
            header_style=HEADER_COLOR,
            show_lines=True,
            style=FRAME_COLOR,
            expand=True,
            box=box.SQUARE,
        )
        table.add_column("Wk", justify="center")
        for i in range(7):
            table.add_column(
                (start_date + timedelta(days=i)).strftime("%A"), justify="center"
            )

        self.table.add_column("Wk", style="dim", width=6, justify="center")
        self.table.add_column("Mon", style=DAY_COLOR, justify="center", width=10)
        self.table.add_column("Tue", style=DAY_COLOR, justify="center", width=10)
        self.table.add_column("Wed", style=DAY_COLOR, justify="center", width=10)
        self.table.add_column("Thu", style=DAY_COLOR, justify="center", width=10)
        self.table.add_column("Fri", style=DAY_COLOR, justify="center", width=10)
        self.table.add_column("Sat", style=DAY_COLOR, justify="center", width=10)
        self.table.add_column("Sun", style=DAY_COLOR, justify="center", width=10)
        self.table.add_row(
            "1\n", " 1\n", " 2\n", " 3\n", " 4\n", " 5\n", " 6\n", " 7\n"
        )
        self.table.add_row(
            "2\n", " 8\n", " 9\n", "10\n", "11\n", "12\n", "13\n", "14\n"
        )
        self.table.add_row(
            "3\n", "15\n", "16\n", "17\n", "18\n", "19\n", "20\n", "21\n"
        )
        self.table.add_row(
            "4\n", "22\n", "23\n", "24\n", "25\n", "26\n", "27\n", "28\n"
        )
        return Static(self.table)


class WeeksViewApp(App):
    """An app to display the table and scrollable list."""

    CSS = """
    Screen {
        background: #2e2e2e; /* Dark grey  near perfect */
    }
    """
    BINDINGS = [
        ("?", "help", "Help"),
        ("q", "quit", ""),  # binds without displaying in footer
        # ("[", "scroll_left", "← 4wks"),
        # ("]", "scroll_right", "→ 4wks"),
        # ("{", "scroll_up", "↑ 1wk"),
        # ("}", "scroll_down", "↓ 1wk"),
        ("left", "scroll_left", "← 4wks"),
        ("right", "scroll_right", "→ 4wks"),
        ("up", "scroll_up", "↑ 1wk"),
        ("down", "scroll_down", "↓ 1wk"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.screen_title = "etm"
        # self.size = Size(80, 24)

    def on_mount(self) -> None:
        # self.title = "etm"
        self.title = "event and task manager"
        # self.view = self.compose()

    def action_quit(self):
        self.exit()

    def action_help(self):
        self.exit()

    def action_scroll_right(self):
        # self.exit()
        pass

    def action_scroll_left(self):
        pass

    def action_scroll_up(self):
        pass

    def action_scroll_down(self):
        pass

    def compose(self) -> ComposeResult:
        # Generate a list of 100 lines
        yield WeeksTable().table
        lines = [f" Line {i}" for i in range(100)]
        yield ScrollableList(lines)
        # yield Header(show_clock=True, time_format="%H:%M")
        yield Header()
        yield Footer()


if __name__ == "__main__":
    app = WeeksViewApp()
    app.run()
