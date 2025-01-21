# TODO: Keep the display part - the model part will be in model.py
from datetime import datetime, timedelta
from logging import log
from sre_compile import dis
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from rich.console import Console
from rich.table import Table
from rich import style
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
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import PromptSession
import string
import shutil
from typing import List, Tuple, Dict
from .common import log_msg, display_messages


DAY_COLOR = NAMED_COLORS["LemonChiffon"]
FRAME_COLOR = NAMED_COLORS["Khaki"]
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

HEADER_COLOR = NAMED_COLORS["LemonChiffon"]

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


# import inspect
# from rich import print as rprint
#
# DEFAULT_LOG_FILE = "log_msg.txt"
#
#
# def log_msg(msg: str, file_path: str = DEFAULT_LOG_FILE):
#     """
#     Log a message and save it directly to a specified file.
#
#     Args:
#         msg (str): The message to log.
#         file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
#     """
#     caller_name = inspect.stack()[1].function
#     formatted_msg = f"[yellow]{caller_name}[/yellow]:\n  {msg}"
#
#     # Save the message to the file
#     with open(file_path, "a") as f:
#         f.write(f"{formatted_msg}\n")
#
#


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


class FourWeekView:
    def __init__(self, controller, bindings):
        self.controller = controller  # Use the controller instead of db_manager
        self.key_bindings = bindings
        self.console = Console(theme=Theme({}))
        self.current_start_date = calculate_4_week_start()
        self.digit_buffer = []  # Buffer for storing two-digit input
        self.showing_item = False
        self.selected_week = tuple(
            datetime.now().isocalendar()[:2]
        )  # Currently selected week
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
        self.key_bindings.add("down")(lambda _: self.move_next_week())
        self.key_bindings.add("left")(lambda _: self.move_previous_period())
        self.key_bindings.add("up")(lambda _: self.move_previous_week())
        self.key_bindings.add("space")(lambda _: self.reset_to_today())
        self.key_bindings.add("0")(lambda _: self.restore_details())
        self.key_bindings.add("Q")(lambda _: self.quit())

        # Add key bindings for digits
        for digit in [str(x) for x in range(1, 5)]:

            @self.key_bindings.add(digit)
            def _(_, digit=digit):
                # log_msg(f"Processing digit: {digit}, {type(digit) = }")
                yr_wk = self.rownum_to_yrwk[int(digit)]
                # log_msg(f"Selected week: {yr_wk}")
                self.selected_week = yr_wk
                self.controller.refresh_display(
                    self.current_start_date, self.selected_week
                )

        for char in "abcdefghijklmnopqrstuvwxyz":

            @self.key_bindings.add(char)
            def _(event, char=char):
                self.digit_buffer.append(char)
                if len(self.digit_buffer) == self.afill:
                    base26_tag = "".join(self.digit_buffer)
                    self.digit_buffer.clear()
                    self.process_tag(base26_tag)

        @self.key_bindings.add("escape", eager=True)
        def _(event):
            """
            Restore the display when Escape is pressed.
            """
            self.restore_details()

    def move_next_period(self):
        """
        Move to the next 4-week period.
        """
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()

    def move_next_week(self):
        """
        Move to the next week in the current 4-week period.
        """
        self.selected_week = get_next_yrwk(*self.selected_week)
        if self.selected_week > tuple(
            (self.current_start_date + timedelta(weeks=4) - ONEDAY).isocalendar()[:2]
        ):
            self.current_start_date += timedelta(weeks=1)
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()

    def move_previous_period(self):
        """
        Move to the previous 4-week period.
        """
        self.current_start_date -= timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()

    def move_previous_week(self):
        """
        Move to the previous week in the current 4-week period.
        """
        self.selected_week = get_previous_yrwk(*self.selected_week)
        if self.selected_week < tuple((self.current_start_date).isocalendar()[:2]):
            self.current_start_date -= timedelta(weeks=1)
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()

    def reset_to_today(self):
        """
        Reset the display to the current 4-week period containing today.
        """
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()

    def restore_details(self):
        """
        Restore the display for the current period.
        """
        log_msg(
            f"Restoring details for {self.selected_week = }, {self.current_start_date = }"
        )
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()

    def display_panel(self):
        log_msg(
            f"Displaying panel for {self.current_start_date = } and {self.selected_week = }"
        )
        panel = self.controller.refresh_display(
            self.current_start_date, self.selected_week
        )
        log_msg(f"Displaying panel: {panel}")
        self.console.clear()
        self.console.print(panel)

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
        # self.controller.refresh_display(self.current_start_date, self.selected_week)
        self.display_panel()
        while True:
            try:
                session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                self.quit()
