
from PyQt5 import QtCore, QtWidgets

from qt_dataviewer.abstract.types import LabelsDict
from qt_dataviewer.resources.icons import Icons


class TextFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(str, str)

    def __init__(self, name: str, key: str, width: int = 100):
        super().__init__()
        self.name = name
        self.key = key
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label, 0)
        text_edit = QtWidgets.QLineEdit()
        text_edit.setMinimumWidth(width)
        self.text_edit = text_edit
        layout.addWidget(text_edit, 1)

        text_edit.editingFinished.connect(self._text_changed)

    @QtCore.pyqtSlot()
    def _text_changed(self):
        text = self.text_edit.text()
        self.filter_changed.emit(self.key, text)


class ListFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(str, str)
    no_filtering_text = "-- All --"

    def __init__(self, name: str, key: str, items: list[str], width: int = 100):
        super().__init__()
        self.name = name
        self.key = key
        self._updating = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label, 0)

        items.sort(key=lambda x:x.lower())
        combo_box = QtWidgets.QComboBox()
        combo_box.setMinimumWidth(width)
        combo_box.addItem(self.no_filtering_text)
        combo_box.addItems(items)
        combo_box.setCurrentIndex(0)
        self.combo_box = combo_box
        layout.addWidget(combo_box, 1)

        combo_box.currentTextChanged.connect(self._text_changed)

    @QtCore.pyqtSlot(str)
    def _text_changed(self, text: str):
        if self._updating:
            return
        if text != self.no_filtering_text:
            self.filter_changed.emit(self.key, text)
        else:
            # NOTE: emit None doesn't work.
            self.filter_changed.emit(self.key, "")

    def set_items(self, items: list[str]):
        items.sort(key=lambda x:x.lower())
        combo_box = self.combo_box
        old_text = combo_box.currentText()
        self._updating = True
        combo_box.clear()
        combo_box.addItem(self.no_filtering_text)
        combo_box.addItems(items)
        combo_box.setCurrentText(old_text)
        self._updating = False
        if old_text != combo_box.currentText():
            self._text_changed(combo_box.currentText())

    @QtCore.pyqtSlot(dict)
    def set_items_from_dict(self, items: LabelsDict):
        self.set_items(items.get(self.key, []))


class KeywordFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(str, list)  # list[str]

    def __init__(self, name: str, key: str, width: int = 150):
        super().__init__()
        self.name = name
        self.key = key

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label, 0)
        text_edit = QtWidgets.QLineEdit()
        text_edit.setMinimumWidth(width)
        self.text_edit = text_edit
        layout.addWidget(text_edit, 1)

        text_edit.editingFinished.connect(self._text_changed)

    @QtCore.pyqtSlot()
    def _text_changed(self):
        text = self.text_edit.text()
        keywords = []
        # allow separation with commas and/or spaces
        # replace commas by spaces
        text = text.replace(',', ' ')
        for word in text.split(' '):
            if word:
                keywords.append(word)

        self.filter_changed.emit(self.key, keywords)


class RatingFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(int)

    def __init__(self, name: str, star: bool = False, hide: bool = False):
        super().__init__()
        self.name = name
        self._rating = 0

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        label = QtWidgets.QLabel(name)
        layout.addWidget(label, 0)

        combo_box = QtWidgets.QComboBox()
        self.combo_box = combo_box
        if star:
            combo_box.addItem(Icons.starred(), "Starred only")
        if hide:
            combo_box.addItem(Icons.neutral(), "Default")
            combo_box.addItem(Icons.hidden(), "Show hidden")
        else:
            combo_box.addItem(Icons.no_star(), "Default")
        combo_box.setCurrentText("Default")

        combo_box.currentTextChanged.connect(self._text_changed)
        layout.addWidget(combo_box, 1)

    @QtCore.pyqtSlot(str)
    def _text_changed(self, text: str):
        if text == "Starred only":
            self._rating = +1
            self.filter_changed.emit(self._rating)
        elif text == "Default":
            self._rating = 0
            self.filter_changed.emit(self._rating)
        elif text == "Show hidden":
            self._rating = -1
            self.filter_changed.emit(self._rating)

