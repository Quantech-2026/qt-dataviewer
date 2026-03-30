import os
import sys
from qt_dataviewer.qcodes import QCoDeSDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()


def print_usage():
    print("Usage: qt-qcodes-browser [<database-file>] [--dark] [--light]")


def main():
    args = sys.argv[1:]

    kwargs = {}
    path = None
    for arg in args:
        if arg == "--dark":
            kwargs["gui_style"] = "dark"
        elif arg == "--light":
            kwargs["gui_style"] = "light"
        elif path is None:
            path = arg
        else:
            print_usage()
            return

    if path and not os.path.exists(path):
        print(f"Error: '{path}' not found")
        print()
        print_usage()
        return

    QCoDeSDataBrowser(path, **kwargs)
