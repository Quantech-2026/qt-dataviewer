import os
import sys
from qt_dataviewer.quantify import QuantifyDataBrowser


def print_usage():
    print("Usage: qt-quantify-browser [<directory>] [--dark] [--light] [--no-scan] [--check-datasets]")


def main():
    args = sys.argv[1:]

    kwargs = {}
    path = None
    for arg in args:
        if arg == "--dark":
            kwargs["gui_style"] = "dark"
        elif arg == "--light":
            kwargs["gui_style"] = "light"
        elif arg == "--no-scan":
            kwargs["auto_scan"] = False
        elif arg == "--check-datasets":
            kwargs["check_datasets"] = True
        elif path is None:
            path = arg
        else:
            print_usage()
            return

    if path and not os.path.isdir(path):
        print(f"Error: '{path}' is not a directory")
        print()
        print_usage()
        return

    QuantifyDataBrowser(path, **kwargs)
