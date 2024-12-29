# Notes

## For Chat


The main "view" would display 4 weeks. There would be a heading for the period, e.g., "Oct 28 - Nov 24, 2024", 7 columns for the weekdays "MO", "TU", "WE", "TH", "FR", "SA", "SU" and 4 rows (one for each of the weeks) with the relevant month day displayed in each the relevant row and column cell, e.g, "28" in the top left and "24" in the bottom right.

The key is to be able to obtain all the items from Items that have scheduled datetimes falling within the 4 week period and similarly for any other 4 week period.



  ```python

    CREATE TABLE DateTimes (
        record_id INTEGER,
        start_datetime TEXT,
        end_datetime TEXT,
        year INTEGER GENERATED ALWAYS AS (CAST(strftime('%Y', start_datetime) AS INTEGER)) VIRTUAL,
        week INTEGER GENERATED ALWAYS AS (CAST(strftime('%W', start_datetime) AS INTEGER)) VIRTUAL,
        weekday INTEGER GENERATED ALWAYS AS (CAST(strftime('%w', start_datetime) AS INTEGER)) VIRTUAL,
        start_minutes INTEGER GENERATED ALWAYS AS (CAST(strftime('%M', start_datetime)+60*strftime('%H', datetime) AS INTEGER)) VIRTUAL,
        end_minutes INTEGER GENERATED ALWAYS AS (CAST(strftime('%M', end_datetime)+60*strftime('%H', datetime) AS INTEGER)) VIRTUAL,
        FOREIGN KEY (record_id) REFERENCES Records (id)
    )

  ```

## shared but independent

types:
    *: event
    -: task 
    %: note 
    +: timer 


> 
    project/
        shared_mate/
            __init__.py
            database.py
            accounts.py
            times.py
        time_mate/
            __init__.py
            main.py
        task_mate/
            __init__.py
            main.py
        event_mate/
            __init__.py
            main.py
        note_mate/
            __init__.py
            main.py

```python
    CREATE TABLE IF NOT EXISTS Events (
        id INTEGER PRIMARY KEY,
        account_id INTEGER,
        title TEXT NOT NULL,
        start_time INTEGER,
        end_time INTEGER,
        location TEXT,
        FOREIGN KEY (account_id) REFERENCES Accounts (id)
    );

CREATE TABLE IF NOT EXISTS Meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR REPLACE INTO Meta (key, value) VALUES ('schema_version', '1.0');

ALTER TABLE Times ADD COLUMN new_column_name TEXT DEFAULT '';  

    def check_and_upgrade_schema(conn):
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS Meta (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("SELECT value FROM Meta WHERE key = 'schema_version'")
        result = cursor.fetchone()
        current_version = result[0] if result else None

        if current_version is None:
            # Initialize the schema
            cursor.execute("INSERT INTO Meta (key, value) VALUES ('schema_version', '1.0')")
        elif current_version == '1.0':
            # Upgrade to version 1.1
            cursor.execute("ALTER TABLE Times ADD COLUMN new_column_name TEXT DEFAULT ''")
            cursor.execute("UPDATE Meta SET value = '1.1' WHERE key = 'schema_version'")
        conn.commit()

    def add_events_table(conn):
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Meta WHERE key = 'schema_version'")
        current_version = cursor.fetchone()
        if current_version < '1.1':  # Assuming Events was included at version 1.1
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Events (
                id INTEGER PRIMARY KEY,
                account_id INTEGER,
                title TEXT NOT NULL,
                start_time INTEGER,
                end_time INTEGER,
                location TEXT,
                FOREIGN KEY (account_id) REFERENCES Accounts (id)
            )
            """)
            cursor.execute("UPDATE Meta SET value = '1.1' WHERE key = 'schema_version'")
            conn.commit()    
```

```python
    from setuptools import setup, find_packages

    setup(
        name="netm",
        version="0.1.0",
        packages=find_packages(),
        install_requires=[
            # List dependencies here, e.g., 'click', 'prompt_toolkit', etc.
        ],
        entry_points={
            "console_scripts": [
                "timemate=time_mate.main:main",
                "taskmate=task_mate.main:main",
                "eventmate=event_mate.main:main",
                "notemate=note_mate.main:main",
            ],
        },
    )
```

## fields - old and new

    - [!] keep
    - [?] maybe scrap
    - [x] definitely scrap

### item types

    - [ ] * event
    - [ ] - task
    - [ ] % journal
    - [ ] ! inbox
    - [ ] ~ goal

