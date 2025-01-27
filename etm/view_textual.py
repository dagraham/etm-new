from .__version__ import version as etm_version
from .common import log_msg, display_messages
from datetime import datetime, timedelta
from logging import log
from packaging.version import parse as parse_version
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from rich import box
from rich.console import Console
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.geometry import Size
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Input
from textual.widgets import Label
from textual.widgets import Markdown, Static, Footer, Header
import string


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


class DetailsScreen(ModalScreen):
    """A temporary details screen."""

    def __init__(self, details: str):
        super().__init__()
        self.details = details

    def compose(self) -> ComposeResult:
        yield Static(f"Details\n{self.details}")

    def on_key(self, event):
        if event.key == "escape":
            self.app.pop_screen()


class SearchScreen(Screen):
    """A screen to handle search input and display results."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.search_term = None  # Store the search term
        self.results = []  # Store search results

    def compose(self) -> ComposeResult:
        # Display search input at the top
        yield Input(placeholder="Enter search term...", id="search_input")
        # Display the scrollable list for search results
        yield ScrollableList([], id="search_results")
        # Display a footer
        yield Static(
            "[bold yellow]?[/bold yellow] Help [bold yellow]ESC[/bold yellow] Back",
            id="custom_footer",
        )

    def on_input_submitted(self, event: Input.Submitted):
        """Handle the submission of the search input."""
        if event.input.id == "search_input":
            self.search_term = event.value  # Capture the search term
            self.query_one("#search_input", Input).remove()  # Remove the input
            self.perform_search(self.search_term)  # Perform the search

    def perform_search(self, search_term: str):
        """Perform the search and update the results."""
        self.results = self.controller.find_records(search_term)  # Query controller
        scrollable_list = self.query_one("#search_results", ScrollableList)
        if self.results:
            # Populate the scrollable list with results
            scrollable_list.lines = [Text.from_markup(line) for line in self.results]
        else:
            # Display a message if no results are found
            scrollable_list.lines = [Text("No matches found.")]
        scrollable_list.refresh()

    def on_key(self, event):
        """Handle key presses."""
        if event.key == "escape":
            # Return to the previous screen
            self.app.pop_screen()


class ScrollableList(ScrollView):
    """A scrollable list widget with a fixed title and search functionality."""

    def __init__(self, lines: list[str], **kwargs) -> None:
        super().__init__(**kwargs)

        # Extract the title and remaining lines
        # self.title = Text.from_markup(title) if title else Text("Untitled")
        self.lines = [Text.from_markup(line) for line in lines]  # Exclude the title
        self.virtual_size = Size(40, len(self.lines))  # Adjust virtual size for lines
        self.console = Console()
        self.search_term = None
        self.matches = []

    def set_search_term(self, search_term: str):
        """Set the search term, clear previous matches, and find new matches."""
        log_msg(f"Setting search term: {search_term}")
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
        line_text = self.lines[y].copy()  # Create a copy to apply styles dynamically

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


class WeeksScreen(Screen):
    """Weeks view screen."""

    def __init__(
        self,
        title: str,
        table: str,
        details: list[str],
        footer_content: str = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search",
    ):
        super().__init__()
        self.table_title = title
        self.table = table
        self.list_title = details[0]
        self.lines = details[1:]
        self.footer_content = footer_content

    def compose(self) -> ComposeResult:
        # Display the table
        yield Static(self.table_title, id="table_title", classes="list-title")
        yield Static(self.table, id="table", classes="weeks-table")

        # Display the title and scrollable list
        yield Static(self.list_title, id="list_title", classes="list-title")
        yield ScrollableList(self.lines, id="list")  # Using "list" as the ID
        yield Static(self.footer_content, id="custom_footer")


class FullScreenList(Screen):
    """Reusable full-screen list for Last, Next, and Find views."""

    def __init__(
        self,
        details: list[str],
        footer_content: str = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search",
    ):
        super().__init__()
        if details:
            self.title = details[0]  # First line is the title
            self.lines = details[1:]  # Remaining lines are scrollable content
        else:
            self.title = "Untitled"
            self.lines = []
        self.footer_content = footer_content

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        yield Static(self.title, id="list_title", classes="list-title")
        yield ScrollableList(self.lines, id="list")  # Using "list" as the ID
        yield Static(self.footer_content, id="custom_footer")


class DynamicViewApp(App):
    """A dynamic app that supports temporary and permanent view changes."""

    CSS_PATH = "view_textual.css"

    digit_buffer = reactive([])  # To store pressed characters
    afill = 1  # Number of characters needed to trigger a tag action

    BINDINGS = [
        (".", "center_week", ""),
        ("space", "current_period", ""),
        ("shift+left", "previous_period", ""),
        ("shift+right", "next_period", ""),
        ("left", "previous_week", ""),
        ("right", "next_week", ""),
        ("L", "show_last", "Show Last"),  # Bind 'L' for Last Instances
        ("N", "show_next", "Show Next"),  # Bind 'N' for Next Instances
        ("F", "show_find", "Find"),  # Bind 'F' for Find
        ("W", "show_weeks", "Show Weeks"),  # Bind 'W' for Weeks view
        ("?", "show_help", "Help"),
        ("Q", "quit", "Quit"),
        ("/", "start_search", "Search"),
        (">", "next_match", "Next Match"),
        ("<", "previous_match", "Previous Match"),
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
        self.view = "week"
        self.saved_lines = []

    def on_key(self, event):
        """Handle key events."""
        if event.key == "escape":
            if self.view_mode == "info":
                # self.action_clear_info()  # Use the new action for clearing the search
                self.restore_list()
            else:
                self.action_clear_search()  # Use the new action for clearing the search
        elif event.key in "abcdefghijklmnopqrstuvwxyz":
            # Handle lowercase letters
            self.digit_buffer.append(event.key)
            if len(self.digit_buffer) == self.afill:
                base26_tag = "".join(self.digit_buffer)
                self.digit_buffer.clear()
                self.action_show_details(base26_tag)

    def on_mount(self):
        """Initial layout for the default view (Weeks)."""
        # Fetch the default table and details for the Weeks view
        self.action_show_weeks()

    def mount_full_screen_list(self, details: list[str], footer_content: str):
        """Mount a full-screen list with the given details and footer content."""
        if details:
            title = details[0]
            lines = details[1:]
        else:
            title = "Untitled"
            lines = []

        # Create and mount the full-screen list
        full_screen_list = FullScreenList(details, footer_content)
        self.mount(full_screen_list)  # Mount the full-screen list directly

    def update_scrollable_list(self, lines: list[str], title: str):
        """Update the ScrollableList with new content."""
        try:
            # Update the title widget
            title_widget = self.query_one("#list_title", Static)
            title_widget.update(title)
        except LookupError:
            # Handle case where title widget doesn't exist (unlikely)
            pass

        # Update or refresh the ScrollableList
        try:
            scrollable_list = self.query_one("#list", ScrollableList)
            scrollable_list.lines = [Text.from_markup(line) for line in lines]
            scrollable_list.refresh()
        except LookupError:
            # If no ScrollableList exists, log or handle as needed
            pass

    def action_show_weeks(self):
        """Switch back to the Weeks view."""
        self.view = "week"
        title, table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        self.afill = 1 if len(details) <= 26 else 2 if len(details) <= 676 else 3
        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        self.push_screen(WeeksScreen(title, table, details, footer))

    def action_show_last(self):
        """Show the 'Last' view."""
        self.view = "last"
        details = self.controller.get_last()
        self.afill = 1 if len(details) <= 26 else 2 if len(details) <= 676 else 3
        footer = (
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] ESC Back"
        )
        self.push_screen(FullScreenList(details, footer))

    def action_show_next(self):
        """Show the 'Next' view."""
        self.view = "next"
        details = self.controller.get_next()
        self.afill = 1 if len(details) <= 26 else 2 if len(details) <= 676 else 3
        footer = (
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] ESC Back"
        )
        self.push_screen(FullScreenList(details, footer))

    def action_show_find(self):
        """Show the 'Find' view."""
        search_input = Input(
            placeholder="Enter search term for item name or details ...",
            id="find_input",
        )
        self.mount(search_input)  # Mount the search input widget
        self.set_focus(search_input)  # Focus on the search input

    def on_input_submitted(self, event: Input.Submitted):
        """Handle submission from search or find input."""
        search_term = event.value  # Get the submitted search term
        event.input.remove()  # Remove the input widget after submission

        if event.input.id == "find_input":
            self.view = "find"
            # Handle the 'Find' view
            results = self.controller.find_records(search_term)  # Fetch results
            footer = (
                "[bold yellow]?[/bold yellow] Help "
                "[bold yellow]ESC[/bold yellow] Back "
                '[bold yellow]"/"[/bold yellow] Search'
            )
            # Mount a FullScreenList to display the results
            self.push_screen(FullScreenList(results))
            # self.mount_full_screen_list(results, footer)

        elif event.input.id == "search":
            # Handle inline search in the current list
            self.perform_search(search_term)  # Perform the search in the active list

    def update_footer(self, search_active: bool = False, search_string: str = ""):
        """Update the footer based on the current state."""
        if search_active:
            max_length = 20
            truncated_string = (
                f"{search_string[:max_length]}..."
                if len(search_string) > max_length
                else search_string
            )
            footer_content = f"[bold yellow]?[/bold yellow] Help, [bold yellow]/[/bold yellow] [bold {MATCH_COLOR}]{truncated_string}[/bold {MATCH_COLOR}], [bold yellow]>[/bold yellow] next, [bold yellow]<[/bold yellow] prev, [bold yellow]esc[/bold yellow] clear"
        else:
            footer_content = (
                "[bold yellow]?[/bold yellow] Help, [bold yellow]/[/bold yellow] Search"
            )

        self.query_one("#custom_footer", Static).update_content(footer_content)

    def action_start_search(self):
        """Show the search input widget."""
        self.search_term = ""  # Clear the previous search term
        search_input = Input(placeholder="Search...", id="search")
        self.query_one("#custom_footer", Static).update(
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search Mode"
        )
        # self.push_screen(search_input)
        self.mount(search_input)  # Mount the search input widget to the app
        self.set_focus(search_input)

    def action_start_search(self):
        """Show the search input widget for inline search."""
        search_input = Input(placeholder="Search...", id="search")
        self.mount(search_input)
        self.set_focus(search_input)

    def action_clear_info(self):
        try:
            footer = self.query_one("#custom_footer", Static)
            footer.update(
                "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
            )
        except LookupError:
            log_msg("Footer not found to update.")

    def action_clear_search(self):
        """Clear the current search and reset the footer."""
        self.search_term = ""  # Clear the global search term
        try:
            # Find the active ScrollableList and clear the search
            scrollable_list = self.query_one("#list", ScrollableList)
            scrollable_list.clear_search()
            scrollable_list.refresh()
        except LookupError:
            log_msg("No active ScrollableList found to clear search.")

        # Update the footer to reflect the cleared search state
        try:
            footer = self.query_one("#custom_footer", Static)
            footer.update(
                "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
            )
        except LookupError:
            log_msg("Footer not found to update.")

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

    def action_next_match(self):
        """Scroll to the next match."""
        try:
            scrollable_list = self.query_one("#list", ScrollableList)
            current_y = scrollable_list.scroll_offset.y
            next_match = next(
                (i for i in scrollable_list.matches if i > current_y), None
            )
            if next_match is not None:
                scrollable_list.scroll_to(0, next_match)  # Scroll to the next match
                scrollable_list.refresh()
            else:
                log_msg("No next match found.")
        except LookupError:
            log_msg("No active ScrollableList found for next match.")

    def action_previous_match(self):
        """Scroll to the previous match."""
        try:
            scrollable_list = self.query_one("#list", ScrollableList)
            current_y = scrollable_list.scroll_offset.y
            previous_match = next(
                (i for i in reversed(scrollable_list.matches) if i < current_y), None
            )
            if previous_match is not None:
                scrollable_list.scroll_to(
                    0, previous_match
                )  # Scroll to the previous match
                scrollable_list.refresh()
            else:
                log_msg("No previous match found.")
        except LookupError:
            log_msg("No active ScrollableList found for previous match.")

    def perform_search(self, search_term: str):
        """Perform a search in the currently active view."""
        self.search_term = search_term  # Update the search term globally
        try:
            # Find the ScrollableList in the current view
            scrollable_list = self.query_one("#list", ScrollableList)
            scrollable_list.set_search_term(search_term)
            scrollable_list.refresh()
        except LookupError:
            log_msg("No active ScrollableList found for the current view.")

    def action_show_help(self):
        self.push_screen(DetailsScreen("\n".join(HelpText)))

    def action_show_details(self, tag: str):
        """Show a temporary details screen for the selected item."""
        details = self.controller.process_tag(tag, self.view)
        self.push_screen(DetailsScreen(details))

    def action_quit(self):
        """Exit the app."""
        self.exit()

    # def replace_list_with(self, lines: list[str]):
    #     """Replace the current ScrollableList with updated content, including a title."""
    #     # Extract the title (always the first line)
    #     if lines:
    #         title = lines[0]  # Use the first line as the title
    #         content_lines = lines[1:]  # Remaining lines as the scrollable content
    #     else:
    #         title = "Untitled"
    #         content_lines = []
    #
    #     # Update the title widget
    #     self.query_one("#list_title", Static).update(title)
    #
    #     # Reuse or replace the ScrollableList widget
    #     try:
    #         list_widget = self.query_one("#list", ScrollableList)
    #         self.saved_lines = list_widget.lines
    #         list_widget.lines = [Text.from_markup(line) for line in content_lines]
    #         list_widget.virtual_size = Size(40, len(content_lines))
    #         list_widget.refresh()
    #     except LookupError:
    #         # Create and mount a new ScrollableList if it doesn't exist
    #         new_list = ScrollableList(content_lines, id="list")
    #         self.main_container.mount(
    #             new_list, after=self.query_one("#list_title", Static)
    #         )
    #
    #     # self.view_mode = "info"
    #
    # def restore_list(self):
    #     try:
    #         list_widget = self.query_one("#list", ScrollableList)
    #         list_widget.lines = self.saved_lines
    #         list_widget.refresh()
    #     except LookupError:
    #         # Create and mount a new ScrollableList if it doesn't exist
    #         new_list = ScrollableList(content_lines, id="list")
    #         self.main_container.mount(
    #             new_list, after=self.query_one("#list_title", Static)
    #         )
    #     # if self.view == "week":
    #     #     self.action_show_weeks()
    #     #     # """Restore the Weeks view."""
    #     #     # self.update_table_and_list()
    #     #     # self.view_mode = "weeks"
    #     #     # self.update_footer()
    #     # elif self.view == "last":
    #     #     self.action_show_last()
    #     # elif self.view == "next":
    #     #     self.action_show_next()
    #     # elif self.view == "find":
    #     #     self.action_show_find()
    #

    def update_table_and_list(self):
        """Update the table and scrollable list."""
        title, table, details = self.controller.get_table_and_list(
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
