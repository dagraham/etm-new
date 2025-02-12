import sqlite3
import sys
import os
import random
import lorem
from datetime import datetime, timedelta
from dateutil.tz import gettz
from dateutil import rrule
from dateutil.rrule import rrulestr
from collections import defaultdict
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from typing import List, Tuple, Union

from rich import style
from rich.table import Table
from rich.console import Console

DAY_COLOR = NAMED_COLORS["LightSkyBlue"]
BUSY_COLOR = NAMED_COLORS["LightSlateGray"]
CONF_COLOR = NAMED_COLORS["DarkOrange"]
ONEDAY = timedelta(days=1)
ONEWK = 7 * ONEDAY

db_path = "example.db"


def setup_database(replace: bool = False):
    # conn = sqlite3.connect(db_path)  # Use a persistent SQLite database
    # cursor = conn.cursor()

    if replace and os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Records (
            id INTEGER PRIMARY KEY,
            type TEXT CHECK(type IN ('*', '-', '~', '^')) NOT NULL, -- *: event, -: task, ~: goal, ^: chore
            name TEXT NOT NULL,
            details TEXT,
            rrulestr TEXT, -- DTSTART and RDATEs in UTC times
            extent INTEGER,  -- Duration of the event in minutes
            processed INTEGER DEFAULT 0  -- not infinitely repeating: 0 = not processed, 1 = processed
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS DateTimes (
            record_id INTEGER,
            start_datetime INTEGER,
            end_datetime INTEGER,
            FOREIGN KEY (record_id) REFERENCES Records (id)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS GeneratedWeeks (
            start_year INTEGER,
            start_week INTEGER, 
            end_year INTEGER, 
            end_week INTEGER 
    );
    """
    )

    conn.commit()
    return conn, c


def local_dtstr_to_utc_str(local_dt_str: str) -> str:
    """
    Convert a local datetime string to a UTC datetime string.

    Args:
        local_dt_str (str): Local datetime string.
        local_tz_str (str): Local timezone string.

    Returns:
        str: UTC datetime string.
    """
    from dateutil import parser

    local_dt = parser.parse(local_dt_str).astimezone()
    utc_dt = local_dt.astimezone(tz=gettz("UTC")).replace(tzinfo=None)
    return utc_dt.isoformat()


def week(dt: datetime) -> Union[datetime, datetime]:
    y, w, d = dt.isocalendar()
    wk_beg = dt - (d - 1) * ONEDAY if d > 1 else dt
    wk_end = dt + (7 - d) * ONEDAY if d < 7 else dt
    return wk_beg.date(), wk_end.date()


def generate_datetimes(rrule_string, extent, start, end):
    """
    Generate datetimes from an rrule string within a specified range, handling event extents.

    Args:
        rrule_string (str): The rrule string defining the recurrence.
        extent (int): Duration of the event in minutes.
        start (str): Start datetime in ISO format.
        end (str): End datetime in ISO format.

    Returns:
        List[List]: A list of lists, where each inner list contains:
                    [year, month, day, hour, minute, week, weekday, start_minutes, end_minutes]
    """
    # Replace escaped newline in rrule strings for compatibility
    rrule_string = rrule_string.replace("\\n", "\n")
    rule = rrulestr(rrule_string)
    extent_delta = timedelta(minutes=extent)
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    # Determine the range of occurrences
    if (
        "RRULE" not in rrule_string
        or "COUNT=" in rrule_string
        or "UNTIL=" in rrule_string
    ):
        print(f"Generating all occurrences for {rrule_string = }")
        occurrences = rule.between(datetime.min, datetime.max, inc=True)
    else:
        print(f"Generating occurrences for the period: {rrule_string = }")
        occurrences = rule.between(start_dt, end_dt, inc=True)

    records = []

    for start in occurrences:
        print(f"Processing start: {start = }")
        event_start = (
            start.replace(tzinfo=gettz("UTC")).astimezone().replace(tzinfo=None)
        )
        print(f"Processing event_start: {event_start = }")
        event_end = event_start + extent_delta

        # Handle events spanning multiple days
        records.append([event_start, event_end])
    return records


def populate_datetimes_table(start: str, end: str):
    """
    Populate the DateTimes table with datetimes for all records within the specified range.
    """
    conn.create_function("generate_datetimes", 4, generate_datetimes)
    # Fetch all records with their rrule strings, extents, and processed state
    c.execute("SELECT id, rrulestr, extent, processed FROM Records")
    records = c.fetchall()

    for record_id, rrulestr_str, extent, processed in records:
        if processed == 1:
            # Skip already processed finite recurrences
            if (
                "RRULE" not in rrulestr_str
                or "COUNT=" in rrulestr_str
                or "UNTIL=" in rrulestr_str
            ):
                continue

        # Generate datetimes for the given range
        occurrences = generate_datetimes(rrulestr_str, extent, start, end)
        for occ in occurrences:
            start_datetime, end_datetime = occ

            # Insert into DateTimes
            c.execute(
                """
                INSERT INTO DateTimes (
                    record_id, start_datetime, end_datetime
                ) VALUES (?, ?, ?)
                """,
                (
                    record_id,
                    round(start_datetime.timestamp()),
                    round(end_datetime.timestamp()),
                ),
            )

        # Mark finite recurrences as processed
        if (
            "RRULE" not in rrulestr_str
            or "COUNT=" in rrulestr_str
            or "UNTIL=" in rrulestr_str
        ):
            c.execute("UPDATE Records SET processed = 1 WHERE id = ?", (record_id,))

    conn.commit()


def extend_datetimes_for_weeks(start_year, start_week, weeks):
    """
    Extend the DateTimes table by generating data for the specified number of weeks
    starting from a given year and week.

    Args:
        start_year (int): The starting year.
        start_week (int): The starting ISO week.
        weeks (int): Number of weeks to generate.
    """
    start = datetime.strptime(f"{start_year} {start_week} 1", "%G %V %u")
    end = start + timedelta(weeks=int(weeks))

    start_year, start_week = start.isocalendar()[:2]
    end_year, end_week = end.isocalendar()[:2]

    c.execute("SELECT * FROM GeneratedWeeks")
    cached_ranges = c.fetchall()

    # Determine the full range that needs to be generated
    min_year = (
        min(cached_ranges, key=lambda x: x[0])[0] if cached_ranges else start_year
    )
    min_week = (
        min(cached_ranges, key=lambda x: x[1])[1] if cached_ranges else start_week
    )
    max_year = max(cached_ranges, key=lambda x: x[2])[2] if cached_ranges else end_year
    max_week = max(cached_ranges, key=lambda x: x[3])[3] if cached_ranges else end_week

    # Expand the range to include gaps and requested period
    if start_year < min_year or (start_year == min_year and start_week < min_week):
        min_year, min_week = start_year, start_week
    if end_year > max_year or (end_year == max_year and end_week > max_week):
        max_year, max_week = end_year, end_week

    first_day = datetime.strptime(f"{min_year} {min_week} 1", "%G %V %u")
    last_day = datetime.strptime(f"{max_year} {max_week} 1", "%G %V %u") + timedelta(
        days=6
    )

    populate_datetimes_table(first_day.isoformat(), last_day.isoformat())

    # Update the GeneratedWeeks table
    c.execute("DELETE FROM GeneratedWeeks")  # Clear old entries
    c.execute(
        "INSERT INTO GeneratedWeeks (start_year, start_week, end_year, end_week) VALUES (?, ?, ?, ?)",
        (min_year, min_week, max_year, max_week),
    )
    conn.commit()


def get_events_for_period(start_date, end_date):
    """
    Fetch events from DateTimes within the specified period.

    Args:
        start_date (str): Start date in ISO format.
        end_date (str): End date in ISO format.

    Returns:
        List[Tuple]: List of tuples with event details.
    """
    # Convert ISO format dates to integer seconds since the epoch
    print(f"Fetching events between {start_date = } and {end_date = }...")
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    print(f"Fetching events between {start_ts = } and {end_ts = }...")
    print(
        f"between {datetime.fromtimestamp(start_ts) = } and {datetime.fromtimestamp(end_ts) = }..."
    )

    query = """
        SELECT record_id, start_datetime, end_datetime
        FROM DateTimes
        WHERE start_datetime BETWEEN ? AND ?
    """
    c.execute(query, (start_ts, end_ts))
    return c.fetchall()


def event_tuple_to_minutes(start_dt: datetime, end_dt: datetime) -> Tuple[int, int]:
    """
    Convert event start and end datetimes to minutes since midnight.

    Args:
        start_dt (datetime): Event start datetime.
        end_dt (datetime): Event end datetime.

    Returns:
        Tuple(int, int): Tuple of start and end minutes since midnight.
    """
    start_minutes = start_dt.hour * 60 + start_dt.minute
    end_minutes = end_dt.hour * 60 + end_dt.minute
    return (start_minutes, end_minutes)


def process_events(events):
    """
    Process events and split across days for display.

    Args:
        events (List[Tuple]): List of events (record_id, start_ts, end_ts).
        timezone_str (str): Local timezone string.

    Returns:
        Dict[int, Dict[int, Dict[int, List[Tuple]]]]: Nested dictionary grouped by year, week, and weekday.
    """
    from collections import defaultdict
    from datetime import datetime, timedelta
    # import pytz

    # local_tz = pytz.timezone(timezone_str)
    grouped_events = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for record_id, start_ts, end_ts in events:
        start_dt = (
            datetime.utcfromtimestamp(start_ts)
            .replace(tzinfo=gettz("UTC"))
            .astimezone()
            .replace(tzinfo=None)
        )
        end_dt = (
            datetime.utcfromtimestamp(end_ts)
            .replace(tzinfo=gettz("UTC"))
            .astimezone()
            .replace(tzinfo=None)
        )

        while start_dt.date() <= end_dt.date():
            # Compute the end time for the current day
            day_end = min(
                end_dt, datetime.combine(start_dt.date(), datetime.max.time())
            )

            # Group by ISO year, week, and weekday
            iso_year, iso_week, iso_weekday = start_dt.isocalendar()
            grouped_events[iso_year][iso_week][iso_weekday].append((start_dt, day_end))

            # Move to the next day
            start_dt = datetime.combine(
                start_dt.date() + timedelta(days=1), datetime.min.time()
            )

    return grouped_events


def render_weekday_table(grouped_events, start_year, start_week, num_weeks):
    """
    Render a 4x7 table showing events for the specified weeks.

    Args:
        grouped_events (Dict[int, Dict[int, Dict[int, List[Tuple]]]]): Events grouped by year, week, and weekday.
        start_year (int): The starting ISO year.
        start_week (int): The starting ISO week.
        num_weeks (int): Number of weeks to display.
    """
    #
    # Calculate the range of weeks to render
    print(f"{grouped_events = }")
    start_date = datetime.strptime(f"{start_year} {start_week} 1", "%G %V %u")
    end_date = start_date + timedelta(weeks=num_weeks)
    title = (
        f"[yellow]{start_date.strftime('%B %-d')} – {end_date.strftime('%B %-d, %Y')}[/yellow]"
        if start_date.year == end_date.year
        else f"[yellow]{start_date.strftime('%B %-d, %Y')} – {end_date.strftime('%B %-d, %Y')}[/yellow]"
    )
    current_date = start_date

    console = Console()
    table = Table(
        show_header=True,
        header_style="bold blue",
        show_lines=True,
        expand=True,
        title=title,
    )
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Add columns for weekdays
    table.add_column(
        "Week", justify="center", style="dim", no_wrap=True, width=6, vertical="middle"
    )
    for day in weekdays:
        table.add_column(
            day,
            justify="center",
            style=DAY_COLOR,
            no_wrap=True,
            width=10,
            vertical="middle",
        )

    # Add rows for each week in the range
    while current_date < end_date:
        iso_year, iso_week, _ = current_date.isocalendar()
        # row = [f"{iso_week:>2}\n{iso_year}"]
        row = [f"{iso_week:>2}\n"]
        for weekday in range(1, 8):  # ISO weekdays: 1 = Monday, 7 = Sunday
            monthday_str = datetime.strptime(
                f"{iso_year} {iso_week} {weekday}", "%G %V %u"
            ).strftime("%d")
            events = grouped_events.get(iso_year, {}).get(iso_week, {}).get(weekday, [])
            if events:
                tups = [event_tuple_to_minutes(ev[0], ev[1]) for ev in events]
                print(f"{tups = }")
                aday_str, busy_str = get_busy_bar(tups)
                # This is the
                # event_strings = [
                #     f"{ev[0].strftime('%H:%M')}–{ev[1].strftime('%H:%M')}" for ev in events
                # ]
                if aday_str:
                    row.append(f"{aday_str} {monthday_str} {aday_str}{busy_str}")
                else:
                    row.append(f"{monthday_str}{busy_str}")
            else:
                row.append(f"{monthday_str}\n")

        table.add_row(*row)
        current_date += timedelta(weeks=1)

    console.print(table)


import bisect

SLOT_HOURS = [0, 4, 8, 12, 16, 20, 24]
# SLOT_HOURS = [0, 8, 11, 14, 17, 20, 24]
SLOT_MINUTES = [x * 60 for x in SLOT_HOURS]
BUSY = "■"  # U+25A0 this will be busy_bar busy and conflict character
FREE = "□"  # U+25A1 this will be busy_bar free character
ADAY = "━"  # U+2501 for all day events ━


def get_busy_bar(lop: List[Tuple[int, int]]) -> Tuple[str, str]:
    busy_conf = {x: 0 for x in SLOT_MINUTES}
    busy_minutes = []
    conflict_minutes = []
    lop.sort()
    (b, e) = (0, 0)
    allday = 0
    for B, E in lop:
        if B == 0 and E == 0:
            allday += 1
        if E == B and not allday:
            # skip zero duration events
            continue
        print(f"{b = }, {e = }, {B = }, {E = }")
        if e <= B:  # no conflict
            busy_minutes.append((b, e))
            b = B
            e = E
        else:  # B < e
            busy_minutes.append((b, B))
            if e <= E:
                conflict_minutes.append((B, e))
                b = e
                e = E
            else:  # E < e
                conflict_minutes.append((B, E))
                b = E
                e = e
    busy_minutes.append((b, e))
    for b, e in busy_minutes:
        print(f"busy_minutes {b = }, {e = }")
        if not e > b:
            print(f"skipping {b = }, {e = }")
            continue
        start = bisect.bisect_left(SLOT_MINUTES, b)
        end = max(start, bisect.bisect_right(SLOT_MINUTES, e) - 1)
        print(f"busy_minutes {start = }, {end = }")
        for i in range(start, end + 1):
            busy_conf[SLOT_MINUTES[i]] = 1
            print(
                f"{i = }, {b = }, {e = }, {SLOT_MINUTES[i] = }, {busy_conf[SLOT_MINUTES[i]] = }"
            )

    for b, e in conflict_minutes:
        print(f"conflict_minutes {b = }, {e = }")
        if not e > b:
            print(f"skipping {b = }, {e = }")
            continue
        start = bisect.bisect_left(SLOT_MINUTES, b)
        end = max(start, bisect.bisect_right(SLOT_MINUTES, e) - 1)
        print(f"conflict_minutes {start = }, {end = }")
        for i in range(start, end + 1):
            busy_conf[SLOT_MINUTES[i]] = 2
            print(
                f"{b = }, {e = }, {SLOT_MINUTES[i] = }, {busy_conf[SLOT_MINUTES[i]] = }"
            )

    busy_bar = []
    have_busy = False
    for i in range(len(SLOT_MINUTES) - 1):
        if busy_conf[SLOT_MINUTES[i]] == 0:
            busy_bar.append(f"[dim]{FREE}[/dim]")
            # busy_bar.append(f"{FREE}")
        elif busy_conf[SLOT_MINUTES[i]] == 1:
            have_busy = True
            busy_bar.append(f"[{DAY_COLOR}]{BUSY}[/{DAY_COLOR}]")
        else:
            have_busy = True
            busy_bar.append(f"[{CONF_COLOR}]{BUSY}[/{CONF_COLOR}]")
    busy_str = (
        f"\n[{BUSY_COLOR}]{''.join(busy_bar)}[/{BUSY_COLOR}]" if have_busy else "\n"
    )
    aday_str = f"{ADAY}" if allday > 0 else ""

    return aday_str, busy_str


conn = None
c = None


def main():
    global conn, c
    if sys.argv[1:] and sys.argv[1] == "xxx":
        use_examples()
        return
    conn, c = setup_database()
    # Define the 4-week period
    start_date = datetime.now() - timedelta(days=7)
    start_year, start_week = start_date.isocalendar()[:2]
    end_date = start_date + timedelta(weeks=4)
    # current_year, current_week = datetime(2024, 12, 2, 0, 0).isocalendar()[:2]
    extend_datetimes_for_weeks(start_year=start_year, start_week=start_week, weeks=4)

    print(f"Fetching events from {start_date} to {end_date}...")

    events = get_events_for_period(start_date, end_date)
    print(f"Found {len(events)} events: {events = }")

    grouped_events = process_events(events)

    render_weekday_table(grouped_events, start_year, start_week, num_weeks=4)


if __name__ == "__main__":
    main()