### flags

    - [ ] ✓ done
    - [ ] > beginning soon
    - [ ] < past due

### new @keys

- @s allow many, &r rrule freq and friends optional in each. Combined and stored as rrulestr.

- @t tab (account, replaces index). #tags replaces @t tag

### @keys

    - [x] +: include. list of datetimes to include -> multiple @s
    - [ ] @-: exclude. list of datetimes to exclude
    - [ ] @a*: alert. list of + (before) or - (after) periods: list of commands
    - [ ] @b: beginby. integer (number of days before)
    - [ ] @c: calendar. string
    - [ ] @d: description. string
    - [ ] @e: extent. timeperiod
    - [ ] @f: finished. datetime
    - [ ] @g: goto. string (url or filepath)
    - [ ] @h: history. (for repeating tasks, a list of the most recent completion datetimes)
    - [x] @i: index. forward slash delimited string. E.g., client/project/activity -> @t
    - [ ] @j*: job summary. string, optionally followed by job &key entries
    - [ ] @k*: doc_id. connect this reminder to the one corresponding to doc_id.
    - [ ] @l: location (aka context). forward slash delimited string. E.g., home/maintenance
    - [ ] @m: mask. string stored in obfuscated form
    - [ ] @n*: attendee. string using “[name:] address” format. If “address” begins with exactly 10 digits followed by an “@” it is treated as a mobile phone number. Otherwise it is treated as an email address. The optional “name:” can be used to facilitate autocompletion.
    - [ ] @o: overdue. character from (r) restart, (s) skip, (k) keep. Defaults to (k) keep.
    - [ ] @p: priority. integer from 0 (none), 1 (low), 2 (normal), 3 (high), 4 (urgent)
    - [ ] @q: quota. Used in goals to specify the attributes. E.g., @q 3m: 2, 3 would specify a goal of 3 completions per (m)onth for month numbers 2 and 3 each year. A range can also be used to specify period numbers, e.g., @q 3: 1-5. The default, absent a periods specification, is to apply the goal to all of the specified periods. Other options for period include (y)ear, (q)uarter and (w)eek and (d)day. Week is the default. The default for the number of periods is 0 which entails repeating indefinitely.
    - [x] @r: repetition frequency, a character from (y)early, (m)onthly, (w)eekly, (d)aily, (h)ourly or mi(n)utely, optionally followed by repetition &key entries -> &r in @s
    - [ ] @s: scheduled date or datetime
    - [x] @t*: tag. string -> #hash tags
    - [ ] @u*: usedtime. string using “timeperiod spent: ending datetime” format
    - [ ] @w: wrap. A pair of before and after timeperiods to extend the busy period for an event, e.g., for travel time to and/or from the location of the event. Use 0m as one of the timeperiods to avoid a wrap in that direction.
    - [ ] @x*: expansion. string
    - [ ] @z: timezone. string. A timezone specification, such as ‘US/Eastern’ or ‘Europe/Paris’ for aware datetimes or ‘float’, to indicate a naive or floating datetime. Datetime entries in the item are interpreted as belonging to the specified timezone when the entry is saved. The current timezone is the default when @z is not specified. Aware datetimes are converted to UTC (coordinated universal time) when stored and the @z entry, now irrelevant, is discarded.

### &keys for use with @j

    - [ ] &s: scheduled: period relative to @s entry (default 0m) at which job is scheduled to be completed
    - [ ] &a: alert: list of + (before) or - (after) periods relative to &s: list of cmd names from the users configuration file
    - [ ] &b: beginby. integer number of days before &s
    - [ ] &d: description. string
    - [ ] &e: extent. period
    - [ ] &f: finished. datetime
    - [ ] &l: location/context. string
    - [ ] &m: masked. string stored in obfuscated form
    - [ ] &i: job unique id. string
    - [ ] &p: prerequisites. list of ids of immediate prereqs
    - [ ] &u*: usedtime. string using “timeperiod spent: ending datetime” format

### &keys for use with @r

    - [ ] &c: count. integer number of repetitions
    - [ ] &E: easter. number of days before (-), on (0) or after (+) Easter
    - [ ] &h: hour. list of integers in 0 … 23
    - [ ] &i: interval. positive integer to apply to frequency, e.g., with @r m &i 3, repetition would occur every 3 months
    - [ ] &m: monthday. list of integers 1 … 31
    - [ ] &M: month number. list of integers in 1 … 12
    - [ ] &n: minute. list of integers in 0 … 59
    - [ ] &s: set position: integer
    - [ ] &u: until. datetime
    - [ ] &w: weekday. list from SU, MO, …, SA possibly prepended with a positive or negative integer
    - [ ] &W: week number. list of integers in 1, …, 53 

