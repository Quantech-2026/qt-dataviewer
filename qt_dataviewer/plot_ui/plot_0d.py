from PyQt5 import QtCore, QtWidgets
from qt_dataviewer.utils.qt_utils import qt_log_exception, get_font

from .smart_format import SmartFormatter
from .plots import BasePlot


class Plot0D(BasePlot):

    @qt_log_exception
    def create(self):
        font = get_font(1.3)

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setFont(font)
        self._layout.addWidget(self.label)

        self.update()

    def update(self):
        plot_model = self._plot_model
        data = plot_model.get_data()
        x = data

        x_formatter = SmartFormatter(x)
        x_str = x_formatter.with_units(data.item(), data)

        self.label.setText(x_str)
