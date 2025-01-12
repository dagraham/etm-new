from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
# from prompt_toolkit.layout.controls import FormattedTextControl
import inspect

from rich.console import Console

# Setup Rich console
console = Console()

# Command functions

from datetime import datetime, timedelta
from rich import style
from rich.table import Table
from rich.text import Text
from rich.console import Group
from rich.panel import Panel
import readline

from rich.console import Console
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from io import StringIO
import string

# Get all lowercase letters
alpha = [x for x in string.ascii_lowercase]


DAY_COLOR = NAMED_COLORS["LightSkyBlue"]
BUSY_COLOR = NAMED_COLORS["LightSlateGray"] 
CONF_COLOR = NAMED_COLORS["DarkOrange"] 
FREE_CHAR = " "

messages = []
selected_day = ""
monthdays = []

def log_msg(msg: str):
    global messages
    caller_name = inspect.stack()[1].function
    messages.append(f"%%{caller_name}:\n  {msg}")

def display_messages():
    global messages
    for msg in messages:
        console.print(msg)

# Simulated database function
def get_day_details(day_id):
    """Fetch details for the given day identifier (e.g., '09')."""
    eg_details = {
        "9": [
            {"record_id": 1, "type": "*", "time": "09:00-10:00", "name": "Staff meeting"},
            {"record_id": 2, "type": "-", "time": "11:00", "name": "record meeting minutes"}
        ],
        "10": [{"record_id": 2, "type": "*", "time": "12:00-13:30", "name": "Lunch with Burk"}],
    }
    indx = 0
    tag_to_id = {}
    detail_rows = eg_details.get(day_id, []) 
    # table = Table(show_header=False, expand=True, box=box.HORIZONTALS)
    details = []
    if detail_rows:
        for detail in detail_rows:
            details.append(f"[dim]{alpha[indx]}[/dim]   {detail['type']}   {detail['time']:<12}   {detail['name']}")
            indx += 1
    else:
        details.append(f"Nothing scheduled for {day_id}") 
    return "\n".join(details), tag_to_id 


# Improved calculation for the start of the 4-week period
def calculate_4_week_start():
    """Calculate the start date of the current 4-week period, beginning on a Monday."""
    global current_start_date, selected_day
    today = datetime.now()
    selected_day = today.strftime("%-d") 
    iso_year, iso_week, iso_weekday = today.isocalendar()


    # Find the Monday of the current ISO week
    start_of_week = today - timedelta(days=iso_weekday - 1)  # Subtract days to get to Monday

    # Find the start of the 4-week cycle
    weeks_into_cycle = (iso_week - 1) % 4  # Weeks since the last 4-week period started
    start_of_cycle = start_of_week - timedelta(weeks=weeks_into_cycle)
    print(f"{start_of_cycle = }") 

    return start_of_cycle


def generate_table(grouped_events={}, start_date=calculate_4_week_start(), num_weeks=4):
    """
    Render a 4x7 table showing events for the specified weeks.

    Args:
        grouped_events (Dict[int, Dict[int, Dict[int, List[Tuple]]]]): Events grouped by year, week, and weekday.
        start_year (int): The starting ISO year.
        start_week (int): The starting ISO week.
        num_weeks (int): Number of weeks to display.
    """
    global selected_day, monthdays 
    # log_msg(f"{start_date = }, {selected_day = }")
    #
    # Calculate the range of weeks to render
    end_date = start_date + timedelta(weeks=num_weeks)
    title = (
        f"[yellow]{start_date.strftime('%B %-d')} – {end_date.strftime('%B %-d, %Y')}[/yellow]"
        if start_date.year == end_date.year 
        else f"[yellow]{start_date.strftime('%B %-d, %Y')} – {end_date.strftime('%B %-d, %Y')}[/yellow]"
    )
    current_date = start_date

    now_year, now_week, now_day = datetime.now().isocalendar()
 

    table = Table(
        show_header=True, header_style="bold blue", 
        show_lines=True, expand=True, title=title
    ) 
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Add columns for weekdays
    table.add_column("Week", justify="center", style="dim", width=6, vertical="middle")
    for day in weekdays:
        table.add_column(day, justify="center", style=DAY_COLOR, width=10, vertical="middle") 

    # Add rows for each week in the range
    monthdays = []
    while current_date < end_date:
        iso_year, iso_week, _ = current_date.isocalendar()
        row = [f"{iso_week:>2}\n"]
        for weekday in range(1, 8):  # ISO weekdays: 1 = Monday, 7 = Sunday
            monthday_str = datetime.strptime(f"{iso_year} {iso_week} {weekday}", "%G %V %u").strftime("%-d")
            monthdays.append(monthday_str)
            events = grouped_events.get(iso_year, {}).get(iso_week, {}).get(weekday, []) if grouped_events else [] 

            today = iso_year == now_year and iso_week == now_week and weekday == now_day
            if events:
                tups = [event_tuple_to_minutes(ev[0], ev[1]) for ev in events]
                print(f"{tups = }") 
                aday_str, busy_str = get_busy_bar(tups)
                if aday_str:
                    # row.append(f"{aday_str} {monthday_str} {aday_str}{busy_str}")
                    mday = f"{aday_str} {monthday_str} {aday_str}{busy_str}"
                else:
                    mday = f"{monthday_str}{busy_str}"
            else:
                mday = f"{monthday_str}\n"

            if today:
                mday = f"[bold][yellow]{mday}[/yellow][/bold]"
            if selected_day and monthday_str == selected_day:
                mday = f"[reverse][bold][yellow]{mday}[/yellow][/bold][/reverse]"
            row.append(mday)

        table.add_row(*row)
        current_date += timedelta(weeks=1)
    return table

