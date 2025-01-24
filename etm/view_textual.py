from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.strip import Strip
from textual.scroll_view import ScrollView
from textual.screen import Screen
from rich.segment import Segment
from textual.widgets import Static, Footer, Header
from rich.table import Table
from rich.console import Console
from rich import box
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from datetime import datetime, timedelta
import string
from .common import log_msg, display_messages

from rich.text import Text


DAY_COLOR = NAMED_COLORS["LemonChiffon"]
FRAME_COLOR = NAMED_COLORS["Khaki"]
HEADER_COLOR = NAMED_COLORS["CornflowerBlue"]
DIM_COLOR = NAMED_COLORS["DarkGray"]
EVENT_COLOR = NAMED_COLORS["LimeGreen"]
AVAILABLE_COLOR = NAMED_COLORS["LightSkyBlue"]
WAITING_COLOR = NAMED_COLORS["SlateGrey"]
FINISHED_COLOR = NAMED_COLORS["DarkGrey"]
GOAL_COLOR = NAMED_COLORS["GoldenRod"]
CHORE_COLOR = NAMED_COLORS["Khaki"]
PASTDUE_COLOR = NAMED_COLORS["DarkOrange"]
BEGIN_COLOR = NAMED_COLORS["Gold"]
INBOX_COLOR = NAMED_COLORS["OrangeRed"]
TODAY_COLOR = NAMED_COLORS["Tomato"]
# SELECTED_BACKGROUND = "#4d4d4d"
SELECTED_BACKGROUND = "#5d5d5d"


# SELECTED_COLOR = NAMED_COLORS["Yellow"]
SELECTED_COLOR = "bold yellow"

ONEDAY = timedelta(days=1)
ONEWK = 7 * ONEDAY
alpha = [x for x in string.ascii_lowercase]

TYPE_TO_COLOR = {
    "*": EVENT_COLOR,  # event
    "-": AVAILABLE_COLOR,  # available task
    "+": WAITING_COLOR,  # waiting task
    "%": FINISHED_COLOR,  # finished task
    "~": GOAL_COLOR,  # goal
    "^": CHORE_COLOR,  # chore
    "<": PASTDUE_COLOR,  # past due task
    ">": BEGIN_COLOR,  # begin
    "!": INBOX_COLOR,  # inbox
}


def format_date_range(start_dt: datetime, end_dt: datetime):
    """
    Format a datetime object as a week string, taking not to repeat the month name unless the week spans two months.
    """
    same_year = start_dt.year == end_dt.year
    same_month = start_dt.month == end_dt.month
    # same_day = start_dt.day == end_dt.day
    if same_year and same_month:
        return f"{start_dt.strftime('%B %-d')} - {end_dt.strftime('%-d, %Y')}"
    elif same_year and not same_month:
        return f"{start_dt.strftime('%B %-d')} - {end_dt.strftime('%B %-d, %Y')}"
    else:
        return f"{start_dt.strftime('%B %-d, %Y')} - {end_dt.strftime('%B %-d, %Y')}"


def decimal_to_base26(decimal_num):
    """
    Convert a decimal number to its equivalent base-26 string.

    Args:
        decimal_num (int): The decimal number to convert.

    Returns:
        str: The base-26 representation where 'a' = 0, 'b' = 1, ..., 'z' = 25.
    """
    if decimal_num < 0:
        raise ValueError("Decimal number must be non-negative.")

    if decimal_num == 0:
        return "a"  # Special case for zero

    base26 = ""
    while decimal_num > 0:
        digit = decimal_num % 26
        base26 = chr(digit + ord("a")) + base26  # Map digit to 'a'-'z'
        decimal_num //= 26

    return base26


def get_previous_yrwk(year, week):
    """
    Get the previous (year, week) from an ISO calendar (year, week).
    """
    # Convert the ISO year and week to a Monday date
    monday_date = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    # Subtract 1 week
    previous_monday = monday_date - timedelta(weeks=1)
    # Get the ISO year and week of the new date
    return previous_monday.isocalendar()[:2]


def get_next_yrwk(year, week):
    """
    Get the next (year, week) from an ISO calendar (year, week).
    """
    # Convert the ISO year and week to a Monday date
    monday_date = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    # Add 1 week
    next_monday = monday_date + timedelta(weeks=1)
    # Get the ISO year and week of the new date
    return next_monday.isocalendar()[:2]


def calculate_4_week_start():
    """
    Calculate the starting date of the 4-week period, starting on a Monday.
    """
    today = datetime.now()
    iso_year, iso_week, iso_weekday = today.isocalendar()
    # start_of_week = datetime.strptime(
    #     " ".join(map(str, [iso_year, iso_week, 1])), "%G %V %u"
    # )
    start_of_week = today - timedelta(days=iso_weekday - 1)
    weeks_into_cycle = (iso_week - 1) % 4
    return start_of_week - timedelta(weeks=weeks_into_cycle)


