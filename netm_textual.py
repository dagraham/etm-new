from etm.controller import Controller
from etm.view_textual import DynamicViewApp
from prompt_toolkit.key_binding import KeyBindings
from etm.common import log_msg, display_messages


def main():
    controller = Controller("example.db")
    view = DynamicViewApp(controller)
    view.run()


if __name__ == "__main__":
    main()
