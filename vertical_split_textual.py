from textual.app import App
from textual.widgets import Header, Footer, Static, Input
from textual.containers import Vertical
from textual.binding import Binding
from textual.reactive import reactive
from rich.table import Table
from rich.text import Text


class SplitPaneApp(App):
    """A Textual application with a visible input field activated by keypress."""

    CSS = """
    Screen {
        background: black;
    }
    Vertical {
        border: round $secondary;
    }
    Static {
        padding: 1;
    }
    Input {
        border: round $primary;
    }
    """

    # Reactive property for table data
    table_data = reactive("Row 1: Sample data")

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("up", "update_table", "Add Row"),
        Binding("down", "clear_table", "Clear Table"),
        Binding("i", "focus_input", "Focus Input"),
    ]

    def compose(self):
        """Compose the layout of the app."""
        yield Header()
        yield Footer()

        with Vertical():
            # Top pane: Rich table display
            yield Static(self.render_table(), id="table-pane")

            # Bottom pane: Always visible input field
            yield Input(placeholder="Type here and press Enter...", id="input-pane")

    def render_table(self):
        """Render the Rich table."""
        table = Table(title="Rich Table Example")
        table.add_column("Row", justify="center", style="cyan")
        table.add_column("Data", style="magenta")
        table.add_row("1", self.table_data)
        return table

    def action_update_table(self):
        """Simulate adding a row to the table."""
        self.table_data = "New Row: Data updated"
        self.query_one("#table-pane", Static).update(self.render_table())

    def action_clear_table(self):
        """Clear the table."""
        self.table_data = ""
        self.query_one("#table-pane", Static).update(self.render_table())

    def action_focus_input(self):
        """Focus the input field when 'i' is pressed."""
        input_widget = self.query_one("#input-pane", Input)
        input_widget.focus()

    async def on_ready(self):
        """Ensure the input field does not have focus initially."""
        self.set_focus(None)  # Explicitly clear focus after the layout is ready

    async def on_input_submitted(self, message):
        """Handle input submission."""
        user_input = message.value  # Correctly access the submitted value
        self.table_data = f"User Input: {user_input}"  # Process the input
        self.query_one("#table-pane", Static).update(self.render_table())
        
        # Clear the input field
        input_widget = self.query_one("#input-pane", Input)
        input_widget.value = ""  # Clear the input content
        
        self.set_focus(None)  # Remove focus from the input field


if __name__ == "__main__":
    SplitPaneApp().run()
