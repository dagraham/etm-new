from logging import log
from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.strip import Strip
from textual.scroll_view import ScrollView
from textual.screen import Screen
from rich.segment import Segment
from textual.widgets import Markdown, Static, Footer, Header
from rich.table import Table
from rich.console import Console
from rich import box
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from datetime import datetime, timedelta
import string
from .common import log_msg, display_messages
from .__version__ import version as etm_version
from packaging.version import parse as parse_version
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Input
from textual.reactive import reactive
from textual.widgets import Label


VERSION = parse_version(etm_version)
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
MATCH_COLOR = NAMED_COLORS["Tomato"]


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


HelpText = f"""\
[bold][{HEADER_COLOR}]ETM {VERSION}[/{HEADER_COLOR}][/bold]
[bold][{HEADER_COLOR}]Application Keys[/{HEADER_COLOR}][/bold]
  [bold]escape[/bold]:      previous screen     [bold]Q[/bold]:         Quit etm
[bold][{HEADER_COLOR}]Search Keys[/{HEADER_COLOR}][/bold]
  [bold]/[/bold]:           Set search          [bold]N[/bold]:         Next match 
  [bold]escape[/bold]:      Clear search        [bold]P[/bold]:         Previous match           
[bold][{HEADER_COLOR}]Navigation Keys[/{HEADER_COLOR}][/bold]
  [bold]left[/bold]:        previous week       [bold]up[/bold]:        up in the list view     
  [bold]right[/bold]:       next week           [bold]down[/bold]:      down in the list view   
  [bold]shift+left[/bold]:  previous 4-weeks    [bold]period[/bold]:    center week
  [bold]shift+right[/bold]: next 4-weeks        [bold]space[/bold]:     current 4-weeks 
""".splitlines()


class CustomFooter(Static):
    """A customizable footer widget with dynamic content."""

    # Reactive attributes for dynamic updates
    search_active = reactive(False)
    search_string = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_active = False
        self.search_string = ""
        self.content = (
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        )

    def render(self) -> str:
        """Render the footer content."""
        log_msg(
            f"In CustomFooter render {self.search_active = }, {self.search_string = }"
        )
        return self.content

    def update_content(self, content: str):
        """Update the footer content."""
        log_msg(f"In CustomFooter update_content: {content}")
        self.content = content
        self.refresh()

    def set_normal_mode(self):
        """Switch to normal mode."""
        self.search_active = False
        self.search_string = ""

    def set_search_mode(self, search_string: str):
        """Switch to search mode with the given search string."""
        self.search_active = True
        self.search_string = search_string


class DetailsScreen(ModalScreen):
    """A temporary details screen."""

    def __init__(self, details: str):
        super().__init__()
        self.details = details

    def compose(self) -> ComposeResult:
        yield Static(f"Details:\n{self.details}")

    def on_key(self, event):
        if event.key == "escape":
            self.app.pop_screen()


