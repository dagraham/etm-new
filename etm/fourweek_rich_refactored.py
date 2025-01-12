from datetime import datetime, timedelta
from sre_compile import dis
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from rich.console import Console
from rich.table import Table
from rich.columns import Columns
from rich.console import Group, group
from rich.panel import Panel
from rich.layout import Layout
from rich import print as rprint
import re
import inspect
from rich.theme import Theme
from rich import box

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import PromptSession
import string
import shutil


DAY_COLOR = NAMED_COLORS["LightSkyBlue"]
BUSY_COLOR = NAMED_COLORS["LightSlateGray"]
CONF_COLOR = NAMED_COLORS["DarkOrange"]
DIM_COLOR = NAMED_COLORS["LightSlateGray"]
EVENT_COLOR = NAMED_COLORS["LimeGreen"]
AVAILABLE_COLOR = NAMED_COLORS["LightSkyBlue"]
WAITING_COLOR = NAMED_COLORS["SlateGrey"]
FINISHED_COLOR = NAMED_COLORS["DarkGrey"]
GOAL_COLOR = NAMED_COLORS["GoldenRod"]
CHORE_COLOR = NAMED_COLORS["Khaki"]
PASTDUE_COLOR = NAMED_COLORS["DarkOrange"]
BEGIN_COLOR = NAMED_COLORS["Gold"]
INBOX_COLOR = NAMED_COLORS["OrangeRed"]


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

# TODO: Add a setting to show unscheduled events
show_unscheduled = False

messages = []


def log_msg(msg: str):
    global messages
    caller_name = inspect.stack()[1].function
    messages.append(f"[yellow]{caller_name}[/yellow]:\n  {msg}")


def display_messages():
    global messages
    for msg in messages:
        rprint(msg)


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


def base26_to_decimal(base26_num):
    """
    Convert an arbitrary-length base-26 number to its decimal equivalent.

    Args:
        base26_num (str): A base-26 string using 'a' as 0 and 'z' as 25.

    Returns:
        int: The decimal equivalent of the base-26 number.
    """
    decimal_value = 0
    length = len(base26_num)

    # Process each character in the base-26 string
    for i, char in enumerate(base26_num):
        digit = ord(char) - ord("a")  # Map 'a' to 0, ..., 'z' to 25
        power = length - i - 1  # Compute the power of 26
        decimal_value += digit * (26**power)

    return decimal_value


def indx_to_tag(indx: int, fill: int = 1):
    """
    Convert an index to a base-26 tag.
    """
    return decimal_to_base26(indx).ljust(fill, "a")


log_msg(f"""
    {decimal_to_base26(0) = }   
    {decimal_to_base26(1) = }
    {decimal_to_base26(25) = }
    {decimal_to_base26(26) = }
    {decimal_to_base26(675) = }
    {base26_to_decimal("a") = }
    {base26_to_decimal("b") = }
    {base26_to_decimal("z") = }
    {base26_to_decimal("ba") = }
    {base26_to_decimal("gz") = }
""")


def base26_to_decimal(base26_num):
    """
    Convert a 2-digit base-26 number to its decimal equivalent.

    Args:
        base26_num (str): A 2-character string in base-26 using 'a' as 0 and 'z' as 25.

    Returns:
        int: The decimal equivalent of the base-26 number.
    """
    # Ensure the input is exactly 2 characters
    if len(base26_num) != 2:
        raise ValueError("Input must be a 2-character base-26 number.")

    # Map each character to its base-26 value
    digit1 = ord(base26_num[0]) - ord("a")  # First character
    digit2 = ord(base26_num[1]) - ord("a")  # Second character

    # Compute the decimal value
    decimal_value = digit1 * 26**1 + digit2 * 26**0

    return decimal_value


