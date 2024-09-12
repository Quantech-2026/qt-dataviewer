import qt_dataviewer.resources as resources
import os
import pathlib

from PyQt5 import QtGui, QtCore


def add_icon_to_button(button, icon_name):
    button.setIcon(get_icon(icon_name))
    button.setIconSize(QtCore.QSize(24, 24))


def get_icon(icon_name):
    icon_path = os.path.dirname(resources.__file__)
    return QtGui.QIcon(os.path.join(icon_path, icon_name))


def get_image(image_name):
    icon_path = os.path.dirname(resources.__file__)
    return QtGui.QImage(os.path.join(icon_path, image_name))


def add_icons_to_checkbox(checkbox, icon_checked: str, icon_unchecked: str, size: int):
    icon_path = os.path.dirname(resources.__file__)
    icon_unchecked_uri = pathlib.Path(os.path.join(icon_path, icon_unchecked)).as_uri()
    icon_checked_uri = pathlib.Path(os.path.join(icon_path, icon_checked)).as_uri()
    style_sheet = f"""
    QCheckBox::indicator {{
        width: {size}px;
        height: {size}px;
    }}
    QCheckBox::indicator:unchecked {{
        image: url("{icon_unchecked_uri[8:]}");
    }}
    QCheckBox::indicator:checked {{
        image: url("{icon_checked_uri[8:]}");
    }}
    """
    checkbox.setStyleSheet(style_sheet)


class Icons:
    STARRED = get_icon("Starred.png")
    NO_STAR = get_icon("StarWhite.png")
    NEUTRAL = get_icon("NeutralCompact.png")
    HIDDEN = get_icon("Hidden.png")


class Images:
    STARRED = get_image("Starred.png").scaledToHeight(20, mode=QtCore.Qt.SmoothTransformation)
    NO_STAR = get_image("StarWhite.png").scaledToHeight(20, mode=QtCore.Qt.SmoothTransformation)
    NEUTRAL = get_image("Neutral.png").scaledToHeight(20, mode=QtCore.Qt.SmoothTransformation)
    HIDDEN = get_image("Hidden.png").scaledToHeight(20, mode=QtCore.Qt.SmoothTransformation)