class ScrollableList(ScrollView):
    """A scrollable list widget with a fixed title and search functionality."""

    def __init__(self, lines: list[str], **kwargs) -> None:
        super().__init__(**kwargs)

        # Extract the title and remaining lines
        self.title = Text.from_markup(lines[0]) if lines else Text("Untitled")
        self.lines = [Text.from_markup(line) for line in lines[1:]]  # Exclude the title
        self.virtual_size = Size(40, len(self.lines))  # Adjust virtual size for lines
        self.console = Console()
        self.search_term = None
        self.matches = []

    def set_search_term(self, search_term: str):
        """Set the search term, clear previous matches, and find new matches."""
        self.clear_search()  # Clear previous search results
        self.search_term = search_term.lower() if search_term else None
        self.matches = [
            i
            for i, line in enumerate(self.lines)
            if self.search_term and self.search_term in line.plain.lower()
        ]
        if self.matches:
            self.scroll_to(0, self.matches[0])  # Scroll to the first match
            self.refresh()

    def clear_search(self):
        """Clear the current search and remove all highlights."""
        self.search_term = None
        self.matches = []  # Clear the list of matches
        self.refresh()  # Refresh the view to remove highlights

    def render_line(self, y: int) -> Strip:
        """Render a single line of the list."""
        scroll_x, scroll_y = self.scroll_offset  # Current scroll position
        y += scroll_y  # Adjust for the current vertical scroll offset

        # If the line index is out of bounds, return an empty line
        if y < 0 or y >= len(self.lines):
            return Strip.blank(self.size.width)

        # Get the Rich Text object for the current line
        line_text = self.lines[y]

        # Highlight the line if it matches the search term
        if self.search_term and y in self.matches:
            line_text.stylize(f"bold {MATCH_COLOR}")  # Apply highlighting

        # Render the Rich Text into segments
        segments = list(line_text.render(self.console))

        # Adjust segments for horizontal scrolling
        cropped_segments = Segment.adjust_line_length(
            segments, self.size.width, style=None
        )

        return Strip(cropped_segments, self.size.width)


