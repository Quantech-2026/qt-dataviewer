import numpy as np
import xarray as xr
from qtpy import QtCore, QtWidgets
from qt_dataviewer.model.plot_model import get_phase
from qt_dataviewer.utils.qt_utils import qt_log_exception, get_font

from .smart_format import SmartFormatter
from .plots import BasePlot


class Plot0D(BasePlot):

    @qt_log_exception
    def create(self):
        font = get_font(1.3)

        self._layout.addStretch(1)
        self.labels = []
        for i in range(4):
            label = QtWidgets.QLabel()
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setFont(font)
            self._layout.addWidget(label)
            self.labels.append(label)
        self._layout.addStretch(1)

        self.update()

    def update(self):
        plot_model = self._plot_model
        data = plot_model.get_data()
        x = data

        texts = [""]*4
        if np.iscomplexobj(x):

            texts[0] = "Re: " + _get_text(x.real)
            texts[1] = "Im: " + _get_text(x.imag)
            texts[2] = "Ampl: " + _get_text(np.abs(x))
            texts[3] = "Phase: " + _get_text(get_phase(x))
        else:
            texts[0] = _get_text(x)

        for i, text in enumerate(texts):
            self.labels[i].setText(text)


def _get_text(x: xr.DataArray):
    return SmartFormatter(x).with_units(x.item(), x)
