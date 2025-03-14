#!/usr/bin/env python3
from etm.controller import Controller
from etm.view_textual import DynamicViewApp

# from prompt_toolkit.key_binding import KeyBindings
from etm.common import log_msg, display_messages

from rich import print


# def test():
#     controller = Controller("example.db")
#     db_manager = controller.db_manager
#     last_instances = db_manager.get_last_instances()
#     print("Last Instances:", last_instances[:5])
#     next_instances = db_manager.get_next_instances()
#     print("\nNext Instances:", next_instances[:5])
#     next = controller.get_next()
#     print("\nNext:")
#     for item in next:
#         print(item)
#     last = controller.get_last()
#     print("\nLast:")
#     for item in last:
#         print(item)
#     search_results = controller.find_records(r"\ball day\b")
#     for item in search_results:
#         print(item)


def main():
    controller = Controller("example.db")
    view = DynamicViewApp(controller)
    view.run()


if __name__ == "__main__":
    main()
