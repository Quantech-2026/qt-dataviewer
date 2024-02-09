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

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        source_type: str,
        option_liveplotting: bool = False,
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

        hbox = QtWidgets.QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)

        self.source_type_label = QtWidgets.QLabel(f"{source_type}:")
        hbox.addWidget(self.source_type_label)

        source_label = QtWidgets.QLabel("<none>")
        source_label.setWordWrap(True) # @@@ Path !!
        source_label.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        font = QtGui.QFont()
        font.setPointSize(8)
        source_label.setFont(font)
        source_label.setMinimumWidth(120)
        self.source_label = source_label
        hbox.addWidget(self.source_label)

        filters_layout = QtWidgets.QHBoxLayout()
        self.filters_layout = filters_layout

        hbox.addLayout(filters_layout, 1)

        hbox.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        checkbox = QtWidgets.QCheckBox("Live updating")
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        self.cb_live_plotting = checkbox

        hbox.addWidget(checkbox, alignment=QtCore.Qt.AlignRight)

        close_all_button = QtWidgets.QPushButton("Close all plots")
        close_all_button.clicked.connect(self.close_all_plots)
        hbox.addWidget(close_all_button)

        self.setLayout(hbox)

    def set_live_plotting(self, checked: bool):
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

