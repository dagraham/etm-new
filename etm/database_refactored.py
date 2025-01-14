import os
import sqlite3
from typing import Optional
from bisect import bisect_left, bisect_right
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

    # def old_get_busy_bar(self, lop: List[Tuple[int, int]]) -> Tuple[str, str]:
    #     busy_conf = {x: 0 for x in SLOT_MINUTES}
    #     # keys = 240, 480, ...
    #     # values = 0, 1, 2 (0: free, 1: busy, 2: conflict)
    #     # times in 0 - 240 are charged to 240, in 240 - 480 are charged to 480, etc.
    #
    #     busy_minutes = []
    #     conflict_minutes = []
    #     lop.sort()
    #     (b, e) = (0, 0)
    #     allday = 0
    #
    #     for B, E in lop:
    #         # this event begins at B and ends at E
    #         if B == 0 and E == 0:  # starts and ends at midnight
    #             allday += 1
    #         if E == B and not allday:  # starts and ends at the same time
    #             continue
    #         if e <= B:
    #             # e and b are 0 at the beginning,
    #             # but remember the relevant begin and ends from previous events
    #             # if the current event's begin is greater than the last event's end
    #             # then no conflict, just add the last event to busy_minutes
    #             busy_minutes.append((b, e))
    #             b = B
    #             e = E
    #         else:
    #             # if the current event's begin is less than the last event's end
    #             # then there is a conflict so
    #             # add b to B (the non overlapping part) to busy_minutes
    #             # add B to e (the overlapping part) to conflict_minutes if B < e
    #             # and otherwise add B to E to conflict_minutes
    #             # and update b and e accordingly
    #             busy_minutes.append((b, B))
    #             if e <= E:
    #                 conflict_minutes.append((B, e))
    #                 b = e
    #                 e = E
    #             else:
    #                 conflict_minutes.append((B, E))
    #                 b = E
    #                 e = e
    #     # add the last b - e to busy_minutes
    #     busy_minutes.append((b, e))
    #
    #     for b, e in busy_minutes:
    #         if not e > b:
    #             continue
    #         # bisect_left and bisect_right finds the smallest and largest indices
    #         # in SLOT_MINUTES where b and e can be inserted and maintain the order
    #         # e.g. if SLOT_MINUTES = [0, 240, 480, 720, 960, 1200, 1440]
    #         # and b = 300 and e = 900, bisect_left(SLOT_MINUTES, b) = 2,
    #         # bisect_right(SLOT_MINUTES, e) = 4
    #         start = bisect_left(SLOT_MINUTES, b)
    #         end = max(start, bisect_right(SLOT_MINUTES, e) - 1)
    #         for i in range(start, end + 1):
    #             busy_conf[SLOT_MINUTES[i]] = 1
    #
    #     for b, e in conflict_minutes:
    #         if not e > b:
    #             continue
    #         start = bisect_left(SLOT_MINUTES, b)
    #         end = max(start, bisect_right(SLOT_MINUTES, e) - 1)
    #         for i in range(start, end + 1):
    #             busy_conf[SLOT_MINUTES[i]] = 2
    #
    #     busy_bar = ["" for x in SLOT_MINUTES]
    #     have_busy = False
    #     for i in range(len(SLOT_MINUTES) - 1):
    #         if busy_conf[SLOT_MINUTES[i]] == 0:
    #             busy_bar[i] = f"[dim]{FREE}[/dim]"
    #         elif busy_conf[SLOT_MINUTES[i]] == 1:
    #             have_busy = True
    #             busy_bar[i] = f"[{BUSY_COLOR}]{BUSY}[/{BUSY_COLOR}]"
    #         else:
    #             have_busy = True
    #             busy_bar[i] = f"[{CONF_COLOR}]{BUSY}[/{CONF_COLOR}]"
    #
    #     busy_str = (
    #         f"\n[{FRAME_COLOR}]{''.join(busy_bar)}[/{FRAME_COLOR}]"
    #         if have_busy
    #         else "\n"
    #     )
    #     aday_str = f"{ADAY}" if allday > 0 else ""
    #
    #     return aday_str, busy_str

    def get_busy_bar(self, events):
        """
        Determine slot states (0: free, 1: busy, 2: conflict) for a list of events.

        Args:
            L (List[int]): Sorted list of slot boundaries.
            events (List[Tuple[int, int]]): List of event tuples (start, end).

        Returns:
            List[int]: A list where 0 indicates a free slot, 1 indicates a busy slot,
                    and 2 indicates a conflicting slot.
        """
        # Initialize slot usage as empty lists
        L = SLOT_MINUTES
        slot_events = [[] for _ in range(len(L) - 1)]
        allday = 0

        for b, e in events:
            # Find the start and end slots for the current event

            if b == 0 and e == 0:
                allday += 1
            if e == b and not all_day:
                continue

            start_slot = bisect_left(L, b) - 1
            end_slot = bisect_left(L, e) - 1

            # Track the event in each affected slot
            for i in range(start_slot, min(len(slot_events), end_slot + 1)):
                if L[i + 1] > b and L[i] < e:  # Ensure overlap with the slot
                    slot_events[i].append((b, e))

        # Determine the state of each slot
        slots_state = []
        for i, events_in_slot in enumerate(slot_events):
            if not events_in_slot:
                # No events in the slot
                slots_state.append(0)
            elif len(events_in_slot) == 1:
                # Only one event in the slot, so it's busy but not conflicting
                slots_state.append(1)
            else:
                # Check for overlaps to determine if there's a conflict
                events_in_slot.sort()  # Sort events by start time
                conflict = False
                for j in range(len(events_in_slot) - 1):
                    _, end1 = events_in_slot[j]
                    start2, _ = events_in_slot[j + 1]
                    if start2 < end1:  # Overlap detected
                        conflict = True
                        break
                slots_state.append(2 if conflict else 1)

        busy_bar = ["_" for _ in range(len(slots_state))]
        have_busy = False
        for i in range(len(slots_state)):
            if slots_state[i] == 0:
                busy_bar[i] = f"[dim]{FREE}[/dim]"
            elif slots_state[i] == 1:
                have_busy = True
                busy_bar[i] = f"[{BUSY_COLOR}]{BUSY}[/{BUSY_COLOR}]"
            else:
                have_busy = True
                busy_bar[i] = f"[{CONF_COLOR}]{BUSY}[/{CONF_COLOR}]"

        # return slots_state, "".join(busy_bar)
        busy_str = (
            f"\n[{FRAME_COLOR}]{''.join(busy_bar)}[/{FRAME_COLOR}]"
            if have_busy
            else "\n"
        )

        aday_str = f"{ADAY}" if allday > 0 else ""

        return aday_str, busy_str
