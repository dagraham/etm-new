from etm.model import DatabaseManager
from etm.view_rich import FourWeekView
from prompt_toolkit.key_binding import KeyBindings


def main():
    """
    Entry point for setting up and running the FourWeekView application.
    """
    # Initialize the database manager
    db_manager = DatabaseManager("example.db")

    # Initialize key bindings
    bindings = KeyBindings()

    # Create an instance of FourWeekView with the database manager and bindings
    view = FourWeekView(db_manager, bindings)
    view.run()


if __name__ == "__main__":
    main()