# class ScrollableList(ScrollView):
#     """A scrollable list widget."""
#
#     def __init__(self, lines: list[str]) -> None:
#         super().__init__()
#         self.lines = lines
#         self.virtual_size = Size(
#             40, len(lines)
#         )  # Width 40, height equals number of lines
#
#     def render_line(self, y: int) -> Strip:
#         """Render a single line of the list."""
#         scroll_x, scroll_y = self.scroll_offset  # Current scroll position
#         y += scroll_y  # Adjust for the current vertical scroll offset
#
#         # If the line index is out of bounds, return an empty line
#         if y < 0 or y >= len(self.lines):
#             return Strip.blank(self.size.width)
#
#         # Get the line text and create a segment for it
#         line_text = self.lines[y]
#         segment = Segment(line_text.ljust(self.size.width))  # Left-align and pad
#         return Strip([segment], self.size.width)
#


class ScrollableList(ScrollView):
    """A scrollable list widget that supports Rich formatting."""

    def __init__(self, lines: list[str]) -> None:
        super().__init__()
        # Convert strings with Rich markup into Rich Text objects
        self.lines = [Text.from_markup(line) for line in lines]
        # Set virtual size based on the number of lines
        self.virtual_size = Size(40, len(lines))  # Width 40, height = number of lines
        self.console = Console()  # Create a Console instance for rendering

    def render_line(self, y: int) -> Strip:
        """Render a single line of the list."""
        scroll_x, scroll_y = self.scroll_offset  # Current scroll position
        y += scroll_y  # Adjust for the current vertical scroll offset

        # If the line index is out of bounds, return an empty line
        if y < 0 or y >= len(self.lines):
            return Strip.blank(self.size.width)

        # Get the Rich Text object for the current line
        line_text = self.lines[y]

        # Render the Rich Text into segments
        segments = list(line_text.render(self.console))

        # Adjust segments for horizontal scrolling
        cropped_segments = Segment.adjust_line_length(
            segments, self.size.width, style=None
        )

        # Create a Strip object from the segments
        return Strip(cropped_segments, self.size.width)


class WeeksViewApp(App):
    """An app to display the table and scrollable list."""

    CSS_PATH = "view_textual.css"

    BINDINGS = [
        ("?", "help", "Help"),
        ("q", "quit", "Quit"),  # binds without displaying in footer
        # ("[", "scroll_left", "← 4wks"),
        # ("]", "scroll_right", "→ 4wks"),
        # ("{", "scroll_up", "↑ 1wk"),
        # ("}", "scroll_down", "↓ 1wk"),
        ("space", "current_period", ""),
        ("shift+left", "previous_period", ""),
        ("shift+right", "next_period", ""),
        ("left", "previous_week", ""),
        ("right", "next_week", ""),
    ]

    def __init__(self, controller) -> None:
        super().__init__()
        self.screen_title = "etm"
        self.controller = controller
        self.current_start_date = calculate_4_week_start()
        self.digit_buffer = []  # Buffer for storing two-digit input
        self.selected_week = tuple(
            datetime.now().isocalendar()[:2]
        )  # Currently selected week
        self.yrwk_to_details = {}  # Maps (iso_year, iso_week), to the details for that week

        self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week) for the current period
        self.afill = 1
        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.scroll_offset = 0  # Keeps track of scrolling position

    def on_mount(self) -> None:
        # self.title = "etm"
        self.title = "event and task manager"
        self.view = self.compose()

    def action_quit(self):
        self.exit()

    def action_help(self):
        self.exit()

    def update_table_and_list(self):
        table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        # Update the table and scrollable list
        self.query_one(Static).update(table)  # Update the table
        self.query_one(ScrollableList).lines = [
            Text.from_markup(line) for line in details
        ]
        self.query_one(ScrollableList).virtual_size = Size(
            40, len(details)
        )  # Update virtual size
        self.query_one(ScrollableList).refresh()  # Refresh the scrollable list

    def action_next_period(self):
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        log_msg(f"{self.current_start_date = }, {self.selected_week = }")
        self.update_table_and_list()

    def action_previous_period(self):
        self.current_start_date -= timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        self.update_table_and_list()

    def action_previous_week(self):
        self.selected_week = get_previous_yrwk(*self.selected_week)
        if self.selected_week < tuple((self.current_start_date).isocalendar()[:2]):
            self.current_start_date -= timedelta(weeks=1)
        self.update_table_and_list()

    def action_next_week(self):
        self.selected_week = get_next_yrwk(*self.selected_week)
        if self.selected_week > tuple(
            (self.current_start_date + timedelta(weeks=4) - ONEDAY).isocalendar()[:2]
        ):
            self.current_start_date += timedelta(weeks=1)

        self.update_table_and_list()

    def action_current_period(self):
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.update_table_and_list()

    def compose(self) -> ComposeResult:
        log_msg(f"{self.current_start_date = }, {self.selected_week = }")
        table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        yield Static(table)
        yield ScrollableList(details)
        # yield Header(show_clock=True, time_format="%H:%M")
        yield Header()
        yield Footer()


if __name__ == "__main__":
    pass