class FourWeekView:
    def __init__(self, db_manager, bindings):
        """
        Initialize the FourWeekView with a database manager.
        """
        self.db_manager = db_manager
        self.console = Console(theme=Theme({}))
        # self.console = Console()
        self.current_start_date = self.calculate_4_week_start()
        self.key_bindings = bindings
        self.digit_buffer = []  # Buffer for storing two-digit input
        self.selected_day = datetime.now().strftime(
            "%-d"
        )  # Currently selected date (month day as string)
        self.selected_week = tuple(
            datetime.now().isocalendar()[:2]
        )  # Currently selected week
        # self.monthday_to_details = {}  # Maps month days to their details
        self.yrwk_to_details = {}  # Maps (iso_year, iso_week), to the details for that week
        self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week) for the current period
        self.afill = 1
        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.setup_key_bindings()

    def bind_keys(self, bindings):
        """
        Bind keys dynamically based on the current `afill` value.
        """
        for char in "abcdefghijklmnopqrstuvwxyz":

            @bindings.add(char)
            def _(event, char=char):
                self.digit_buffer.append(char)
                if len(self.digit_buffer) == self.afill:
                    base26_tag = "".join(self.digit_buffer)
                    self.digit_buffer.clear()
                    self.process_tag(base26_tag)

    def setup_key_bindings(self):
        """
        Set up key bindings for navigation, actions, and date selection.
        """
        # bindings = KeyBindings()

        # Navigation
        self.key_bindings.add("right")(lambda _: self.move_next_period())
        self.key_bindings.add("left")(lambda _: self.move_previous_period())
        self.key_bindings.add("space")(lambda _: self.reset_to_today())
        self.key_bindings.add("Q")(lambda _: self.quit())

        # Add key bindings for digits
        for digit in [str(x) for x in range(1, 5)]:

            @self.key_bindings.add(digit)
            def _(_, digit=digit):
                log_msg(f"Processing digit: {digit}, {type(digit) = }")
                yr_wk = self.rownum_to_yrwk[int(digit)]
                log_msg(f"Selected week: {yr_wk}")
                self.selected_week = yr_wk
                self.refresh_display()

        for char in "abcdefghijklmnopqrstuvwxyz":

            @self.key_bindings.add(char)
            def _(event, char=char):
                self.digit_buffer.append(char)
                if len(self.digit_buffer) == self.afill:
                    base26_tag = "".join(self.digit_buffer)
                    self.digit_buffer.clear()
                    self.process_tag(base26_tag)

    def process_tag(self, tag):
        """
        Process the base26 tag entered by the user.
        """
        log_msg(
            f"Processing tag: {tag = }, {self.tag_to_id[self.selected_week].get(tag) = }"
        )
        if tag in self.tag_to_id[self.selected_week]:
            record_id = self.tag_to_id[self.selected_week][tag]
            print(f"Tag '{tag}' corresponds to record ID {record_id}")
        else:
            print(f"Invalid tag: '{tag}'")

    def calculate_4_week_start(self):
        """
        Calculate the starting date of the 4-week period, starting on a Monday.
        """
        today = datetime.now()
        iso_year, iso_week, iso_weekday = today.isocalendar()
        start_of_week = today - timedelta(days=iso_weekday - 1)
        weeks_into_cycle = (iso_week - 1) % 4
        return start_of_week - timedelta(weeks=weeks_into_cycle)

    def generate_table(self, grouped_events):
        """
        Generate a Rich table displaying events for the specified 4-week period.
        """
        end_date = (
            self.current_start_date + timedelta(weeks=4) - ONEDAY
        )  # End on a Sunday
        start_date = self.current_start_date
        now_year, now_week, now_day = datetime.now().isocalendar()
        title = (
            # f"{start_date.strftime('%B %-d')} – {end_date.strftime('%B %-d, %Y')}"
            f"{format_date_range(start_date, end_date)}"
            if start_date.year == end_date.year
            else f"{start_date.strftime('%B %-d, %Y')} – {end_date.strftime('%B %-d, %Y')}"
        )

        table = Table(
            show_header=True,
            header_style="bold blue",
            show_lines=True,
            expand=True,
            box=box.SQUARE,
            title=title,
        )

        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        table.add_column(f"[{DIM_COLOR}]Wk[/{DIM_COLOR}]", justify="center", width=6)
        for day in weekdays:
            table.add_column(day, justify="center", style=DAY_COLOR, width=10)

        # self.monthday_to_details = {}  # Reset for this period
        self.rownum_to_details = {}  # Reset for this period
        current_date = self.current_start_date
        weeks = []
        row_num = 0
        while current_date <= end_date:
            yr_wk = current_date.isocalendar()[:2]
            iso_year, iso_week = yr_wk
            if yr_wk not in weeks:
                weeks.append(yr_wk)
            row_num += 1
            self.rownum_to_yrwk[row_num] = yr_wk
            if yr_wk == self.selected_week:
                row = [f"[reverse][bold][yellow]{row_num}[yellow][/bold][/reverse]\n"]
            else:
                row = [f"[{DIM_COLOR}]{row_num}[{DIM_COLOR}]\n"]
            for weekday in range(1, 8):  # ISO weekdays: 1 = Monday, 7 = Sunday
                date = datetime.strptime(f"{iso_year} {iso_week} {weekday}", "%G %V %u")
                monthday_str = date.strftime(
                    "%-d"
                )  # Month day as string without leading zero
                events = (
                    grouped_events.get(iso_year, {}).get(iso_week, {}).get(weekday, [])
                )
                today = (
                    iso_year == now_year and iso_week == now_week and weekday == now_day
                )

                mday = monthday_str
                if today:
                    mday = f"[bold][yellow]{monthday_str}[/yellow][/bold]"
                # if self.selected_day and monthday_str == self.selected_day:
                #     mday = f"[reverse][bold][yellow]{mday}[/yellow][/bold][/reverse]"

                if events:
                    tups = [
                        self.db_manager.event_tuple_to_minutes(ev[0], ev[1])
                        for ev in events
                    ]
                    aday_str, busy_str = self.db_manager.get_busy_bar(tups)
                    if aday_str:
                        row.append(f"{aday_str} {mday} {aday_str}{busy_str}")
                    else:
                        row.append(f"{mday}{busy_str}")
                else:
                    row.append(f"{mday}\n")

                # Populate monthday_to_details
                # self.monthday_to_details[monthday_str], tag_to_id = (
                #     self.get_day_details(date)
                # )

            table.add_row(*row)
            self.yrwk_to_details[yr_wk] = self.get_week_details((iso_year, iso_week))
            current_date += timedelta(weeks=1)

        return table

    def refresh_display(self, details=None):
        """
        Refresh the display by fetching and processing events, generating the table,
        and rendering the details below the table in a panel group.

        Args:
            details (str, optional): The details to display below the table. Defaults to None.
        """
        current_start_year, current_start_week, _ = (
            self.current_start_date.isocalendar()
        )
        self.db_manager.extend_datetimes_for_weeks(
            current_start_year, current_start_week, 4
        )
        grouped_events = self.db_manager.process_events(
            self.current_start_date, self.current_start_date + timedelta(weeks=4)
        )

        # Generate the table
        table = self.generate_table(grouped_events)

        # Auto-select today's date if within the displayed period
        today = datetime.now()
        today_str = today.strftime("%-d")  # Month day without leading zero
        # if details is None and today_str in self.monthday_to_details:
        #     self.selected_day = today_str
        #     details = self.monthday_to_details[today_str]
        # elif details is None:
        #     self.selected_day = None
        #     details = "No date selected."

        if self.selected_week in self.yrwk_to_details:
            details = self.yrwk_to_details[self.selected_week]
        else:
            details = "No week selected."

        # Create a panel group for the table and details
        panel_group = Group(
            table,
            # Panel(details, title="Details", border_style="blue"),
            details,
            # "Navigation: [bold]>[/bold] Next Period, [bold]<[/bold] Previous Period, [bold].[/bold] Today, [bold]Q[/bold] Quit, [bold]2-digit date[/bold] for Details"
        )

        # Clear the console and render the panel group
        self.console.clear()
        self.console.print(panel_group)

    def get_week_details(self, yr_wk):
        """
        Fetch and format details for a specific week.
        """
        start_datetime = datetime.strptime(f"{yr_wk[0]} {yr_wk[1]} 1", "%G %V %u")

        end_datetime = start_datetime + timedelta(weeks=1)
        # log_msg(f"start_datetime: {start_datetime}, end_datetime: {end_datetime}")
        events = self.db_manager.get_events_for_period(start_datetime, end_datetime)
        this_week = format_date_range(start_datetime, end_datetime - ONEDAY)
        terminal_width = shutil.get_terminal_size().columns

        header = f"Items for {this_week} ({len(events)})"
        details = [f"[not bold][yellow]{header:^{terminal_width}}[/yellow][/not bold]"]

        if not events:
            details.append("Nothing scheduled for this week")
            return "\n".join(details), {}

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        self.afill = 1 if len(events) <= 26 else 2

        self.tag_to_id.setdefault(yr_wk, {})
        weekday_to_events = {}
        for i in range(7):
            this_day = (start_datetime + timedelta(days=i)).date()
            weekday_to_events[this_day] = []

        for start_ts, end_ts, type, name, id in events:
            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)

            if start_dt == end_dt:
                if start_dt.hour == 0 and start_dt.minute == 0:
                    start_end = ""
                else:
                    start_end = start_dt.strftime("%H:%M")
            else:
                start_end = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"

            type_color = TYPE_TO_COLOR[type]
            # all this to remove bold from the start_end (colons) and to preserve the type color:
            escaped_start_end = (
                # f"[not bold][{type_color}]{start_end}[/{type_color}][/not bold]"
                f"[not bold]{start_end}[/not bold]"
            )
            row = [
                id,
                f"[{type_color}]{type} {escaped_start_end:<12}  {name}[/{type_color}]",
            ]
            weekday_to_events[start_dt.date()].append(row)

        indx = 0

        tag = indx_to_tag(indx, self.afill)

        for day, events in weekday_to_events.items():
            if events:
                details.append(
                    # f" [bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/bold]"
                    f" [not bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/not bold]"
                )
            elif show_unscheduled:
                details.append(
                    f" [not bold][{DIM_COLOR}]{day.strftime('%A, %B %-d')}[/{DIM_COLOR}][/not bold]"
                )
            for event in events:
                event_id, event_str = event
                tag = indx_to_tag(indx, self.afill)
                self.tag_to_id[yr_wk][tag] = event_id
                details.append(f"  [dim]{tag}[/dim]  {event_str} {event_id}")
                indx += 1
        details_str = "\n".join(details)
        self.yrwk_to_details[yr_wk] = details_str
        log_msg(f"tags for {yr_wk}: {self.tag_to_id = }")
        return details_str

    # def process_rownum(self, digit):
    #     """
    #     Process two-digit input and fetch details for the selected date.
    #
    #     Args:
    #         digits (str): The two-digit day of the month.
    #     """
    #     log_msg(f"Processing digit: {digit}, {type(digit) = }")
    #     if digit in self.rownum_to_yrwk:
    #         self.selected_week = self.rownum_to_yrwk[digits]
    #         details = self.yrwk_to_details[self.selected_week]
    #         log_msg(f"Selected week: {self.selected_week}")
    #     else:
    #         details = f"Invalid monthday: {digit}"
    #
    #     self.refresh_display(details)

    def move_next_period(self):
        """
        Move to the next 4-week period.
        """
        self.current_start_date += timedelta(weeks=4)
        self.selected_day = None
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.refresh_display()

    def move_previous_period(self):
        """
        Move to the previous 4-week period.
        """
        self.current_start_date -= timedelta(weeks=4)
        self.selected_day = None
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.refresh_display()

    def reset_to_today(self):
        """
        Reset the display to the current 4-week period containing today.
        """
        self.current_start_date = self.calculate_4_week_start()
        self.selected_day = None
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.refresh_display()

    def quit(self):
        """
        Exit the application.
        """
        self.console.print("[red]Exiting application...[/red]")
        display_messages()
        exit()

    def run(self):
        """
        Run the 4-week view interactive session.
        """
        session = PromptSession(key_bindings=self.key_bindings)
        self.refresh_display()
        while True:
            try:
                session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                self.quit()