def render_display(console, table, details):
    """Clear the console and render the table and details together."""
    console.clear()
    panel_group = Group(
    table,
    Panel(details),
        " Period: > , < , . , 2-digit monday or Quit: Q"
    )
    console.print(Panel(panel_group))



current_start_date = calculate_4_week_start()

if not selected_day and datetime.now() >= current_start_date and datetime.now() < current_start_date + timedelta(weeks=4):
    selected_day = datetime.now().strftime("%d")
    details, tag_to_id = get_day_details(selected_day) 
else:
    selected_day = ""

def next_period():
    global current_start_date, selected_day, monthdays
    monthdays = []
    console.clear()
    # log_msg(f"a. {current_start_date = }, {selected_day = }")
    current_start_date += timedelta(weeks=4)
    selected_day = current_start_date.strftime("%-d") 
    details, tag_to_id = get_day_details(selected_day) 
    # log_msg(f"b. {current_start_date = }, {selected_day = }")
    render_display(console, generate_table({}, current_start_date), details)
    # Add logic for displaying the next period

def previous_period():
    global current_start_date, selected_day, monthdays
    monthdays = []
    console.clear()
    # log_msg(f"a. {current_start_date = }, {selected_day = }")
    current_start_date -= timedelta(weeks=4)
    selected_day = current_start_date.strftime("%-d") 
    details, tag_to_id = get_day_details(selected_day) 
    # log_msg(f"b. {current_start_date = }, {selected_day = }")
    render_display(console, generate_table({}, current_start_date), details)
    # Add logic for displaying the previous period

def refresh_display():
    global current_start_date, selected_day, monthdays
    monthdays = []
    # log_msg(f"1. {current_start_date = }, {selected_day = }")
    console.clear()
    current_start_date = calculate_4_week_start()
    # log_msg(f"2. {current_start_date = }, {selected_day = }")
    details, tag_to_id = get_day_details(selected_day) 
    render_display(console, generate_table({}, current_start_date), details)
    # Add logic for refreshing the current display

def quit_application():
    console.clear()
    console.print("[red]Quitting Application![/red]")
    display_messages()
    exit(0)

# Key bindings
bindings = KeyBindings()

@bindings.add(">")
def handle_next_period(event):
    next_period()

@bindings.add("<")
def handle_previous_period(event):
    previous_period()

@bindings.add(".")
def handle_refresh(event):
    refresh_display()

@bindings.add("Q")
def handle_quit(event):
    quit_application()

digit_buffer = []

# Command to execute when two digits are recognized
def process_two_digit_input(digits):
    global selected_day
    print(f"Command invoked with argument: {digits}")
    if digits in monthdays:
        selected_day = digits
        details, tag_to_id = get_day_details(digits)
    else:
        details, tag_to_id = f"Invalid monthday {digits}", {}

    render_display(console, generate_table({}, current_start_date), details)



# Add key bindings for digits
for digit in "0123456789":
    @bindings.add(digit)
    def _(event, digit=digit):
        global digit_buffer
        digit_buffer.append(digit)
        matches = []
        if len(digit_buffer) == 2:
            digits = "".join(digit_buffer).lstrip("0")
            digit_buffer.clear()
            process_two_digit_input(digits)



# Main application
def main():
    session = PromptSession(key_bindings=bindings)
    console.print("[cyan]Welcome to the Rich + PromptSession Integration![/cyan]")
    refresh_display()
    while True:
        # Prompt user for input; keybindings are active during input
        try:
            # session.prompt("Press >, <, ., or q: ")
            session.prompt()
        except KeyboardInterrupt:
            console.print("[red]KeyboardInterrupt - Exiting![/red]")
            break
        except EOFError:
            console.print("[red]EOFError - Exiting![/red]")
            break


if __name__ == "__main__":
    main()
