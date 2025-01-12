import os
import sqlite3
from typing import Optional
import bisect
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.rrule import rrulestr
from typing import List, Tuple
from prompt_toolkit.styles.named_colors import NAMED_COLORS


# Constants for busy bar rendering
BUSY_COLOR = NAMED_COLORS["YellowGreen"]
CONF_COLOR = NAMED_COLORS["Tomato"]
FRAME_COLOR = NAMED_COLORS["DimGrey"]
SLOT_HOURS = [0, 4, 8, 12, 16, 20, 24]
SLOT_MINUTES = [x * 60 for x in SLOT_HOURS]
BUSY = "■"  # U+25A0 this will be busy_bar busy and conflict character
FREE = "□"  # U+25A1 this will be busy_bar free character
ADAY = "━"  # U+2501 for all day events ━


class DatabaseManager:
    def __init__(self, db_path, replace=False):
        """
        Initialize the database manager and optionally replace the database.

        Args:
            db_path (str): Path to the SQLite database file.
            replace (bool): Whether to replace the existing database.
        """
        self.db_path = db_path
        if replace and os.path.exists(db_path):
            os.remove(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # self.conn: Optional[sqlite3.Connection] = None
        # self.cursor: Optional[sqlite3.Cursor] = None
        self.setup_database()

    def setup_database(self):
        """
        Set up the SQLite database schema.
        """
        # self.conn = sqlite3.connect(self.db_path)
        # self.cursor = self.conn.cursor()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Records (
            id INTEGER PRIMARY KEY,
            type TEXT CHECK(type IN ('*', '-', '~', '^')) NOT NULL,
            name TEXT NOT NULL,
            details TEXT,
            rrulestr TEXT,
            extent INTEGER,
            processed INTEGER DEFAULT 0
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS DateTimes (
            record_id INTEGER,
            start_datetime INTEGER,
            end_datetime INTEGER,
            FOREIGN KEY (record_id) REFERENCES Records (id)
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS GeneratedWeeks (
            start_year INTEGER,
            start_week INTEGER, 
            end_year INTEGER, 
            end_week INTEGER
        )
        """)

        self.conn.commit()

    def extend_datetimes_for_weeks(self, start_year, start_week, weeks):
        """
        Extend the DateTimes table by generating data for the specified number of weeks
        starting from a given year and week.

        Args:
            start_year (int): The starting year.
            start_week (int): The starting ISO week.
            weeks (int): Number of weeks to generate.
        """
        start = datetime.strptime(f"{start_year} {start_week} 1", "%G %V %u")
        end = start + timedelta(weeks=weeks)

        start_year, start_week = start.isocalendar()[:2]
        end_year, end_week = end.isocalendar()[:2]

        self.cursor.execute(
            "SELECT start_year, start_week, end_year, end_week FROM GeneratedWeeks"
        )
        cached_ranges = self.cursor.fetchall()

        # Determine the full range that needs to be generated
        min_year = (
            min(cached_ranges, key=lambda x: x[0])[0] if cached_ranges else start_year
        )
        min_week = (
            min(cached_ranges, key=lambda x: x[1])[1] if cached_ranges else start_week
        )
        max_year = (
            max(cached_ranges, key=lambda x: x[2])[2] if cached_ranges else end_year
        )
        max_week = (
            max(cached_ranges, key=lambda x: x[3])[3] if cached_ranges else end_week
        )

        # Expand the range to include gaps and requested period
        if start_year < min_year or (start_year == min_year and start_week < min_week):
            min_year, min_week = start_year, start_week
        if end_year > max_year or (end_year == max_year and end_week > max_week):
            max_year, max_week = end_year, end_week

        first_day = datetime.strptime(f"{min_year} {min_week} 1", "%G %V %u")
        last_day = datetime.strptime(
            f"{max_year} {max_week} 1", "%G %V %u"
        ) + timedelta(days=6)

        # Generate new datetimes for the extended range
        self.generate_datetimes_for_period(first_day, last_day)

        # Update the GeneratedWeeks table
        self.cursor.execute("DELETE FROM GeneratedWeeks")  # Clear old entries
        self.cursor.execute(
            """
        INSERT INTO GeneratedWeeks (start_year, start_week, end_year, end_week)
        VALUES (?, ?, ?, ?)
        """,
            (min_year, min_week, max_year, max_week),
        )

        self.conn.commit()

    def generate_datetimes_for_period(self, start_date, end_date):
        """
        Populate the DateTimes table with datetimes for all records within the specified range.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.
        """
        # Fetch all records with their rrule strings, extents, and processed state
        self.cursor.execute("SELECT id, rrulestr, extent, processed FROM Records")
        records = self.cursor.fetchall()

        for record_id, rule_str, extent, processed in records:
            # Skip finite recurrences that have already been processed
            if processed == 1:
                if (
                    "RRULE" not in rule_str
                    or "COUNT=" in rule_str
                    or "UNTIL=" in rule_str
                ):
                    continue

            # Replace any escaped newline characters in rrulestr
            rule_str = rule_str.replace("\\N", "\n").replace("\\n", "\n")

            # Generate occurrences for the given range
            try:
                occurrences = self.generate_datetimes(
                    rule_str, extent, start_date, end_date
                )

                for start_dt, end_dt in occurrences:
                    self.cursor.execute(
                        """
                    INSERT INTO DateTimes (record_id, start_datetime, end_datetime)
                    VALUES (?, ?, ?)
                    """,
                        (record_id, int(start_dt.timestamp()), int(end_dt.timestamp())),
                    )
            except Exception as e:
                print(
                    f"Error processing rrulestr for record_id {record_id}: {rule_str}"
                )
                print(e)

            # Mark finite recurrences as processed
            if "RRULE" not in rule_str or "COUNT=" in rule_str or "UNTIL=" in rule_str:
                self.cursor.execute(
                    "UPDATE Records SET processed = 1 WHERE id = ?", (record_id,)
                )

        self.conn.commit()

    def generate_datetimes(self, rule_str, extent, start_date, end_date):
        """
        Generate occurrences for a given rrulestr within the specified date range.

        Args:
            rule_str (str): The rrule string defining the recurrence rule.
            extent (int): The duration of each occurrence in minutes.
            start_date (datetime): The start of the range.
            end_date (datetime): The end of the range.

        Returns:
            List[Tuple[datetime, datetime]]: A list of (start_dt, end_dt) tuples.
        """
        from dateutil.rrule import rrulestr

        rule = rrulestr(rule_str, dtstart=start_date)
        occurrences = list(rule.between(start_date, end_date, inc=True))

        # Create (start, end) pairs
        results = []
        for start_dt in occurrences:
            end_dt = start_dt + timedelta(minutes=extent) if extent else start_dt
            results.append((start_dt, end_dt))

        return results

    def get_events_for_period(self, start_date, end_date):
        """
        Retrieve all events that occur or overlap within a specified period,
        including the type, name, and ID of each event, ordered by start time.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.

        Returns:
            List[Tuple[int, int, str, str, int]]: A list of tuples containing
            start and end timestamps, event type, event name, and event ID.
        """
        self.cursor.execute(
            """
        SELECT dt.start_datetime, dt.end_datetime, r.type, r.name, r.id 
        FROM DateTimes dt
        JOIN Records r ON dt.record_id = r.id
        WHERE dt.start_datetime < ? AND dt.end_datetime > ?
        ORDER BY dt.start_datetime
        """,
            (end_date.timestamp(), start_date.timestamp()),
        )
        return self.cursor.fetchall()

    def process_events(self, start_date, end_date):
        """
        Process events and split across days for display.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.

        Returns:
            Dict[int, Dict[int, Dict[int, List[Tuple]]]]: Nested dictionary grouped by year, week, and weekday.
        """
        from collections import defaultdict
        from datetime import datetime, timedelta
        from dateutil.tz import gettz

        # Retrieve all events for the specified period
        events = self.get_events_for_period(start_date, end_date)

        # Group events by ISO year, week, and weekday
        grouped_events = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for start_ts, end_ts, event_type, name, id in events:
            # Convert timestamps to localized datetime objects
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

            # Process and split events across day boundaries
            while start_dt.date() <= end_dt.date():
                # Compute the end time for the current day
                day_end = min(
                    end_dt,
                    datetime.combine(
                        start_dt.date(), datetime.max.time()
                    ),  # End of the current day
                )

                # Group by ISO year, week, and weekday
                iso_year, iso_week, iso_weekday = start_dt.isocalendar()
                # grouped_events[iso_year][iso_week][iso_weekday].append((start_dt, day_end, event_type, name))
                grouped_events[iso_year][iso_week][iso_weekday].append(
                    (start_dt, day_end)
                )

                # Move to the start of the next day
                start_dt = datetime.combine(
                    start_dt.date() + timedelta(days=1), datetime.min.time()
                )

        return grouped_events

    def event_tuple_to_minutes(
        self, start_dt: datetime, end_dt: datetime
    ) -> Tuple[int, int]:
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

    def get_busy_bar(self, lop: List[Tuple[int, int]]) -> Tuple[str, str]:
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
                continue
            if e <= B:
                busy_minutes.append((b, e))
                b = B
                e = E
            else:
                busy_minutes.append((b, B))
                if e <= E:
                    conflict_minutes.append((B, e))
                    b = e
                    e = E
                else:
                    conflict_minutes.append((B, E))
                    b = E
                    e = e

        busy_minutes.append((b, e))

        for b, e in busy_minutes:
            if not e > b:
                continue
            start = bisect.bisect_left(SLOT_MINUTES, b)
            end = max(start, bisect.bisect_right(SLOT_MINUTES, e) - 1)
            for i in range(start, end + 1):
                busy_conf[SLOT_MINUTES[i]] = 1

        for b, e in conflict_minutes:
            if not e > b:
                continue
            start = bisect.bisect_left(SLOT_MINUTES, b)
            end = max(start, bisect.bisect_right(SLOT_MINUTES, e) - 1)
            for i in range(start, end + 1):
                busy_conf[SLOT_MINUTES[i]] = 2

        busy_bar = []
        have_busy = False
        for i in range(len(SLOT_MINUTES) - 1):
            if busy_conf[SLOT_MINUTES[i]] == 0:
                busy_bar.append(f"[dim]{FREE}[/dim]")
            elif busy_conf[SLOT_MINUTES[i]] == 1:
                have_busy = True
                busy_bar.append(f"[{BUSY_COLOR}]{BUSY}[/{BUSY_COLOR}]")
            else:
                have_busy = True
                busy_bar.append(f"[{CONF_COLOR}]{BUSY}[/{CONF_COLOR}]")

        busy_str = (
            f"\n[{FRAME_COLOR}]{''.join(busy_bar)}[/{FRAME_COLOR}]"
            if have_busy
            else "\n"
        )
        aday_str = f"{ADAY}" if allday > 0 else ""

        return aday_str, busy_str
