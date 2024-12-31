from rich.console import Console
from rich.table import Table
from prompt_toolkit.styles.named_colors import NAMED_COLORS


# day_color = NAMED_COLORS["LightSkyBlue"]
day_color = NAMED_COLORS["LightGreen"]

busy = '■'
free = '□'
conflict = '▨'
all_day = '━'
width = 10


table = Table(title="October 28 - November 24, 2024", show_lines=True, expand=True) 

table.add_column("MO", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle") 
table.add_column("TU", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("WE", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("TH", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("FR", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("SA", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")
table.add_column("SU", justify="center", style=day_color, no_wrap=True, width=width, vertical="middle")

table.add_row("28\n", "29\n■ [red]■[/red]■ ", "30\n", "31\n", "01\n", "02\n", "03\n") 
table.add_row("04\n", "05\n", "06\n", "07\n", "08\n", "09\n", "10\n") 
table.add_row("11\n", "12\n", "13\n", "14\n", "[bold][yellow]━ 15 ━[/yellow][/bold]\n ", "16\n", "17\n") 
# table.add_row("11\n", "12\n", "13\n", "14\n", "[bold][yellow]~ 15 ~[/yellow][/bold]\n", "16\n", "17\n") 
table.add_row("18\n", "19\n", "20\n", "21\n", "22\n", "23\n", "24\n") 

console = Console()
console.print(table)

from rich import print
from rich.table import Table

grid = Table.grid(expand=True)
grid.add_column()
grid.add_column(justify="right")
grid.add_row("Raising shields", "[bold magenta]COMPLETED [green]:heavy_check_mark:")

print(grid)