## jobs and prerequisites

### dog house example

In a future, TaskMate app, I may have a task or project that has component jobs. Here is a simple example of such a project:

>
    - dog house
        @j pickup lumber &i 0        
        @j pickup sandpaper &i 1 
        @j pickup paint &i 2
        @j cut pieces &i 3 &p 0
        @j assemble pieces &i 4 &p 3 
        @j sand &i 5 &p 1, 4 
        @j paint &i 6 &p 2, 5

or

>
    - dog house @j
        a. pickup lumber      
        b. pickup sandpaper 
        c. pickup paint
        d. cut pieces &p a
        e. assemble pieces &p d 
        f. sand &p b, e 
        g. paint &p c, f

The &i entries are just the id's of the jobs, numbered consecutively. The first three jobs have no prerequisites but the remaining jobs have prerequisites indicated by the &p entries. E.g., job 3, cut pieces, has the prerequisite, &p 0, that job 0, pickup lumber, be finished first. The completion of a job would be indicated by the addition of an &f entry with the datetime of the completion.

The problem is that some of the jobs have more than one prerequisite, e.g., job 5, sand requires that jobs 1 and 4 be finished and even ones with only one "direct" prerequisite such as job 4, which requires that job 3 be finished first, indirectly requires that job 0 also be finished since job 0 was a prerequisite for job 3.

The challenge is to avoid the need for lists which leads me to the idea of using a binary representation of prerequisites as described in the following table:

| job_id | bin dir | bin ind | int dir | int ind |
| ------ | ------- | ------- |---------|---------|
| 0      | 0000000 | 0000000 | 0       | 0       |
| 1      | 0000000 | 0000000 | 0       | 0       |
| 2      | 0000000 | 0000000 | 0       | 0       |
| 3      | 1000000 | 1000000 | 64      | 64      |
| 4      | 0001000 | 1001000 | 8       | 72      |
| 5      | 0100100 | 1101100 | 36      | 108     |
| 6      | 0010010 | 1111110 | 18      | 126     |

The "bin dir" (binary direct) column gives a binary string representation of the direct prerequisites for each job where there are 7 binary characters, one for each job. Taking job 5 as an example, the string '0100100' with 1's at positions 1 and 4, means that jobs 1 and 4 are (as yet unfinished) prerequisites and the 0's everywhere else mean that no other jobs are (unfinished) prerequisites for job 5. The "bin ind" (binary indirect) shows both the direct and indirect prerequisites. Treating the binary strings as binary numbers, the "int dir" and "int ind" columns give the integer equivalents.

There are some interesting aspects to the integer columns.

1. An integer column can represent the prerequisites for a job (no need for lists)
2. The indirect prerequisites for a job are just the cumulative sum of the direct prerequisite column, i.e., int_ind[j] is just sum for i <= j of int_dir.  
3. The process of updating the prerequisites when job 'i' is completed is pretty simple
    - in each "bin dir" entry replace the character in position 'i' with a 0 or
    - even simpler, replace the number in "int dir" with a 0
4. The staus of job i is pretty simple to obtain:
    - 'finished' has an &f entry
    - 'available' (no unfinished prerequisites) if int_dir[i] == 0
    - 'waiting' (has unfinished prerequisites) if int_dir[i] > 0
    - the unfinished prerequisites, if any, correspond to the positions of the 1's in the binary equivalent of int_ind[i]

What is being assumed about the project? Here is is assumed that

1. no job is a prequisite for itself (either directly or indirectly) and
2. the jobs can be listed in an order in which no job has a prequisite that occurs later in the list
If it is presumed that it is possible to compete the project by finishing the component jobs one at a time without violating any unfinished prerequisite requirements then (1) follows immediately and (2) from the observation that if there were no such order, then the project could not, in fact, be completed without violating an unfinished prequisite requirement.

This almost seems to good to be true. Am I missing something?

