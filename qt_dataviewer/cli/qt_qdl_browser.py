import os
import sys
from qt_dataviewer.sqdl.data_browser import SqdlDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()


def print_usage():
    print("""
Usage: qt-qdl-browser [<scope>] [--dark] [--light]

Browser for QDL database. This database is an internal to QuTech.
"""
          )


def main():
    try:
        import qdl_client
    except ImportError:
        print("Error: package qdl-client not found.")

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

    SqdlDataBrowser(scope, backend_type="qdl", **kwargs)
