from typing import List

from PyQt5 import QtCore, QtWidgets


class TextFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(str, str)

    def __init__(self, name: str, width: int = 100):
        super().__init__()
        self.name = name
        layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label)
        text_edit = QtWidgets.QLineEdit()
        text_edit.setMinimumWidth(width)
        self.text_edit = text_edit
        layout.addWidget(text_edit)

        text_edit.editingFinished.connect(self._text_changed)

    @QtCore.pyqtSlot()
    def _text_changed(self):
        text = self.text_edit.text()
        self.filter_changed.emit(self.name, text)


class ListFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(str, str)
    no_filtering_text = "-- All --"

    def __init__(self, name: str, items: List[str], width: int = 100):
        super().__init__()
        self.name = name

        layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label)

        combo_box = QtWidgets.QComboBox()
        combo_box.setMinimumWidth(width)
        combo_box.addItem(self.no_filtering_text)
        combo_box.addItems(items)
        combo_box.setCurrentIndex(0)
        self.combo_box = combo_box
        layout.addWidget(combo_box)

        combo_box.currentTextChanged.connect(self._text_changed)

    @QtCore.pyqtSlot(str)
    def _text_changed(self, text: str):
        if text != self.no_filtering_text:
            self.filter_changed.emit(self.name, text)
        else:
            # NOTE: emit None doesn't work.
            self.filter_changed.emit(self.name, "")

    def set_items(self, items: List[str]):
        combo_box = self.combo_box
        text = combo_box.currentText()
        combo_box.clear()
        combo_box.addItem(self.no_filtering_text)
        combo_box.addItems(items)
        combo_box.setCurrentText(text)


class KeywordFilterWidget(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(str, list)  # list[str]

    def __init__(self, name: str, width: int = 150):
        super().__init__()
        self.name = name

        layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label)
        text_edit = QtWidgets.QLineEdit()
        text_edit.setMinimumWidth(width)
        self.text_edit = text_edit
        layout.addWidget(text_edit)

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

        self.filter_changed.emit(self.name, keywords)