```python
import click

def display_jobs(jobs):
    """Display the current list of jobs."""
    click.echo("\nJobs so far:")
    for job_id, job in jobs.items():
        prereqs = ", ".join(map(str, job["prerequisites"])) if job["prerequisites"] else "None"
        click.echo(f"{job_id}: {job['name']} (Prerequisites: {prereqs})")
    click.echo("\n")


@click.command()
def main():
    jobs = {}  # Dictionary to store jobs with their details
    job_id = 0  # Auto-incrementing ID for jobs

    while True:
        # Display jobs entered so far
        if jobs:
            display_jobs(jobs)
        
        # Prompt for job name
        job_name = click.prompt(f"Enter the name of job {job_id} (or 'done' to finish)", default="", show_default=False).strip()
        if job_name.lower() == "done" or not job_name:
            break

        # Prompt for prerequisites
        if jobs:
            prereq_input = click.prompt(
                f"Enter prerequisites for job {job_id} as comma-separated IDs (or leave blank if none)", 
                default="", 
                show_default=False
            ).strip()
            prerequisites = [int(p.strip()) for p in prereq_input.split(",") if p.strip().isdigit()]
        else:
            prerequisites = []

        # Validate prerequisites
        invalid_prereqs = [p for p in prerequisites if p not in jobs]
        if invalid_prereqs:
            click.echo(f"Invalid prerequisites: {invalid_prereqs}. Please try again.")
            continue

        # Add the job
        jobs[job_id] = {
            "name": job_name,
            "prerequisites": prerequisites,
            "finished": None,
        }
        job_id += 1

    # Display final list of jobs
    click.echo("\nFinal list of jobs:")
    display_jobs(jobs)
    click.echo("Thank you! Your jobs have been recorded.")

if __name__ == "__main__":
    main()
```

>
    def encode_binary_str(binary_str: str):
        binary_list = [int(x) for x in list(binary_str)]
        result = 0
        for bit in binary_list:
            result = (result << 1) | bit
        return result

>
    def decode_to_binary_str(encoded_int: int, length=4):
        binary_list = []
        for _ in range(length):
            binary_list.append(encoded_int & 1)
            encoded_int >>= 1
        return ''.join(binary_list[::-1])

# Example usage

    binary_list = [0, 1, 0, 1]
    encoded = encode_binary_list(binary_list)
    print(f"Encoded integer: {encoded}")  # Output: 5

    decoded_list = decode_to_binary_list(encoded, len(binary_list))
    print(f"Decoded list: {decoded_list}")  # Output: [0, 1, 0, 1]

```


## hash-tags as many-to-many table
```python
    import sqlite3
    import re

    # Connect to the database
    conn = sqlite3.connect("example.db")
    c = conn.cursor()

    # Create tables
    c.execute("""
    CREATE TABLE IF NOT EXISTS Items (
        id INTEGER PRIMARY KEY,
        description TEXT
    );
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS Tags (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    );
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ItemTags (
        item_id INTEGER,
        tag_id INTEGER,
        PRIMARY KEY (item_id, tag_id),
        FOREIGN KEY (item_id) REFERENCES Items (id),
        FOREIGN KEY (tag_id) REFERENCES Tags (id)
    );
    """)
    conn.commit()

    # Function to extract tags from description
    def extract_tags(description):
        return re.findall(r"#(\w+)", description)

    # Function to insert an item and record tags
    def insert_item(description):
        # Insert the item
        c.execute("INSERT INTO Items (description) VALUES (?)", (description,))
        item_id = c.lastrowid

        # Extract tags
        tags = extract_tags(description)

        for tag in tags:
            # Insert tag into Tags table if not exists
            c.execute("INSERT OR IGNORE INTO Tags (name) VALUES (?)", (tag,))
            
            # Get the tag_id
            c.execute("SELECT id FROM Tags WHERE name = ?", (tag,))
            tag_id = c.fetchone()[0]
            
            # Insert into ItemTags table
            c.execute("INSERT OR IGNORE INTO ItemTags (item_id, tag_id) VALUES (?, ?)", (item_id, tag_id))

        conn.commit()

    # Example Usage
    insert_item("This is a test description with #tag1 and #tag2.")
    insert_item("Another item with #tag2 and #tag3.")

```

### Find all tags for an item

```python
    SELECT Tags.name 
    FROM Tags 
    INNER JOIN ItemTags ON Tags.id = ItemTags.tag_id
    WHERE ItemTags.item_id = 1;
```

### Find all items with a specific tag

```python
    SELECT Items.memorandum 
    FROM Items 
    INNER JOIN ItemTags ON Items.id = ItemTags.item_id
    INNER JOIN Tags ON Tags.id = ItemTags.tag_id
    WHERE Tags.name = 'tag2';
```
