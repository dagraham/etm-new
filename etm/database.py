import sqlite3
from datetime import datetime
from dateutil.tz import gettz

# from etm.common import parse



# Connect to SQLite database
conn = sqlite3.connect("example.db")
c = conn.cursor()

# Create Records table
c.execute(
    """
    CREATE TABLE IF NOT EXISTS Records (
        id INTEGER PRIMARY KEY,
        rrulestr TEXT,
        extent INTEGER,  -- Duration of the event in minutes
        processed INTEGER DEFAULT 0  -- not infinitely repeating: 0 = not processed, 1 = processed
    )
"""
)

# Create DateTimes table
c.execute(
    """
    CREATE TABLE IF NOT EXISTS DateTimes (
        record_id INTEGER,
        year INTEGER,
        month INTEGER,
        day INTEGER, 
        hour INTEGER, 
        minute INTEGER,
        week INTEGER,
        weekday INTEGER,
        start_minutes INTEGER,
        end_minutes INTEGER,
        FOREIGN KEY (record_id) REFERENCES Records (id)
    );    
"""
)

conn.commit()

# Create GeneratedWeeks table 
c.execute(
    """
    CREATE TABLE GeneratedWeeks (
        start_year INTEGER,
        start_week INTEGER,
        end_year INTEGER,
        end_week INTEGER
    );
"""
)

conn.commit()


# Insert the records into the database
records = [
    (1, r'DTSTART:20241122T220000\nRRULE:FREQ=DAILY;COUNT=2', 240),
    (2, r'DTSTART:20241123T080000\nRRULE:FREQ=WEEKLY;COUNT=3', 90),
    (3, r'RDATE:20241223T080000', 90),
    (4, r'DTSTART:20241224T080000\nRDATE:20241227T093000', 90),
    (5, r'DTSTART:20241220T080000\nRRULE:FREQ=WEEKLY', 90),
]

# Use a parameterized query to insert the records
for record in records:
    c.execute("INSERT INTO Records (id, rrulestr, extent) VALUES (?, ?, ?)", record)

# Commit the changes
conn.commit()


from datetime import datetime, timedelta

from dateutil.rrule import rrulestr

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
    min_year = min(cached_ranges, key=lambda x: x[0])[0] if cached_ranges else start_year
    min_week = min(cached_ranges, key=lambda x: x[1])[1] if cached_ranges else start_week
    max_year = max(cached_ranges, key=lambda x: x[2])[2] if cached_ranges else end_year
    max_week = max(cached_ranges, key=lambda x: x[3])[3] if cached_ranges else end_week

    # Expand the range to include gaps and requested period
    if start_year < min_year or (start_year == min_year and start_week < min_week):
        min_year, min_week = start_year, start_week
    if end_year > max_year or (end_year == max_year and end_week > max_week):
        max_year, max_week = end_year, end_week


    first_day = datetime.strptime(f"{min_year} {min_week} 1", "%G %V %u")
    last_day = datetime.strptime(f"{max_year} {max_week} 1", "%G %V %u") + timedelta(days=6)

    populate_datetimes_table(first_day.isoformat(), last_day.isoformat())

    # Update the GeneratedWeeks table
    c.execute("DELETE FROM GeneratedWeeks")  # Clear old entries
    c.execute(
        "INSERT INTO GeneratedWeeks (start_year, start_week, end_year, end_week) VALUES (?, ?, ?, ?)",
        (min_year, min_week, max_year, max_week),
    )
    conn.commit()


def populate_datetimes_table(start: str, end: str):
    """
    Populate the DateTimes table with datetimes for all records within the specified range.
    """
    # Fetch all records with their rrule strings, extents, and processed state
    c.execute("SELECT id, rrulestr, extent, processed FROM Records")
    records = c.fetchall()

    for record_id, rrulestr_str, extent, processed in records:
        if processed == 1:
            # Skip already processed finite recurrences
            if "RRULE" not in rrulestr_str or "COUNT=" in rrulestr_str or "UNTIL=" in rrulestr_str:
                continue

        # Generate datetimes for the given range
        occurrences = generate_datetimes(rrulestr_str, extent, start, end)
        for occ in occurrences:
            year, month, day, hour, minute, week, weekday, start_minutes, end_minutes = occ

            # Insert into DateTimes
            c.execute(
                """
                INSERT INTO DateTimes (
                    record_id, year, month, day, hour, minute, week, weekday, start_minutes, end_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, year, month, day, hour, minute, week, weekday, start_minutes, end_minutes),
            )

        # Mark finite recurrences as processed
        if "RRULE" not in rrulestr_str or "COUNT=" in rrulestr_str or "UNTIL=" in rrulestr_str:
            c.execute("UPDATE Records SET processed = 1 WHERE id = ?", (record_id,))

    conn.commit()

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
    if "RRULE" not in rrule_string or "COUNT=" in rrule_string or "UNTIL=" in rrule_string:
        print(f"Generating all occurrences for {rrule_string = }")
        occurrences = rule.between(datetime.min, datetime.max, inc=True)
    else:
        print(f"Generating occurrences for the period: {rrule_string = }")
        occurrences = rule.between(start_dt, end_dt, inc=True)

    records = []

    for event_start in occurrences:
        event_end = event_start + extent_delta

        # Handle events spanning multiple days
        while event_start.date() != event_end.date():
            day_end = datetime.combine(event_start.date(), datetime.max.time())
            records.append([
                event_start.year, event_start.month, event_start.day,
                event_start.hour, event_start.minute,
              event_start.isocalendar().week, event_start.isocalendar().weekday,
                event_start.hour * 60 + event_start.minute,
                day_end.hour * 60 + day_end.minute
            ])
            event_start = datetime.combine(
                event_start.date() + timedelta(days=1), datetime.min.time()
            )

        # Add the final segment for the last part of the event
        records.append([
            event_start.year, event_start.month, event_start.day,
            event_start.hour, event_start.minute,
            event_start.isocalendar().week, event_start.isocalendar().weekday,
            event_start.hour * 60 + event_start.minute,
            event_end.hour * 60 + event_end.minute
        ])

    return records



# Register the function with SQLite
conn.create_function("generate_datetimes", 4, generate_datetimes)


from datetime import datetime

def test_weeks(start_year: str, start_week: str, weeks: int):
    """
    Test the week generation functionality.

    Args:
        start_date (str): Start date in ISO format.
        weeks (int): Number of weeks to generate.
    """
    first_day = datetime.strptime(f"{start_year} {start_week} 1", "%G %V %u")
    last_day = first_day + timedelta(weeks=int(weeks), days=6) 
    return first_day, last_day

print(test_weeks("2020", "51", 4))

# Example usage
# populate_datetimes_table("2024-11-22T00:00:00", "2024-12-31T23:59:59")
current_year, current_week = datetime.now().isocalendar()[:2]
extend_datetimes_for_weeks(start_year=current_year, start_week=current_week, weeks=4)

# Query the DateTimes table
c.execute("SELECT * FROM DateTimes")
rows = c.fetchall()
for row in rows:
    print(row)