class DynamicViewApp(App):
    """A dynamic app that supports temporary and permanent view changes."""

    CSS_PATH = "view_textual.css"

    digit_buffer = reactive([])  # To store pressed characters
    afill = 1  # Number of characters needed to trigger a tag action

    BINDINGS = [
        ("?", "show_help", "Help"),
        ("Q", "quit", ""),
        (".", "center_week", ""),
        ("space", "current_period", ""),
        ("shift+left", "previous_period", ""),
        ("shift+right", "next_period", ""),
        ("left", "previous_week", ""),
        ("right", "next_week", ""),
        ("/", "start_search", ""),  # Keybinding for search
        ("N", "next_match", ""),
        ("P", "previous_match", ""),
        # No global esc binding here
    ]
    search_term = reactive("")  # Store the current search term

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        # self.title = "etm - event and task manager"
        self.title = ""
        self.view_mode = "list"  # Initial view is the ScrollableList

    def on_key(self, event):
        """Handle key events."""
        if event.key == "escape":
            if self.view_mode == "info":
                self.restore_list()
            elif self.view_mode == "list":
                self.action_clear_search()  # Use the new action for clearing the search
        elif event.key in "abcdefghijklmnopqrstuvwxyz":
            # Handle lowercase letters
            self.digit_buffer.append(event.key)
            if len(self.digit_buffer) == self.afill:
                base26_tag = "".join(self.digit_buffer)
                self.digit_buffer.clear()
                self.display_tag(base26_tag)

    def compose(self) -> ComposeResult:
        """Initial layout."""
        table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )

        # Create the ScrollableList instance
        scrollable_list = ScrollableList(details, id="list")
        custom_footer = CustomFooter(id="custom_footer")

        # Main container with a fixed title and scrollable content
        log_msg("Creating title widget")
        self.main_container = Vertical(
            Static(table, id="table"),
            Static(
                scrollable_list.title, id="list_title", classes="list-title"
            ),  # Title
            scrollable_list,  # Scrollable content
        )
        yield self.main_container
        # yield Footer(show_command_palette=False)
        yield custom_footer  # Use the corrected custom footer

    def update_footer(self, search_active: bool = False, search_string: str = ""):
        """Update the footer based on the current state."""
        log_msg(f"In update_footer {search_active = }, {search_string = }")
        if search_active:
            max_length = 20
            truncated_string = (
                f"{search_string[:max_length]}..."
                if len(search_string) > max_length
                else search_string
            )
            footer_content = f"[bold yellow]?[/bold yellow] Help, [bold yellow]/[/bold yellow] [bold {MATCH_COLOR}]{truncated_string}[/bold {MATCH_COLOR}], [bold yellow]N[/bold yellow] next, [bold yellow]P[/bold yellow] prev, [bold yellow]esc[/bold yellow] clear"
        else:
            footer_content = (
                "[bold yellow]?[/bold yellow] Help, [bold yellow]/[/bold yellow] Search"
            )
        log_msg(f"Updating footer with: {footer_content}")
        self.query_one("#custom_footer", Static).update_content(footer_content)

    def action_start_search(self):
        """Show the search input widget."""
        self.update_table_and_list()
        search_input = Input(placeholder="Search...", id="search")
        self.main_container.mount(search_input)
        self.set_focus(search_input)

    def on_input_submitted(self, event: Input.Submitted):
        """Handle the submission of the search input."""
        if event.input.id == "search":
            self.search_term = event.value  # Store the search term globally
            event.input.remove()  # Remove the input widget
            self.perform_search(self.search_term)

    def action_clear_search(self):
        """Clear the current search and reset the footer."""
        self.search_term = ""  # Clear the global search term
        scrollable_list = self.query_one("#list", ScrollableList)
        scrollable_list.clear_search()
        self.update_footer(search_active=False)
        self.update_table_and_list()

    def action_next_match(self):
        """Scroll to the next match."""
        scrollable_list = self.query_one("#list", ScrollableList)
        current_y = scrollable_list.scroll_offset.y
        next_match = next((i for i in scrollable_list.matches if i > current_y), None)
        if next_match is not None:
            scrollable_list.scroll_to(0, next_match)  # Use scroll_to for scrolling
            scrollable_list.refresh()

    def action_previous_match(self):
        """Scroll to the previous match."""
        scrollable_list = self.query_one("#list", ScrollableList)
        current_y = scrollable_list.scroll_offset.y
        previous_match = next(
            (i for i in reversed(scrollable_list.matches) if i < current_y), None
        )
        if previous_match is not None:
            scrollable_list.scroll_to(0, previous_match)  # Use scroll_to for scrolling
            scrollable_list.refresh()

    def perform_search(self, search_term: str):
        """Perform a search in the ScrollableList."""
        scrollable_list = self.query_one("#list", ScrollableList)
        scrollable_list.set_search_term(search_term)
        self.update_footer(search_active=True, search_string=search_term)
        scrollable_list.refresh()

    def action_show_help(self):
        """Show help content."""
        log_msg("Calling replace_list_with(HelpText)")
        self.replace_list_with(HelpText)

    def display_tag(self, tag: str):
        """Display details for the selected tag in the ScrollableList."""
        # Retrieve the corresponding item's details using the tag
        details = self.controller.process_tag(tag, self.selected_week)
        if details:
            # Replace the current list with the details
            self.replace_list_with(details.splitlines())
        else:
            # Optionally, show a message if no item matches the tag
            self.replace_list_with([f"No item found for tag: {tag}"])

    def action_quit(self):
        """Exit the app."""
        self.exit()

    def replace_list_with(self, lines: list[str]):
        """Replace the current ScrollableList with updated content, including a title."""
        # Extract the title (always the first line)
        if lines:
            title = lines[0]  # Use the first line as the title
            content_lines = lines[1:]  # Remaining lines as the scrollable content
        else:
            title = "Untitled"
            content_lines = []

        # Update the title widget
        self.query_one("#list_title", Static).update(title)

        # Reuse or replace the ScrollableList widget
        try:
            list_widget = self.query_one("#list", ScrollableList)
            list_widget.lines = [Text.from_markup(line) for line in content_lines]
            list_widget.virtual_size = Size(40, len(content_lines))
            list_widget.refresh()
        except LookupError:
            # Create and mount a new ScrollableList if it doesn't exist
            new_list = ScrollableList(content_lines, id="list")
            self.main_container.mount(
                new_list, after=self.query_one("#list_title", Static)
            )

        self.view_mode = "info"

    def restore_list(self):
        """Restore the original ScrollableList."""
        log_msg("in restore_list")

        # Find the table widget
        table_widget = self.query_one("#table", Static)

        # Reuse or create the title widget
        try:
            title_widget = self.query_one("#list_title", Static)
        except LookupError:
            log_msg("Creating title widget")
            title_widget = Static(id="list_title", classes="list-title")
            self.main_container.mount(title_widget, after=table_widget)

        # Get the table and details, extracting the title and content
        table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        if details:
            title = details[0]  # Use the first line as the title
            content_lines = details[1:]  # Remaining lines as the scrollable content
        else:
            title = "Untitled"
            content_lines = []

        # Update the title widget content
        title_widget.update(title)

        # Reuse or replace the ScrollableList
        log_msg("Reusing or replacing list widget")
        try:
            list_widget = self.query_one("#list", ScrollableList)
            log_msg("Reusing existing list widget")
            list_widget.lines = [Text.from_markup(line) for line in content_lines]
            list_widget.virtual_size = Size(
                40, len(content_lines)
            )  # Update virtual size
            list_widget.refresh()  # Refresh the list
        except LookupError:
            log_msg("Creating new list widget")
            list_widget = ScrollableList(content_lines, id="list")
            self.main_container.mount(list_widget, after=title_widget)

        # Update the view mode
        self.view_mode = "list"

    def action_show_details(self):
        """Show a temporary details screen for the selected item."""
        details = "Detailed information about the selected item."
        self.push_screen(DetailsScreen(details))

    # def update_table_and_list(self):
    #     """Update the table and scrollable list."""
    #     # Fetch the table and details
    #     table, details = self.controller.get_table_and_list(
    #         self.current_start_date, self.selected_week
    #     )
    #
    #     # Update the table widget
    #     self.query_one("#table", Static).update(table)
    #
    #     # Extract the title (always the first line) and update the title widget
    #     if details:
    #         title = details[
    #             0
    #         ]  # Use the first line as the title without modifying the list
    #         self.query_one("#list_title", Static).update(title)
    #
    #     # Update the scrollable list with the remaining lines
    #     scrollable_list = self.query_one("#list", ScrollableList)
    #     scrollable_list.lines = [
    #         Text.from_markup(line) for line in details[1:]
    #     ]  # Exclude title
    #     scrollable_list.virtual_size = Size(40, len(details[1:]))  # Adjust virtual size
    #     scrollable_list.refresh()  # Refresh the widget

    def update_table_and_list(self):
        """Update the table and scrollable list."""
        table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )

        # Update the table widget
        self.query_one("#table", Static).update(table)

        # Extract the title (always the first line) and update the title widget
        if details:
            title = details[0]  # Use the first line as the title
            self.query_one("#list_title", Static).update(title)

        # Update the scrollable list with the remaining lines
        scrollable_list = self.query_one("#list", ScrollableList)
        scrollable_list.lines = [
            Text.from_markup(line) for line in details[1:]
        ]  # Exclude title
        scrollable_list.virtual_size = Size(40, len(details[1:]))  # Adjust virtual size
        scrollable_list.refresh()

        # Reapply the search term if it's active
        if self.search_term:
            scrollable_list.set_search_term(self.search_term)

    def action_current_period(self):
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.update_table_and_list()

    def action_next_period(self):
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.update_table_and_list()

    def action_previous_period(self):
        self.current_start_date -= timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
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

    def action_refresh(self):
        self.update_table_and_list()

    def action_center_week(self):
        """Make the selected week the 2nd row of the 4-week period."""
        log_msg(f"{self.selected_week = }, {self.current_start_date = }")
        self.current_start_date = datetime.strptime(
            " ".join(map(str, [self.selected_week[0], self.selected_week[1], 1])),
            "%G %V %u",
        ) - timedelta(weeks=1)
        self.update_table_and_list()

    def action_replace_with_tree_view(self):
        """Replace the list view with a tree view."""
        self.main_container.mount(Static("Tree View: Replace this with your tree."))


if __name__ == "__main__":
    pass
