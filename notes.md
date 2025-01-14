# Notes

## Scratch Pad

Suppose I have 6 "slots" corresponding to the intervals between integers in L = [0, 240, 480, 720, 960, 1300, 1440] and events that correspond tuples(b, e) of two integers each of which >=0 and <= 1440.

Think of the slot 1 as the tuple (0, 240), slot 2 as (240, 480), etc.

Now suppose I have an event (b, e) = (100, 200). Slot 1 should be busy for this event and all the other slots should be free. With (b, e) = (100, 240) this should still be true. But with (b, e) = (100, 241) slot 2 should be busy as well. With (b, e) = (240, 720), slots 2 and 3 should be busy.

How can I do this?

## Week-based views

### Why week based views

ETM has always been focused on weeks and has never supported a month view as such? Why?

1) Weeks are the only calendar constant. There are always 7 days in a week and weeks always start on the same weekday. In contrast, the number of days in a year depends on whether it is a leap year or not, the number of days in a month could be 28, 29, 30 or 31  depending on the month and, thanks to Daylight Savings Time, even the number of hours in a day could be 23, 24 or 25. And I've not even mentioned leap-seconds. A week is something you can hang your hat on.
2) Perhaps not independently, most peoples' schedules are based on a weekly cycle and people think in terms of weeks - even to the point of regarding a month as essentially equivalent to four weeks.
3) For most of us, the list of events for a typical week is manageable on standard computer display. On my phone, on the other hand, iCal defaults to a three day view, today and the following two days, and that is manageable on that screen.

What about a monthly view? One option would be to use a grid with 4 rows of 8 cells, the advantage is that this would just enough rows to fit every month. Here's March for example:
>
            March 2025
      1  2  3  4  5  6  7  8
      9 10 11 12 13 14 15 16
     17 18 19 20 21 22 23 24 
     25 26 27 28 29 30 31

My guess is most people would dislike this view. Why? I think it because the only way to make sense of a month is to divide it into weeks. This why every monthly calendar I have ever seen has 7 columns corresponding to the weekdays and one row for each week in the month.

If the table must have 7 columns corresponding to the weekdays, then how many rows? If only month days corresponding to a single month are to be displayed, then 4, 5 or 6 rows will be needed depending on the month. Four row months are quite rare. For 4 rows to be enough, it would need to be February in a non-leap year in which February 1 falls on a Monday. There are only 8 of these in the rest of the 21st century, (2027, 2038, 2049, 2055, 2066, 2077, 2083, 2094) - the rest of the ~900 months require either 5 or 6 rows. Here is a typical 6 row month:

>
          March 2025       
    Mo Tu We Th Fr Sa Su  
                    1  2  
     3  4  5  6  7  8  9  
    10 11 12 13 14 15 16  
    17 18 19 20 21 22 23  
    24 25 26 27 28 29 30  
    31                    

If 6 rows are needed, then the "monthly" option is to leave the other cells empty as displayed. But there is also a "weekly" option to use the empty cells for dates from the preceeding and following months:

     Feb 24 - Apr 6 2025      
    Mo Tu We Th Fr Sa Su  
    24 25 26 27 28  1  2  
     3  4  5  6  7  8  9  
    10 11 12 13 14 15 16  
    17 18 19 20 21 22 23  
    24 25 26 27 28 29 30  
    31  1  2  3  4  5  6  

The switch from "monthly" to "weekly" has pros and cons:

Pros:

- Fully utilizes available table cells.
- Emphasizes the natural association between rows and weeks. In "weekly" March, e.g., the first row is associated with week number 9 of 2025, Feb 24 - Apr 2 so selecting that row can automatically display the list of items scheduled for that week. What is the association for the first row of "monthly" March? To March 1 and 2 and just the items scheduled for those two days?
- Allows scrolling by a week at a time. It's always possible to see a week in the context of the surrounding weeks, both before and after. With a "monthly" view, the only way to scroll is by a month and, for the first and last weeks of a month, this means no way of seeing the week in the context of the surrounding weeks.
- Allows smooth display transitions. The display will not jump when scrolling from period to period because the same number of rows are always required for the display.

Cons:

- The title of the table becomes more complicated. Instead of just the month and year, the dates of the first and last days are needed.

I think it comes down to this. If the necessity of having a grid with 7 columns corresponding to the weekdays is accepted,
then the only question is how many rows. If only showing a month is required, then the number of rows will depend up the month, many cells in the table will be empty and scrolling will be limited to a month at a time. If the "only a month" requirement is relaxed, then the number of rows can be fixed, the grid will always be full and scrolling can be by a week at a time.

I think the only question is how many rows. I started thinking biweekly (2 rows) but now think that 4 rows is probably the best compromise in the spectrum from too little to too much information.

### Why not month view

ETM has always been focused on week views

## Pastdue tasks

- [ ] All instances listed together by #task and #date with tasks sorted by the date of the first instances
- [ ] Past due list as an appendage to details of the current date or as a separate list. Better separate list.
- [ ] #Beginbys with details of the current date

```python
type_to_color = {
  '*': 'yellow',  # event 
  '-': 'red',     # available task
  '+': 'cyan',    # waiting task
  '%': 'magenta', # finished task 
  '~': 'green',   # goal 
  '^': 'blue',    # chore 
  '<': 'yellow',  # past due task  
  '>': 'red',     # begin 
  '!': 'magenta', # inbox
}
EVENT_COLOR = NAMED_COLORS['LimeGreen']
AVAILABLE_COLOR = NAMED_COLORS['LightSkyBlue']
WAITING_COLOR = NAMED_COLORS['SlateGrey']
FINISHED_COLOR = NAMED_COLORS['DarkGrey']
GOAL_COLOR = NAMED_COLORS['GoldenRod']
CHORE_COLOR = NAMED_COLORS['Khaki']
PASTDUE_COLOR = NAMED_COLORS['DarkOrange']
BEGIN_COLOR = NAMED_COLORS['Gold']
INBOX_COLOR = NAMED_COLORS['OrangeRed']
_COLOR = NAMED_COLORS[]
_COLOR = NAMED_COLORS[]

```
