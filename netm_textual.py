# from etm.database_refactored import DatabaseManager
# from etm.fourweek_textual_refactored import (
#     FourWeekTextualApp,
# )  # Import the Textual version
#
#
# def main():
#     """
#     Entry point for setting up and running the FourWeekTextualApp application.
#     """
#     # Initialize the database manager
#     db_manager = DatabaseManager("example.db")
#
#     # Run the Textual application
#     app = FourWeekTextualApp(db_manager)
#     app.run()
#
#
# if __name__ == "__main__":
#     main()
#
from etm.database_refactored import DatabaseManager
from etm.fourweek_textual_refactored import FourWeekTextualApp


def main():
    db_manager = DatabaseManager("example.db")
    app = FourWeekTextualApp(db_manager)
    app.run()


if __name__ == "__main__":
    main()
