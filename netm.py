from etm.controller import Controller
from etm.view_rich import FourWeekView
from prompt_toolkit.key_binding import KeyBindings
from etm.common import log_msg, display_messages


def main():
    """
    Entry point for setting up and running the FourWeekView application.
    """
    # Initialize the database manager
    # db_manager = DatabaseManager("example.db")

    # Initialize key bindings
    bindings = KeyBindings()
    log_msg(f"got bindings {bindings}")

    controller = Controller("example.db")
    log_msg(f"got controller {controller}")

    # Create an instance of FourWeekView with the database manager and bindings
    view = FourWeekView(controller, bindings)
    view.run()


if __name__ == "__main__":
    log_msg("Starting the application")
    main()
