import os
import sys
from qt_dataviewer.sqdl.data_browser import SqdlDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()


def print_usage():
    print("""
Usage: qt-sqdl-browser [<scope>] [--dark] [--light]

Browser for sQDL database. This database is an internal to QuTech.
"""
          )


def main():
    try:
        import sqdl_client
    except ImportError:
        print("Error: package sqdl-client not found. (This is QuTech internal code.)")

    args = sys.argv[1:]

    kwargs = {}
    scope = None
    for arg in args:
        if arg == "--dark":
            kwargs["gui_style"] = "dark"
        elif arg == "--light":
            kwargs["gui_style"] = "light"
        elif scope is None:
            scope = arg
        else:
            print_usage()
            return

    SqdlDataBrowser(scope, **kwargs)
