from textual import on
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input

from dateutil.parser import parse, ParserError


class InteractivePrompt(Widget):
    """Generic interactive prompt that validates input using a provided method."""

    what = reactive("")
    validate_method = None

    def __init__(self, validate_method, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validate_method = validate_method

    def render(self) -> str:
        return f"{self.what}"

    def validate_what(self, new_what: str) -> str:
        if self.validate_method:
            try:
                return self.validate_method(new_what)
            except Exception as e:
                return f"Error: {str(e)}"
        return new_what


class GenericApp(App[None]):
    def compose(self) -> ComposeResult:
        # A placeholder Input widget
        yield Input(placeholder="Entry: ", id="entry")
        # A generic InteractivePrompt with a specific validation method
        yield InteractivePrompt(
            validate_method=self.date_parser, id="interactive_prompt"
        )

    @on(Input.Changed)
    def update_what(self, event: Input.Changed) -> None:
        # Pass the input value to the InteractivePrompt
        self.query_one(InteractivePrompt).what = event.value

    @staticmethod
    def date_parser(value: str) -> str:
        """Example parser method to validate and transform date strings."""
        try:
            return parse(value).strftime("recognized: %Y-%m-%d %H:%M")
        except ParserError:
            return "Not recognized: " + value


if __name__ == "__main__":
    GenericApp().run()
