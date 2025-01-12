from rich.console import Console
from rich.table import Table
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from datetime import datetime

# day_color = NAMED_COLORS["LightSkyBlue"]
day_color = NAMED_COLORS["LightGreen"]

busy = '■'
free = '□'
conflict = '▨'
all_day = '━'
width = 10


table = Table(
    title="[yellow]October 28 - November 24, 2024[/yellow]",
    box=False, show_header=False, expand=True
) 

table.add_column("wk", justify="center", style=day_color, no_wrap=True, width=3, vertical="middle") 
table.add_column("MO", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle") 
table.add_column("TU", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("WE", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("TH", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("FR", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("SA", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("SU", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")

table.add_row("47\n", "28\n", "29\n[dim]□[/dim]■[dim]□[/dim][red]■[/red]■[dim]□[/dim]", "30\n", "31\n", "01\n", "02\n", "03\n") 
# table.add_row("47\n", "28\n", "29\n■[dim]■[/dim][red]■[/red]■[dim]■[/dim]", "30\n", "31\n", "01\n", "02\n", "03\n") 
table.add_row("48", "04\n", "05\n", "06\n", "07\n", "08\n", "09\n", "10\n") 
table.add_row("49", "11\n", "12\n", "13\n", "14\n", "[bold][yellow]━ 15 ━[/yellow][/bold]\n ", "16\n", "17\n") 
# table.add_row("11\n", "12\n", "13\n", "14\n", "[bold][yellow]~ 15 ~[/yellow][/bold]\n", "16\n", "17\n") 
table.add_row("50", "18\n", "19\n", "20\n", "21\n", "22\n", "23\n", "24\n") 

console = Console()
console.print(table)

from rich import print
from rich.table import Table

now = datetime.now().strftime("%a %b %-d %Y")
grid = Table.grid(expand=True)
grid.add_column(style=day_color)
grid.add_column(justify="right")
grid.add_row(f" {now}", "[bold][red]3<[/red] [yellow]>2[/yellow][/bold]   ")
 
print(grid)



from rich.console import Console
from io import StringIO

# Create a StringIO buffer
buffer = StringIO()

# Create a Console instance that writes to the buffer
console = Console(file=buffer)

# Text to be centered
text = "This line is centered!"

# Print the centered text to the buffer
console.print(text, justify="center")

# Get the string value of the buffer
output = buffer.getvalue()

# Close the buffer (optional)
buffer.close()

# Output is now saved as a string
print("Captured Output:")
print(repr(output))  # Using repr to show exact string with spaces
