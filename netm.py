# from etm.database_refactored import DatabaseManager
# from etm.fourweek_rich_refactored import FourWeekView
#
#
# def main():
#     print("Setting up the database...")
#     db_manager = DatabaseManager("example.db")
#     print("Fetching events for the next 4 weeks...")
#     ui = FourWeekView(db_manager)
#     ui.run()
#     # Example usage
#
# if __name__ == "__main__":
#     main()
#


# from etm.database_refactored import DatabaseManager
# from etm.fourweek_rich_refactored import FourWeekView
#
#
# def main():
#     """Entry point for the application."""
#     # Initialize the database manager
#     db_path = "example.db"  # You can make this configurable via CLI arguments or environment variables
#     print(f"Setting up the database at '{db_path}'...")
#     db_manager = DatabaseManager(db_path)
#
#     # Initialize and run the 4-week view UI
#     print("Launching the 4-week view UI...")
#     ui = FourWeekView(db_manager)
#     try:
#         ui.run()  # Start the application
#     except KeyboardInterrupt:
#         print("\nApplication interrupted by user.")
#     finally:
#         print("Closing the application. Cleaning up resources...")
#         db_manager.close()  # Ensure the database connection is closed properly
#
#
# if __name__ == "__main__":
#     main()

# from etm.database_refactored import DatabaseManager
# from etm.fourweek_rich_refactored import FourWeekView
#
#
# class MockBindings:
#     """
#     Mock class to simulate key bindings.
#     """
#
#     def __init__(self):
#         self.bindings = {}
#
#     def add(self, key):
#         self.bindings[key] = f"Handler for '{key}'"
#         print(f"Key '{key}' bound.")
#
#     def simulate_key_press(self, key):
#         if key in self.bindings:
#             print(f"Simulating key press: '{key}'")
#         else:
#             print(f"No binding found for key: '{key}'")
#
#
# def main():
#     """
#     Entry point for setting up and running the FourWeekView simulation.
#     """
#     # Initialize the database manager
#     db_manager = DatabaseManager("example.db")
#
#     # Create an instance of FourWeekView
#     view = FourWeekView(db_manager)
#
#     # Set the initial display with afill = 1
#     # view.prepare_display(afill_value=1)
#
#     # Simulate bindings
#     bindings = MockBindings()
#     view.setup_key_bindings(bindings)
#
#     # Simulate user input
#     view.tag_to_id = {"a": 1, "b": 2, "aa": 3, "ab": 4}
#
#     print("\n--- Simulating user interactions ---")
#
#     # Simulate switching to afill = 2
#     view.prepare_display(afill_value=2)
#
#     # Simulate key presses
#     bindings.simulate_key_press("a")  # First key
#     bindings.simulate_key_press("b")  # Second key (triggers "ab")
#     view.process_tag("ab")  # Should output "Tag 'ab' corresponds to record ID 4"
#
#     # Simulate invalid input
#     view.process_tag("zz")  # Should output "Invalid tag: 'zz'"
#
#
# if __name__ == "__main__":
#     main()

from etm.database_refactored import DatabaseManager
from etm.fourweek_rich_refactored import FourWeekView
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
