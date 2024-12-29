import sqlite3

# Connect to SQLite database
conn = sqlite3.connect("example.db")
c = conn.cursor()

# Create Records table
c.execute(
    """
    CREATE TABLE IF NOT EXISTS Records (
        id INTEGER PRIMARY KEY,
        rrulestr TEXT,
        extent INTEGER  -- Duration of the event in minutes
    )
"""
)

c.execute(
    """
    CREATE TABLE DateTimes (
        record_id INTEGER,
        start_datetime INTEGER,
        end_datetime INTEGER,
        year INTEGER GENERATED ALWAYS AS (CAST(strftime('%Y', datetime(start_datetime, 'unixepoch')) AS INTEGER)) VIRTUAL,
        week INTEGER GENERATED ALWAYS AS (CAST(strftime('%W', datetime(start_datetime, 'unixepoch')) AS INTEGER)) VIRTUAL,
        weekday INTEGER GENERATED ALWAYS AS (CAST(strftime('%w', datetime(start_datetime, 'unixepoch')) AS INTEGER)) VIRTUAL,
        start_minutes INTEGER GENERATED ALWAYS AS (CAST(strftime('%M', datetime(start_datetime, 'unixepoch')) + 60 * strftime('%H', datetime(start_datetime, 'unixepoch')) AS INTEGER)) VIRTUAL,
        end_minutes INTEGER GENERATED ALWAYS AS (CAST(strftime('%M', datetime(end_datetime, 'unixepoch')) + 60 * strftime('%H', datetime(end_datetime, 'unixepoch')) AS INTEGER)) VIRTUAL,
        FOREIGN KEY (record_id) REFERENCES Records (id)
    )
    """
)


conn.commit()


# Insert the records into the database
records = [
    (1, r"DTSTART:20241122T220000\nRRULE:FREQ=DAILY;COUNT=2", 240),
    (2, r"DTSTART:20241123T080000\nRRULE:FREQ=WEEKLY;COUNT=3", 90),
    (3, r"RDATE:20241223T080000", 90),
    (4, r"DTSTART:20241224T080000\nRDATE:20241227T093000", 90),
]

# Use a parameterized query to insert the records
for record in records:
    c.execute("INSERT INTO Records (id, rrulestr, extent) VALUES (?, ?, ?)", record)

# Commit the changes
conn.commit()


from datetime import datetime, timedelta

from dateutil.rrule import rrulestr


def generate_datetimes(rrule_string, extent, start, end):
    """
    Generate datetimes from an rrule string within a specified range, handling event extents.

    Args:
        rrule_string (str): The rrule string defining the recurrence.
        start (str): Start datetime in timestamp format.
        end (str): End datetime in timestamp format.
        extent (int): Duration of the event in minutes.

    Returns:
        str: A semicolon-separated string of start-end datetime ranges in ISO format.
    """
    rule = rrulestr(rrule_string)
    extent_delta = timedelta(minutes=extent)
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    print(f"{rule = }; {extent_delta = }; {start_dt = }; {end_dt = }")

    records = []

    for event_start in rule.between(start_dt, end_dt, inc=True):
        event_end = event_start + extent_delta

        # Split across days if necessary
        while event_start.date() != event_end.date():
            day_end = datetime.combine(event_start.date(), datetime.max.time())
            records.append(f"{round(event_start.timestamp())},{round(day_end.timestamp())}")
            event_start = datetime.combine(
                event_start.date() + timedelta(days=1), datetime.min.time()
            )

        # Add the final segment
        records.append(f"{round(event_start.timestamp())},{round(event_end.timestamp())}")

    return ";".join(records)


# Register the function with SQLite
conn.create_function("generate_datetimes", 4, generate_datetimes)


from datetime import datetime


def populate_datetimes_table(start: str, end: str):
    """
    Populate the DateTimes table with datetimes for all records within the specified range.

    Args:
        start (str): Start datetime in ISO format.
        end (str): End datetime in ISO format.
    """
    # Clear the DateTimes table
    c.execute("DELETE FROM DateTimes")

    # Fetch all records with their rrule strings and extents
    c.execute("SELECT id, rrulestr, extent FROM Records")
    records = c.fetchall()

    print(f"{start = }; {end = }")
    # Generate and insert datetimes for each record
    for record_id, rrulestr, extent in records:
        # Replace escaped newlines with actual newlines
        print(f"{rrulestr = }; {extent = }")
        rrulestr = rrulestr.replace("\\n", "\n")
        print(f"{rrulestr = }")

        # Use the custom SQLite function to generate datetimes
        c.execute(
            "SELECT generate_datetimes(?, ?, ?, ?)", (rrulestr, extent, start, end)
        )
        datetime_ranges = c.fetchone()[0]

        if datetime_ranges:  # Skip if no datetimes were generated
            for datetime_range in datetime_ranges.split(";"):
                print(f"{datetime_range = }") 
                start_ts, end_ts = datetime_range.split(",")
                # start_ts = round(datetime.fromisoformat(start_iso).timestamp()) 
                # end_ts = round(datetime.fromisoformat(end_iso).timestamp()) 
                c.execute(
                   "INSERT INTO DateTimes (record_id, start_datetime, end_datetime) VALUES (?, ?, ?)",
                    (record_id, int(start_ts), int(end_ts)),
                )

    conn.commit()


# Example usage
populate_datetimes_table("2024-11-22T00:00:00", "2024-12-31T23:59:59")


# Query the DateTimes table
c.execute("SELECT * FROM DateTimes")
rows = c.fetchall()
for row in rows:
    print(row)
