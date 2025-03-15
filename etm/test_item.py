import sys
import os

sys.path.append(os.path.dirname(__file__))  # for pytest
from item import Item
from datetime import datetime, date, timedelta
from dateutil.rrule import rrule, rruleset, rrulestr, DAILY
from dateutil.tz import gettz
from common import timedelta_string_to_seconds


def pprint(obj):
    line = "\n" + "-" * 10 + "\n"
    print(line, obj.__repr__(), line)


json_entry = {
    "created": "{T}:20240712T1052",
    "itemtype": "*",
    "subject": "Thanksgiving",
    "s": "{T}:20101126T0500",
    "r": "RRULE:FREQ=MONTHLY;BYMONTH=11;BYDAY=+4THU",
    "modified": "{T}:20240712T1054",
}

string_entry = """\
DTSTART:20241028T133000
RRULE:FREQ=DAILY;COUNT=14
RRULE:FREQ=DAILY;INTERVAL=2;COUNT=7
RDATE:20241104T134500
RDATE:20241105T151500
EXDATE:20241104T133000
"""


def test_repeat_from_rruleset():
    pacific = gettz("US/Pacific")
    mountain = gettz("America/Denver")
    central = gettz("US/Central")
    eastern = gettz("America/New_York")
    local = gettz()
    utc = gettz("UTC")
    naive = None

    tz = None
    # Define the start date

    rules_lst = []
    start_date = datetime(2024, 10, 28, 13, 30, tzinfo=tz)  # 0:30 on Mon Oct 28, 2024

    # Create a recurrence rule for daily events
    rule1 = rrule(freq=DAILY, dtstart=start_date, count=14)
    rules_lst.append(str(rule1))
    # Create another recurrence rule for specific days (e.g., every 2 days)
    rule2 = rrule(freq=DAILY, dtstart=start_date, interval=2, count=7)
    rules_lst.append(str(rule2))

    # Create an rruleset
    rules = rruleset()

    # Add the rules to the rruleset
    rules.rrule(rule1)
    rules.rrule(rule2)

    # Add a specific date to include
    plusdates = [
        datetime(2024, 11, 4, 13, 45, tzinfo=tz),
        datetime(2024, 11, 5, 15, 15, tzinfo=tz),
    ]
    for dt in plusdates:
        rules.rdate(dt)
        rules_lst.append(dt.strftime("RDATE:%Y%m%dT%H%M%S"))
    # Add a specific date to exclude
    minusdates = [
        datetime(2024, 11, 4, 13, 30, tzinfo=tz),
    ]
    for dt in minusdates:
        rules.exdate(dt)
        rules_lst.append(dt.strftime("EXDATE:%Y%m%dT%H%M%S"))

    # Generate the occurrences of the event
    occurrences = list(rules)

    # start_date = datetime(2024, 10, 28, 13, 30).astimezone()
    # rr = Instances(rules)
    # rr.set_startdt(start_date)
    # rr.add_rule(rhsh)
    # occurrences = list(rr.ruleset)
    for occurrence in occurrences:
        print(occurrence.strftime("  %a %Y-%m-%d %H:%M %Z %z"))


line = "\n" + "-" * 10 + "\n"


def test_item_entry():
    item = Item()
    partial_strings = [
        "",
        "- ",
        "- T",
        "- Thanksgiving ",
        "- Thanksgiving @",
        "- Thanksgiving @s 11/26",
        "- Thanksgiving @s 2010/11/26 ",
        "* Thanksgiving @s 2010/11/26 ",
        "* Thanksgiving @s 2010/11/26 @",
        "* Thanksgiving @s 2010/11/26 @r ",
        "* Thanksgiving @s 2010/11/26 @r z",
        "* Thanksgiving @s 2010/11/26 @r y ",
        "* Thanksgiving @s 2010/11/26 @r y &",
        "* Thanksgiving @s 2010/11/26 @r y &m 11",
        "* Thanksgiving @s 2010/11/26 @r y &m 11 &w 4TH",
        "* Thanksgiving @s 2010/11/26 @r y &m 11 &w +4TH",
    ]

    # FIXME: duplicates in rrule_tokens

    line = "\n" + "-" * 10 + "\n"
    print("\nparsing partial_strings")
    for s in partial_strings:
        print(f"\nprocessing: {s}")
        try:
            item.parse_input(s)
            # if item.rrule_tokens:
            #     success, rruleset_str = item.finalize_rruleset()
            #     print(f"\n{success = } for:\n'{item.entry}'{line}{rruleset_str}{line}")
        except Exception as e:
            print(f"   {e = }")
    pprint(item.item)
    print()


def test_timedelta_string_to_seconds():
    print(
        f"timedelta_string_to_seconds({'90m'}) = {timedelta_string_to_seconds('90m')}"
    )


def test_do_alert():
    item = Item()
    item.parse_input(
        "- with alerts @s 2025-03-14 4pm @e 90m @a 30m, 15m, 0m, -1h: d, c, e @d testing alert"
    )
    pprint(item.item)


def test_rruleset_from_item():
    item = Item()
    item.parse_input(
        "* rdates and exdates @s 2024-08-07 4p @r w &i 2 &w WE @r w &w MO @+ 2024-08-09 2p, 2024-08-16 2p @- 2024-08-21 4p"
    )
    # if item.rrule_tokens:
    #     success, rruleset_str = item.finalize_rruleset()
    #     print(f"\n{success = } for:\n'{item.entry}'{line}{rruleset_str}{line}" )
    pprint(item.item)


def test_rrule_to_entry():
    item = Item()
    input_str = "* rdates and exdates @s 2024-08-07 4:00pm @r w &i 2 &w WE @r w &w MO @+ 2024-08-09 2:30pm, 2024-08-16 1:45pm @- 2024-08-21 4:00p"

    item.parse_input(input_str)
    # if item.rrule_tokens:
    #     success, rruleset_str = item.finalize_rruleset()
    # if not success:
    #     return False
    # output_str = item.rrule_to_entry(rruleset_str)

    # print(f"\nstarting complete entry:{line}{input_str}{line}")
    # print(f"resulting rruleset:{line}{rruleset_str}{line}")
    # print(f"back to the @r entry:{line}{output_str}{line}")


def test_task_with_jobs():
    item = Item()
    input_str = "- task with jobs @s 2024-08-07 4:00pm @j alpha &s 5d &d whatever @j beta &d more of the same &p 1 @j gamma plus &p 1 &d last one"

    item.parse_input(input_str)
    if item.job_tokens:
        print(f"job_tokens:\n{item.job_tokens = }")
    print(f"jobs for {item.item['subject']}:")
    for job in item.jobs:
        print(f"  {job}")

    pprint(item.item)


# test_repeat_from_rruleset()
test_timedelta_string_to_seconds()
test_do_alert()
test_item_entry()
# test_rruleset_from_item()
# test_rrule_to_entry()
# test_task_with_jobs()
