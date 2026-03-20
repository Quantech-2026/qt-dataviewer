import os
import sys
from qt_dataviewer.data_file_browser import DataFileBrowser


def print_usage():
    print("Usage: qt-file-browser [<directory>] [--dark] [--light]")


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

    if path and not os.path.isdir(path):
        print(f"Error: '{path}' is not a directory")
        print()
        print_usage()
        return

    DataFileBrowser(path, **kwargs)
