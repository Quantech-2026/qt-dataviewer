from functools import cache
import qt_dataviewer.resources as resources
import os
import pathlib

from qtpy import QtGui, QtCore


def add_icon_to_button(button, icon_name):
    button.setIcon(get_icon(icon_name))
    button.setIconSize(QtCore.QSize(24, 24))


@cache
def get_icon(icon_name):
    icon_path = os.path.dirname(resources.__file__)
    return QtGui.QIcon(os.path.join(icon_path, icon_name))


@cache
def get_image(image_name, height=None):
    icon_path = os.path.dirname(resources.__file__)
    image = QtGui.QImage(os.path.join(icon_path, image_name))
    if height:
        image = image.scaledToHeight(height, mode=QtCore.Qt.SmoothTransformation)
    return image


def add_icons_to_checkbox(checkbox, icon_checked: str, icon_unchecked: str, size: int):
    icon_path = os.path.dirname(resources.__file__)
    icon_unchecked_path = pathlib.Path(os.path.join(icon_path, icon_unchecked)).as_posix()
    icon_checked_path = pathlib.Path(os.path.join(icon_path, icon_checked)).as_posix()
    style_sheet = f"""
    QCheckBox::indicator {{
        width: {size}px;
        height: {size}px;
    }}
    QCheckBox::indicator:unchecked {{
        image: url("{icon_unchecked_path}");
    }}
    QCheckBox::indicator:checked {{
        image: url("{icon_checked_path}");
    }}
    """
    checkbox.setStyleSheet(style_sheet)


class Icons:

    @staticmethod
    def starred():
        return get_icon("Starred.png")

    @staticmethod
    def no_star():
        return get_icon("StarWhite.png")

    @staticmethod
    def neutral():
        return get_icon("NeutralCompact.png")

    @staticmethod
    def hidden():
        return get_icon("Hidden.png")

    @staticmethod
    def looping():
        return get_icon("looping.png")


class Images:

    @staticmethod
    def starred():
        return get_image("Starred.png", height=20)

    @staticmethod
    def no_star():
        return get_image("StarWhite.png", height=20)

    @staticmethod
    def neutral():
        return get_image("Neutral.png", height=20)

    @staticmethod
    def hidden():
        return get_image("Hidden.png", height=20)
