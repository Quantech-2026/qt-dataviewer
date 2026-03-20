from PyQt5 import QtCore, QtWidgets, QtGui


class TopBar(QtWidgets.QWidget):
    """Top bar of the browser

    Attributes:
        liveplotting_changed (QtCore.pyqtSignal):
            A PyQt signal emitted when the live plotting state changes.
        close_all_plots (QtCore.pyqtSignal):
            A PyQt signal emitted when all plots should be closed.
    """

    liveplotting_changed = QtCore.pyqtSignal(bool)
    close_all_plots = QtCore.pyqtSignal()
    open_uid = QtCore.pyqtSignal(str)

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        source_type: str,
        option_liveplotting: bool = False,
        uid_label_text: str = 'UID',
    ):
        """Initializes top bar

        Args:
            parent (QtWidgets.QWidget): parent widget
            source_type (str): label to show for source ("Directory", "Database", "Scope")
            option_liveplotting (bool): if True shows a live plotting checkbox.
        """
        super().__init__(parent)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        vbox.addLayout(hbox, 1)

        filters_layout = QtWidgets.QHBoxLayout()
        filters_layout.setContentsMargins(0, 0, 0, 0)
        # filters_layout.addStretch(1)

        self.filters_layout = filters_layout
        vbox.addLayout(filters_layout, 1)

        self.source_type_label = QtWidgets.QLabel(f"{source_type}:")
        hbox.addWidget(self.source_type_label)

        source_label = QtWidgets.QLabel("<none>")
        source_label.setWordWrap(True)
        source_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        source_label.setMinimumWidth(140)
        self.source_label = source_label
        hbox.addWidget(self.source_label, stretch=4)

        hbox.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        hbox.addWidget(QtWidgets.QLabel(uid_label_text))
        uid_edit = QtWidgets.QLineEdit()
        uid_edit.setMinimumWidth(140)
        self.uid_edit = uid_edit
        hbox.addWidget(uid_edit, stretch=2)
        uid_edit.returnPressed.connect(self._uid_entered)

        if option_liveplotting:
            checkbox = QtWidgets.QCheckBox("Live updating")
            checkbox.stateChanged.connect(self._on_checkbox_changed)
            hbox.addWidget(checkbox, alignment=QtCore.Qt.AlignRight)
            self.cb_live_plotting = checkbox
        else:
            self.cb_live_plotting = None

        close_all_button = QtWidgets.QPushButton("Close all plots")
        close_all_button.setToolTip("Closes all plots (Ctrl+K)")
        close_all_button.clicked.connect(self.close_all_plots)
        self._shortcut_close_all = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+K"), self)
        self._shortcut_close_all.activated.connect(self.close_all_plots)
        hbox.addWidget(close_all_button)

    def set_live_plotting(self, checked: bool):
        if self.cb_live_plotting is not None:
            self.cb_live_plotting.setChecked(checked)

    def set_data_source(self, source_name: str) -> None:
        """Set the text for the data source.

        Args:
            source_name (str): name of source.
        """
        if source_name is None:
            self.source_label.setText("<none>")
        else:
            self.source_label.setText(source_name)

    def add_filter(self, filter_widget):
        self.filters_layout.addWidget(filter_widget, 1)

    @QtCore.pyqtSlot(int)
    def _on_checkbox_changed(self, state: QtCore.Qt.CheckState) -> None:
        """Slot called when the checkbox is changed.

        Args:
            state (QtCore.Qt.CheckState): The new state of the checkbox.
        """
        self.liveplotting_changed.emit(state == QtCore.Qt.Checked)

    @QtCore.pyqtSlot()
    def _uid_entered(self):
        text = self.uid_edit.text().strip()
        if not text:
            return
        self.open_uid.emit(text)
